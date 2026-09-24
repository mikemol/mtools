# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 1: one transcript JSONL line in, one tagged record out, and nothing dropped.

A Claude Code transcript is one JSON envelope per line. This module narrows each line into
exactly one of five record kinds:

- `UserRecord` and `AssistantRecord`: `type: "user"` / `type: "assistant"` with a `message`;
- `AttachmentRecord`: `type: "attachment"`, where `message` is null and the content lives in
  `attachment.prompt` (a str OR a list of blocks) and the provenance in `attachment.origin.kind`,
  nested, never at the top level. A reader keyed on `message.role` sees none of it;
- `UnknownRecord`: any other `type`, a missing `type`, a non-object line, or a known type whose
  fields do not have the expected shape. It carries the reason;
- `MalformedLine`: a line that is not JSON, reported with its 1-based line number.

⚑ THE POSITIVE-CONTROL RULE: every input line yields exactly one record. Unknown shapes and
malformed lines are records, never skips, so a count over the output is a count over the input.
Each decoded record keeps `raw`, the whole envelope, for the lossless walk (stage 2) to read.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

type Json = dict[str, object]
type Content = str | tuple[object, ...]


@dataclass(frozen=True, slots=True)
class UserRecord:
    """A `type: "user"` envelope. Its content may be tool output wearing the user role."""

    line: int
    raw: Json
    content: Content
    is_sidechain: bool
    is_compact_summary: bool


@dataclass(frozen=True, slots=True)
class AssistantRecord:
    """A `type: "assistant"` envelope; `tool_use` interiors stay inside `content`."""

    line: int
    raw: Json
    content: Content
    is_sidechain: bool


@dataclass(frozen=True, slots=True)
class AttachmentRecord:
    """A `type: "attachment"` envelope: `message` is null, the content is `attachment.prompt`."""

    line: int
    raw: Json
    attachment_type: str | None
    prompt: Content | None
    origin_kind: str | None
    is_sidechain: bool


@dataclass(frozen=True, slots=True)
class UnknownRecord:
    """A parsed line this module does not decode. `raw` is whatever the JSON was."""

    line: int
    raw: object
    type: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class MalformedLine:
    """A line that is not JSON. It is a population to count, never a line to skip."""

    line: int
    text: str
    error: str


type Record = UserRecord | AssistantRecord | AttachmentRecord | UnknownRecord | MalformedLine


class _ShapeError(Exception):
    """A known `type` whose fields do not have the shape this module decodes."""


def _content(value: object, where: str) -> Content:
    """Narrow a content field: a string, or a list of blocks kept as a tuple.

    Returns:
        the narrowed content.

    Raises:
        _ShapeError: when the value is neither a string nor a list.

    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return tuple(cast("list[object]", value))
    msg = f"{where} is {type(value).__name__}, not str or list"
    raise _ShapeError(msg)


def _message_content(env: Json) -> Content:
    """Read `message.content` from a user or assistant envelope.

    Returns:
        the narrowed content.

    Raises:
        _ShapeError: when `message` is not an object.

    """
    message = env.get("message")
    if not isinstance(message, dict):
        msg = f"message is {type(message).__name__}, not an object"
        raise _ShapeError(msg)
    return _content(cast("Json", message).get("content"), "message.content")


def _optional_str(value: object) -> str | None:
    """Return the value when it is a string, else None.

    Returns:
        the string, or None.

    """
    return value if isinstance(value, str) else None


def _attachment(env: Json, line: int, *, sidechain: bool) -> AttachmentRecord:
    """Decode an attachment envelope, reading `origin` where it actually is: nested.

    Returns:
        the attachment record.

    Raises:
        _ShapeError: when `attachment` is not an object.

    """
    att = env.get("attachment")
    if not isinstance(att, dict):
        msg = f"attachment is {type(att).__name__}, not an object"
        raise _ShapeError(msg)
    body = cast("Json", att)
    raw_prompt = body.get("prompt")
    prompt = None if raw_prompt is None else _content(raw_prompt, "attachment.prompt")
    origin = body.get("origin")
    kind = _optional_str(cast("Json", origin).get("kind")) if isinstance(origin, dict) else None
    return AttachmentRecord(
        line=line,
        raw=env,
        attachment_type=_optional_str(body.get("type")),
        prompt=prompt,
        origin_kind=kind,
        is_sidechain=sidechain,
    )


def decode(value: object, line: int) -> Record:
    """Narrow one parsed JSON value into a record. Never raises; never returns nothing.

    Returns:
        the tagged record; `UnknownRecord` for anything it does not decode.

    """
    if not isinstance(value, dict):
        return UnknownRecord(line, value, None, f"line is {type(value).__name__}, not an object")
    env = cast("Json", value)
    kind = _optional_str(env.get("type"))
    sidechain = env.get("isSidechain") is True
    try:
        if kind == "user":
            return UserRecord(
                line=line,
                raw=env,
                content=_message_content(env),
                is_sidechain=sidechain,
                is_compact_summary=env.get("isCompactSummary") is True,
            )
        if kind == "assistant":
            return AssistantRecord(line, env, _message_content(env), is_sidechain=sidechain)
        if kind == "attachment":
            return _attachment(env, line, sidechain=sidechain)
    except _ShapeError as exc:
        return UnknownRecord(line, env, kind, str(exc))
    reason = "no string `type` field" if kind is None else f"type {kind!r} is not decoded"
    return UnknownRecord(line, env, kind, reason)


def parse_line(text: str, line: int) -> Record:
    """Parse one JSONL line. A line that is not JSON is a `MalformedLine`, not an exception.

    Returns:
        the tagged record.

    """
    try:
        value = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        return MalformedLine(line, text, str(exc))
    return decode(value, line)


def parse_lines(lines: Iterable[str]) -> Iterator[Record]:
    """Yield one record per input line, numbered from 1; blank lines are malformed, not skipped.

    Yields:
        the records, in input order.

    """
    for number, text in enumerate(lines, start=1):
        yield parse_line(text.rstrip("\n"), number)


def read_path(path: Path) -> Iterator[Record]:
    """Yield the records of a transcript file, one per line.

    Yields:
        the records, in file order.

    """
    with path.open(encoding="utf-8", errors="replace") as handle:
        yield from parse_lines(handle)

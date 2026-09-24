# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 4: who is speaking in a record — a classification, not a yes/no "is it the human".

⚑ "WHAT THE USER SAID" IS NOT `role == "user"`. Tool output, harness injections, subagent
reports and peer sessions all arrive wearing the user role. substrate's `human_text` answered
one question — human or not — and so a peer's message queued as an attachment, or a cron tick
prompt, was either invisible or counted as the operator. Here every record gets one kind:

- `human`: prose the operator typed (after harness wrappers are stripped), or a queued
  attachment whose `attachment.origin.kind` is `human`;
- `peer`: another session's message — an attachment with origin `peer`, or user text that is
  a `<cross-session-message>` / `<agent-message>` wrapper;
- `harness`: text that is entirely harness plumbing (`<system-reminder>`, command wrappers,
  `<task-notification>`), an `isMeta` envelope, or an attachment with no origin;
- `tool_result`: user-role content that is only tool output;
- `compact_summary`: a compaction summary;
- `scheduled`: a prompt the CALLER declared scheduled, by prefix. ⚑ Nothing in the envelope
  marks a cron or tick prompt (study shape 5), so this cannot be inferred; a caller that knows
  its scheduler's prompts names them, and one that does not gets them as `human`, as before;
- `assistant`; `unknown` for an unknown record, a malformed line, or an origin kind not listed.

`text` is the prose the kind refers to, wrappers stripped: what a search for "what the human
said" should search, and nothing else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.transcriptstruct.blocks import blocks
from mikemol.transcriptstruct.records import AssistantRecord, AttachmentRecord, UserRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.transcriptstruct.records import Record

# Moved from substrate's human_text: the harness's wrappers, stripped before asking whether
# anything the human typed is left. Close tags are optional where an envelope may be cut.
_STRIP = (
    re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL),
    re.compile(
        r"<(command-name|command-message|command-args|local-command-stdout|local-command-stderr)>"
        r".*?</\1>",
        re.DOTALL,
    ),
    re.compile(r"<task-notification>.*?(?:</task-notification>|\Z)", re.DOTALL),
    re.compile(
        r"<(task-id|tool-use-id|output-file|status|summary|note|result)>.*?</\1>", re.DOTALL
    ),
)
_PEER = re.compile(r"\A\s*<(cross-session-message|agent-message)\b")
_ORIGIN = {"human": "human", "peer": "peer"}


@dataclass(frozen=True, slots=True)
class Provenance:
    """A record's speaker kind, and the prose that kind refers to."""

    kind: str
    text: str


def _strip(text: str) -> str:
    """Remove every harness wrapper from `text`.

    Returns:
        what is left, which is empty when the text was only plumbing.

    """
    for pattern in _STRIP:
        text = pattern.sub("", text)
    return text.strip()


def _prose(record: Record) -> str:
    """Join a record's decoded text blocks.

    Returns:
        the text blocks, newline-joined; tool output and thinking are not prose.

    """
    return "\n".join(block.text for block in blocks(record) if block.kind == "text")


def _by_flags(record: UserRecord) -> Provenance | None:
    """Classify a user record from its envelope flags and block kinds alone.

    Returns:
        compact_summary, harness (isMeta) or tool_result; None when the text must decide.

    """
    if record.is_compact_summary:
        return Provenance("compact_summary", _prose(record))
    if record.raw.get("isMeta") is True:
        return Provenance("harness", _prose(record))
    decoded = blocks(record)
    if decoded and all(block.kind.startswith("tool_result") for block in decoded):
        return Provenance("tool_result", "")
    return None


def _by_text(record: UserRecord, scheduled: Sequence[str]) -> Provenance:
    """Classify a user record from its prose.

    Returns:
        peer, harness (nothing left once wrappers are stripped), scheduled or human.

    """
    raw_text = _prose(record)
    if _PEER.match(raw_text):
        return Provenance("peer", raw_text.strip())
    text = _strip(raw_text)
    if not text:
        return Provenance("harness", "")
    if any(text.startswith(prefix) for prefix in scheduled):
        return Provenance("scheduled", text)
    return Provenance("human", text)


def classify(record: Record, *, scheduled: Sequence[str] = ()) -> Provenance:
    """Say who is speaking in `record`.

    `scheduled` lists prompt prefixes the caller's scheduler emits; see the module docstring.

    Returns:
        exactly one Provenance; never raises for any record stage 1 produces.

    """
    if isinstance(record, UserRecord):
        return _by_flags(record) or _by_text(record, scheduled)
    if isinstance(record, AssistantRecord):
        return Provenance("assistant", _prose(record))
    if isinstance(record, AttachmentRecord):
        if record.origin_kind is None:
            return Provenance("harness", _prose(record))
        return Provenance(_ORIGIN.get(record.origin_kind, "unknown"), _prose(record))
    return Provenance("unknown", "")

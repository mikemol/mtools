# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Gmail API responses narrowed into records: messages (W333), list pages (W334), MIME parts (W335).

⚑⚑ A MESSAGE THE NARROWING CANNOT READ IS A RECORD, NEVER A SKIP. `message` returns `Unreadable`
with a reason where a lenient reader would drop the message or fill a field in, so a count over
the output is a count over the input (life:W27, W287).

⚑ `object` IS THE TYPE OF A JSON VALUE HERE, NEVER `Any`. A container is checked with
`isinstance` and then cast to hold `object`, as //audiostruct's `stages._segments` does, and every
element is checked again where it is read. The idiom is restated, not imported, because a record
layer must not depend on another distribution.

⚑ TWO FIELDS MAY BE ABSENT, AND ONLY TWO. The API omits `labelIds` on a message with no labels and
`snippet` on one with no text; absence there reads as `()` and `""`, which is what the message
holds. Every other field is required, and a present field of the wrong type is always
`Unreadable`, never coerced.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import cast


@dataclass(frozen=True)
class Message:
    """A message the narrowing read in full: `headers` keep their order and their repeats."""

    id: str
    thread_id: str
    labels: tuple[str, ...]
    snippet: str
    internal_date_ms: int
    headers: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Unreadable:
    """A response the narrowing could not read: `id` when one was readable, and why not."""

    id: str | None
    reason: str


class _RefusedError(Exception):
    """One field out of shape; `message` turns it into `Unreadable`."""


def _record(value: object) -> dict[str, object] | None:
    # JSON object keys are always strings, so the cast states what `json.loads` guarantees.
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def _items(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        msg = f"{name} is missing or not a list"
        raise _RefusedError(msg)
    return cast("list[object]", value)


def _text(rec: dict[str, object], key: str) -> str:
    value = rec.get(key)
    if not isinstance(value, str):
        msg = f"{key} is missing or not a string"
        raise _RefusedError(msg)
    return value


def _labels(rec: dict[str, object]) -> tuple[str, ...]:
    if "labelIds" not in rec:
        return ()
    labels: list[str] = []
    for item in _items(rec["labelIds"], "labelIds"):
        if not isinstance(item, str):
            msg = "labelIds holds a non-string"
            raise _RefusedError(msg)
        labels.append(item)
    return tuple(labels)


def _snippet(rec: dict[str, object]) -> str:
    if "snippet" not in rec:
        return ""
    return _text(rec, "snippet")


def _internal_date(rec: dict[str, object]) -> int:
    value = _text(rec, "internalDate")
    if not value.isascii() or not value.isdigit():
        msg = f"internalDate {value!r} is not a decimal count of milliseconds"
        raise _RefusedError(msg)
    return int(value)


def _headers(rec: dict[str, object]) -> tuple[tuple[str, str], ...]:
    payload = _record(rec.get("payload"))
    if payload is None:
        msg = "payload is missing or not an object"
        raise _RefusedError(msg)
    headers: list[tuple[str, str]] = []
    for ordinal, item in enumerate(_items(payload.get("headers"), "payload.headers")):
        header = _record(item)
        if header is None:
            msg = f"payload.headers[{ordinal}] is not an object"
            raise _RefusedError(msg)
        try:
            headers.append((_text(header, "name"), _text(header, "value")))
        except _RefusedError as err:
            msg = f"payload.headers[{ordinal}]: {err}"
            raise _RefusedError(msg) from err
    return tuple(headers)


def message(value: object) -> Message | Unreadable:
    """Narrow one `users.messages.get` response (`format=metadata`) into one record.

    Returns:
        `Message` when every required field reads, else `Unreadable` with the first reason.

    """
    rec = _record(value)
    if rec is None:
        return Unreadable(id=None, reason="response is not a JSON object")
    raw_id = rec.get("id")
    msg_id = raw_id if isinstance(raw_id, str) else None
    try:
        return Message(
            id=_text(rec, "id"),
            thread_id=_text(rec, "threadId"),
            labels=_labels(rec),
            snippet=_snippet(rec),
            internal_date_ms=_internal_date(rec),
            headers=_headers(rec),
        )
    except _RefusedError as err:
        return Unreadable(id=msg_id, reason=str(err))


@dataclass(frozen=True)
class Listed:
    """One entry of a `users.messages.list` page, with where it was listed."""

    id: str
    thread_id: str
    page: int
    ordinal: int


def _entry(item: object, page: int, ordinal: int) -> Listed | Unreadable:
    where = f"page {page} messages[{ordinal}]"
    entry = _record(item)
    if entry is None:
        return Unreadable(id=None, reason=f"{where} is not an object")
    raw_id = entry.get("id")
    try:
        return Listed(_text(entry, "id"), _text(entry, "threadId"), page, ordinal)
    except _RefusedError as err:
        return Unreadable(id=raw_id if isinstance(raw_id, str) else None, reason=f"{where}: {err}")


def pages(values: list[object]) -> list[Listed | Unreadable]:
    """Narrow a run of `users.messages.list` responses, in fetch order, into records.

    ⚑ ONE RECORD PER LISTED ENTRY, AND ONE PER PAGE THAT CANNOT BE READ. `resultSizeEstimate` is
    the API's estimate and is never read as the count: the count is the number of records. An
    empty page omits `messages`, and reads as no entries.

    ⚑ A TRUNCATED LISTING IS A RECORD TOO. Every page but the last must carry `nextPageToken`, and
    the last must not; otherwise the run is not the whole listing, and an `Unreadable` says so
    rather than letting a partial count read as complete.

    Returns:
        `Listed` per entry in order, with `Unreadable` for each page or entry out of shape.

    """
    out: list[Listed | Unreadable] = []
    last = len(values) - 1
    for page_no, value in enumerate(values):
        page = _record(value)
        if page is None:
            out.append(Unreadable(id=None, reason=f"page {page_no} is not a JSON object"))
            continue
        has_next = isinstance(page.get("nextPageToken"), str)
        if has_next == (page_no == last):
            state = "has" if has_next else "lacks"
            why = f"page {page_no} {state} nextPageToken: listing truncated"
            out.append(Unreadable(id=None, reason=why))
        if "messages" not in page:
            continue
        try:
            items = _items(page["messages"], f"page {page_no} messages")
        except _RefusedError as err:
            out.append(Unreadable(id=None, reason=str(err)))
            continue
        out.extend(_entry(item, page_no, ordinal) for ordinal, item in enumerate(items))
    return out


@dataclass(frozen=True)
class Part:
    """One node of a `format=full` MIME tree: `path` is its child indices from the root."""

    path: tuple[int, ...]
    part_id: str
    mime_type: str
    filename: str
    data: bytes | None
    attachment_id: str | None


def _where(path: tuple[int, ...]) -> str:
    return "part " + (".".join(str(i) for i in path) if path else "root")


def decode_base64url(text: str) -> bytes:
    """Decode Gmail's base64url strictly, padding or not (W335, shared with fetch.raw in W358).

    Text a lenient decoder would quietly repair is refused, never passed on in a changed form:
    binascii.Error (a ValueError) propagates from the strict decode.

    Returns:
        the decoded bytes.

    """
    return base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_", validate=True)


def _optional_text(rec: dict[str, object], key: str) -> str | None:
    return _text(rec, key) if key in rec else None


def _part(node: dict[str, object], path: tuple[int, ...]) -> Part:
    body = _record(node.get("body"))
    if body is None:
        msg = "body is missing or not an object"
        raise _RefusedError(msg)
    data = _optional_text(body, "data")
    try:
        decoded = None if data is None else decode_base64url(data)
    except binascii.Error as err:
        msg = f"body.data is not base64url: {err}"
        raise _RefusedError(msg) from err
    return Part(
        path=path,
        part_id=_text(node, "partId"),
        mime_type=_text(node, "mimeType"),
        filename=_text(node, "filename"),
        data=decoded,
        attachment_id=_optional_text(body, "attachmentId"),
    )


def _walk(
    value: object, path: tuple[int, ...], msg_id: str | None, out: list[Part | Unreadable]
) -> None:
    node = _record(value)
    if node is None:
        out.append(Unreadable(id=msg_id, reason=f"{_where(path)} is not an object"))
        return
    try:
        out.append(_part(node, path))
    except _RefusedError as err:
        out.append(Unreadable(id=msg_id, reason=f"{_where(path)}: {err}"))
    if "parts" not in node:
        return
    try:
        children = _items(node["parts"], "parts")
    except _RefusedError as err:
        out.append(Unreadable(id=msg_id, reason=f"{_where(path)}: {err}"))
        return
    for index, child in enumerate(children):
        _walk(child, (*path, index), msg_id, out)


def parts(value: object) -> list[Part | Unreadable]:
    """Narrow one `users.messages.get` response (`format=full`) into one record per MIME part.

    ⚑ EVERY NODE OF THE TREE IS A RECORD, containers included, in depth-first order. A node out of
    shape is an `Unreadable` naming its path, and its children are still walked, so one bad part
    does not hide its siblings or descendants. `body.data` is decoded from base64url; text that
    does not decode is `Unreadable`, never passed on as it stands.

    Returns:
        `Part` per readable node, `Unreadable` per node out of shape, in tree order.

    """
    rec = _record(value)
    if rec is None:
        return [Unreadable(id=None, reason="response is not a JSON object")]
    raw_id = rec.get("id")
    msg_id = raw_id if isinstance(raw_id, str) else None
    if "payload" not in rec:
        return [Unreadable(id=msg_id, reason="payload is missing")]
    out: list[Part | Unreadable] = []
    _walk(rec["payload"], (), msg_id, out)
    return out

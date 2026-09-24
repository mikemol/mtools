# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 3: a record's content, decoded into blocks, whole, each with the path it came from.

Replaces substrate's `blocks()`, which differed in three ways that each hid content:

- it read only `message.content`, so an attachment's `prompt`, where a queued command's text
  lives, decoded to nothing. Here an attachment's prompt is content like any other;
- it TRUNCATED silently: a `tool_use` input at 20,000 characters, an unknown block at 4,000,
  with no mark. Here nothing is truncated. A reader that wants a preview cuts it, knowingly;
- it collapsed a block it did not understand into a string and called it decoded. Here such a
  block is kept with `decoded=False`, so the population a later stage counts as UNDECODED is
  exactly the set of blocks this module could not read.

Every block carries its path from the envelope's root, in `walk`'s spelling, so a later stage
can subtract the paths decoded here from every string the walk finds.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct.records import AssistantRecord, AttachmentRecord, UserRecord

if TYPE_CHECKING:
    from mikemol.transcriptstruct.records import Content, Record
    from mikemol.transcriptstruct.walk import Path

# The block types whose text sits in one field of the same name.
_TEXT_FIELD = {"text": "text", "thinking": "thinking"}


@dataclass(frozen=True, slots=True)
class Block:
    """One content block: its kind, its whole text, where it sits, and whether it was understood.

    `kind` is the block's `type` (`text`, `thinking`, `tool_use`, `tool_result`, ...). A
    `tool_result` sub-block that is not text is `tool_result:<its type>`. An undecoded block's
    `text` is its whole JSON, so nothing about it is lost.
    """

    kind: str
    text: str
    path: Path
    decoded: bool


def _dump(value: object) -> str:
    """Serialise a value whole, keeping non-ASCII text as written.

    Returns:
        the JSON text, never truncated.

    """
    return json.dumps(value, ensure_ascii=False)


# The tool_result sub-block types this module reads: each type's block kind, and the one field
# that holds its content. `tool_reference` names a tool a tool search loaded (measured: the whole
# undecoded population of a real transcript was these 80), so its name is its content.
_SUB_FIELD = {
    "text": ("tool_result", "text"),
    "tool_reference": ("tool_result:tool_reference", "tool_name"),
}


def _sub_block(sub: object, where: Path) -> Block:
    """Decode one element of a `tool_result`'s content list.

    Returns:
        a decoded block for a text or tool_reference element; else `tool_result:<type>`,
        undecoded, carrying the element's whole JSON.

    """
    body = cast("dict[str, object]", sub) if isinstance(sub, dict) else {}
    kind = body.get("type")
    known = _SUB_FIELD.get(kind) if isinstance(kind, str) else None
    text = body.get(known[1]) if known else None
    if known and isinstance(text, str):
        return Block(known[0], text, (*where, known[1]), decoded=True)
    return Block(f"tool_result:{body.get('type', '?')}", _dump(sub), where, decoded=False)


def _tool_result(body: dict[str, object], path: Path) -> list[Block]:
    """Decode a `tool_result`, whose content is a string or a list of sub-blocks.

    Returns:
        one block for a string; one per sub-block for a list; one undecoded block otherwise.

    """
    content = body.get("content")
    where = (*path, "content")
    if isinstance(content, str):
        return [Block("tool_result", content, where, decoded=True)]
    if not isinstance(content, list):
        return [Block("tool_result", _dump(content), where, decoded=False)]
    items = cast("list[object]", content)
    return [_sub_block(sub, (*where, index)) for index, sub in enumerate(items)]


def _block(item: object, path: Path) -> list[Block]:
    """Decode one element of a content list.

    Returns:
        the blocks it holds: usually one, several for a `tool_result` with a list inside.

    """
    if not isinstance(item, dict):
        return [Block("?", _dump(item), path, decoded=False)]
    body = cast("dict[str, object]", item)
    kind = body.get("type")
    field = _TEXT_FIELD.get(kind) if isinstance(kind, str) else None
    text = body.get(field) if field else None
    if field and isinstance(text, str):
        return [Block(field, text, (*path, field), decoded=True)]
    if kind == "tool_use":
        return [Block("tool_use", _dump(body.get("input", {})), (*path, "input"), decoded=True)]
    if kind == "tool_result":
        return _tool_result(body, path)
    return [Block(kind if isinstance(kind, str) else "?", _dump(item), path, decoded=False)]


def decode_content(content: Content, path: Path) -> tuple[Block, ...]:
    """Decode a content field found at `path`: a string is one text block; a list, its elements.

    Returns:
        the blocks, in document order.

    """
    if isinstance(content, str):
        return (Block("text", content, path, decoded=True),)
    out: list[Block] = []
    for index, item in enumerate(content):
        out.extend(_block(item, (*path, index)))
    return tuple(out)


def blocks(record: Record) -> tuple[Block, ...]:
    """Decode a record's content wherever its kind keeps it.

    Returns:
        a user or assistant record's `message.content`, an attachment's `attachment.prompt`,
        and nothing for an attachment without a prompt, an unknown record or a malformed line.

    """
    if isinstance(record, (UserRecord, AssistantRecord)):
        return decode_content(record.content, ("message", "content"))
    if isinstance(record, AttachmentRecord) and record.prompt is not None:
        return decode_content(record.prompt, ("attachment", "prompt"))
    return ()

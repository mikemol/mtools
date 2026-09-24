# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 3: content decodes whole, attachments too, and nothing unread passes as read.

Every fixture is SYNTHETIC and built inline. Real transcript excerpts are held by substrate's
operator and do not enter this tree.
"""

from __future__ import annotations

import json

from mikemol.transcriptstruct.blocks import Block, blocks
from mikemol.transcriptstruct.records import AssistantRecord, parse_line
from mikemol.transcriptstruct.walk import strings

_OLD_TOOL_USE_CAP = 20_000
_OLD_UNKNOWN_CAP = 4_000
_CONTENT = ("message", "content")


def _user(content: object) -> str:
    """Build a synthetic user line.

    Returns:
        the JSONL line.

    """
    message: dict[str, object] = {"role": "user", "content": content}
    envelope: dict[str, object] = {"type": "user", "message": message}
    return json.dumps(envelope)


def _assistant(content: object) -> str:
    """Build a synthetic assistant line.

    Returns:
        the JSONL line.

    """
    message: dict[str, object] = {"role": "assistant", "content": content}
    envelope: dict[str, object] = {"type": "assistant", "message": message}
    return json.dumps(envelope)


def test_a_string_content_is_one_text_block() -> None:
    """A bare string `content` is one decoded text block at `message.content`."""
    expected = (Block("text", "hello", _CONTENT, decoded=True),)
    assert blocks(parse_line(_user("hello"), 1)) == expected


def test_text_and_thinking_blocks_decode_at_their_field_paths() -> None:
    """Typed text and thinking blocks decode to their text, at `[i].thinking` and `[i].text`."""
    content = [{"type": "thinking", "thinking": "t"}, {"type": "text", "text": "x"}]
    assert blocks(parse_line(_assistant(content), 1)) == (
        Block("thinking", "t", (*_CONTENT, 0, "thinking"), decoded=True),
        Block("text", "x", (*_CONTENT, 1, "text"), decoded=True),
    )


def test_a_queued_command_prompt_decodes_as_content() -> None:
    """An attachment's prompt is content; the old reader, keyed on `message`, decoded nothing."""
    attachment = {"type": "queued_command", "prompt": [{"type": "text", "text": "drain it"}]}
    envelope: dict[str, object] = {"type": "attachment", "message": None, "attachment": attachment}
    line = json.dumps(envelope)
    assert blocks(parse_line(line, 1)) == (
        Block("text", "drain it", ("attachment", "prompt", 0, "text"), decoded=True),
    )


def test_a_long_tool_use_input_is_not_truncated() -> None:
    """A tool_use input past the old 20,000-character cap decodes whole.

    ⚑ The old reader cut it at 20,000 with no mark, so a finding past that point was invisible
    and its absence looked like a fact about the transcript.
    """
    tail = "the finding at the very end"
    content = [{"type": "tool_use", "input": {"command": "x" * _OLD_TOOL_USE_CAP + tail}}]
    (block,) = blocks(parse_line(_assistant(content), 1))
    assert block.kind == "tool_use"
    assert tail in block.text


def test_an_unknown_block_is_kept_whole_and_marked_undecoded() -> None:
    """A block type nobody decodes is kept whole with `decoded=False`, not cut to 4,000."""
    big = "y" * (_OLD_UNKNOWN_CAP + 10)
    (block,) = blocks(parse_line(_user([{"type": "image_note", "note": big}]), 1))
    assert block.kind == "image_note"
    assert not block.decoded
    assert big in block.text


def test_tool_result_text_sub_blocks_decode_and_others_are_undecoded() -> None:
    """A tool_result list decodes its text parts; an image part is undecoded."""
    parts = [{"type": "text", "text": "out"}, {"type": "image", "source": {}}]
    text, image = blocks(parse_line(_user([{"type": "tool_result", "content": parts}]), 1))
    assert text == Block("tool_result", "out", (*_CONTENT, 0, "content", 0, "text"), decoded=True)
    assert image.kind == "tool_result:image"
    assert not image.decoded


def test_every_decoded_path_is_a_string_path_the_walk_finds() -> None:
    """Each decoded block's path is one of the walk's leaf paths, so a later stage can subtract."""
    content = [{"type": "text", "text": "a"}, {"type": "tool_result", "content": "b"}]
    record = parse_line(_assistant(content), 1)
    assert isinstance(record, AssistantRecord)
    walked = {leaf.path for leaf in strings(record.raw)}
    decoded = [block for block in blocks(record) if block.decoded]
    assert len(decoded) == len(content)
    assert all(block.path in walked for block in decoded)


def test_an_unknown_record_has_no_blocks() -> None:
    """A record this package does not decode yields no blocks; the walk still sees its strings."""
    assert blocks(parse_line('{"type": "summary", "summary": "s"}', 1)) == ()

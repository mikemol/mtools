# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 1: every line yields one tagged record, and the blind shapes decode.

Every fixture is SYNTHETIC and built inline, shaped after census-kit's transcript-shapes
reference. Real transcript excerpts are held by substrate's operator and do not enter this tree.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.transcriptstruct.records import (
    AssistantRecord,
    AttachmentRecord,
    MalformedLine,
    UnknownRecord,
    UserRecord,
    decode,
    parse_line,
    parse_lines,
    read_path,
)

if TYPE_CHECKING:
    from pathlib import Path

_DIRECTIVE = "synthetic directive typed mid-turn: drain the tier"
_PEER = "synthetic cross-session message from a peer"
# Line numbers other than 1, so a record numbered from its own position cannot pass by accident.
_ATTACHMENT_AT = 7
_UNKNOWN_AT = 3
_TORN_AT = 2


def _line(env: dict[str, object]) -> str:
    """Serialise one synthetic envelope as a JSONL line.

    Returns:
        the JSON text.

    """
    return json.dumps(env)


def _queued(prompt: object, origin: object) -> dict[str, object]:
    """Build a shape-1 envelope: `type: attachment`, `queued_command`, `message: null`.

    Returns:
        the envelope.

    """
    return {
        "type": "attachment",
        "message": None,
        "attachment": {"type": "queued_command", "prompt": prompt, "origin": origin},
    }


def test_shape1_a_queued_command_with_null_message_is_an_attachment_record() -> None:
    """Shape 1: an attachment with `message: null` decodes, and its prompt text is kept."""
    rec = parse_line(_line(_queued(_DIRECTIVE, {"kind": "human"})), _ATTACHMENT_AT)
    assert isinstance(rec, AttachmentRecord)
    assert rec.line == _ATTACHMENT_AT
    assert rec.attachment_type == "queued_command"
    assert rec.prompt == _DIRECTIVE


def test_shape2_origin_is_read_where_it_is_nested() -> None:
    """Shape 2: `origin.kind` is read from inside `attachment`, where the harness puts it."""
    rec = parse_line(_line(_queued(_PEER, {"kind": "peer"})), 1)
    assert isinstance(rec, AttachmentRecord)
    assert rec.origin_kind == "peer"


def test_shape2_a_top_level_origin_is_not_mistaken_for_the_nested_one() -> None:
    """Shape 2 contrast: a top-level `origin` is not the provenance; the nested absence stands."""
    env = _queued(_DIRECTIVE, None)
    env["origin"] = {"kind": "human"}
    rec = parse_line(_line(env), 1)
    assert isinstance(rec, AttachmentRecord)
    assert rec.origin_kind is None


def test_shape3_a_list_prompt_decodes_to_its_blocks() -> None:
    """Shape 3: a LIST prompt is kept as its blocks, so the text is content, not a dict repr."""
    blocks = [{"type": "text", "text": _DIRECTIVE}]
    rec = parse_line(_line(_queued(blocks, {"kind": "human"})), 1)
    assert isinstance(rec, AttachmentRecord)
    assert rec.prompt == ({"type": "text", "text": _DIRECTIVE},)


def test_an_attachment_without_a_prompt_decodes_with_prompt_none() -> None:
    """An attachment of another kind, with no prompt, still decodes rather than vanishing."""
    env: dict[str, object] = {"type": "attachment", "attachment": {"type": "hook_output"}}
    rec = parse_line(_line(env), 1)
    assert isinstance(rec, AttachmentRecord)
    assert rec.prompt is None
    assert rec.attachment_type == "hook_output"


def test_a_user_record_keeps_tool_result_blocks_as_content() -> None:
    """Shape 4: tool output wearing the user role is a UserRecord whose blocks are kept whole."""
    block = {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}
    env: dict[str, object] = {"type": "user", "message": {"role": "user", "content": [block]}}
    rec = parse_line(_line(env), 1)
    assert isinstance(rec, UserRecord)
    assert rec.content == (block,)


def test_a_compact_summary_is_flagged() -> None:
    """Shape 6: `isCompactSummary` is carried on the record, so stage 4 can label it testimony."""
    env: dict[str, object] = {
        "type": "user",
        "isCompactSummary": True,
        "message": {"role": "user", "content": "summary text"},
    }
    rec = parse_line(_line(env), 1)
    assert isinstance(rec, UserRecord)
    assert rec.is_compact_summary
    assert rec.content == "summary text"


def test_an_assistant_record_keeps_tool_use_interiors() -> None:
    """Shape 7: `tool_use` inputs stay in the assistant content, whole and untruncated."""
    big = "x" * 50_000
    block = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": big}}
    env: dict[str, object] = {
        "type": "assistant",
        "isSidechain": True,
        "message": {"role": "assistant", "content": [block]},
    }
    rec = parse_line(_line(env), 1)
    assert isinstance(rec, AssistantRecord)
    assert rec.is_sidechain
    assert rec.content == (block,)


def test_an_unknown_type_yields_an_unknown_record() -> None:
    """An undecoded `type` becomes an explicit UnknownRecord carrying the type and the envelope."""
    env: dict[str, object] = {"type": "file-history-snapshot", "snapshot": {}}
    rec = parse_line(_line(env), _UNKNOWN_AT)
    assert isinstance(rec, UnknownRecord)
    assert rec.type == "file-history-snapshot"
    assert rec.line == _UNKNOWN_AT
    assert rec.raw == env


def test_a_missing_type_and_a_non_object_are_unknown() -> None:
    """A line with no `type`, and a JSON value that is not an object, are Unknown, not dropped."""
    no_type = decode({"message": None}, 1)
    array = decode([1, 2], 2)
    assert isinstance(no_type, UnknownRecord)
    assert no_type.type is None
    assert isinstance(array, UnknownRecord)
    assert array.raw == [1, 2]


def test_a_known_type_with_a_wrong_shape_is_unknown_with_the_reason() -> None:
    """A user record whose `message` is null is Unknown with a reason, not a silent empty user."""
    rec = decode({"type": "user", "message": None}, 1)
    bad_att = decode({"type": "attachment", "attachment": {"prompt": 5}}, 2)
    assert isinstance(rec, UnknownRecord)
    assert rec.type == "user"
    assert "message" in rec.reason
    assert isinstance(bad_att, UnknownRecord)
    assert "attachment.prompt" in bad_att.reason


def test_malformed_json_is_reported_with_its_line_number() -> None:
    """A torn line is a MalformedLine at its 1-based number; the lines around it still decode."""
    good = _line(_queued(_DIRECTIVE, {"kind": "human"}))
    torn = good[: len(good) // 2]
    records = list(parse_lines([good + "\n", torn + "\n", good + "\n"]))
    assert [type(r) for r in records] == [AttachmentRecord, MalformedLine, AttachmentRecord]
    bad = records[1]
    assert isinstance(bad, MalformedLine)
    assert bad.line == _TORN_AT
    assert bad.text == torn
    assert bad.error


def test_a_blank_line_is_malformed_not_skipped() -> None:
    """A blank line is counted as malformed, so output count equals input line count."""
    records = list(parse_lines(["\n"]))
    assert [type(r) for r in records] == [MalformedLine]


def test_every_line_of_a_file_yields_exactly_one_record(tmp_path: Path) -> None:
    """Positive control: a mixed file of N lines reads back as N records, in order, numbered."""
    lines = [
        _line({"type": "user", "message": {"role": "user", "content": "hi"}}),
        _line(_queued([{"type": "text", "text": _DIRECTIVE}], {"kind": "human"})),
        "{not json",
        _line({"type": "system", "subtype": "x"}),
        _line({"type": "assistant", "message": {"role": "assistant", "content": []}}),
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    records = list(read_path(path))
    assert [r.line for r in records] == list(range(1, len(lines) + 1))
    assert [type(r) for r in records] == [
        UserRecord,
        AttachmentRecord,
        MalformedLine,
        UnknownRecord,
        AssistantRecord,
    ]


def test_an_undecodable_line_is_reported_not_replaced(tmp_path: Path) -> None:
    """A line of invalid UTF-8 is a MalformedLine naming the byte; its neighbours still decode.

    ⚑⚑ TS1-d: replacement characters would parse into a silently altered record reading as
    genuine. Reported per line, so one torn line does not cost the file.
    """
    good = _line({"type": "user", "message": {"role": "user", "content": "hi"}}).encode()
    torn = b'{"type": "user", "text": "caf\xe9"}'
    path = tmp_path / "t.jsonl"
    path.write_bytes(b"\n".join([good, torn, good]) + b"\n")
    records = list(read_path(path))
    assert [type(r) for r in records] == [UserRecord, MalformedLine, UserRecord]
    torn_record = records[1]
    assert isinstance(torn_record, MalformedLine)
    assert torn_record.line == _TORN_AT
    assert "invalid UTF-8 at byte" in torn_record.error

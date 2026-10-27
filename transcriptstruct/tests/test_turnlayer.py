# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An announced next action the SAME assistant turn carries out is discharged, not debt (W2052).

⚑ THE CONTROLS (github-8f's ruling): the announce is discharged only by a LATER tool_use before
the turn ends; a tool result does not end the turn, a human prompt does, a subagent's tool call is
not the turn's, a record carrying both the sentence and the call is discharged by itself, an owed
row is never turned, and a discharged announce is not counted whatever else it names.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct import commitledger, commitrows, turnlayer
from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.records import parse_lines

if TYPE_CHECKING:
    from pathlib import Path

_PROMPT = 1
_ANNOUNCE = 2
_AFTER_RESULT = 4


def _user(text: str) -> str:
    body: dict[str, object] = {"type": "user", "message": {"role": "user", "content": text}}
    return json.dumps(body)


def _result() -> str:
    blocks = [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]
    body: dict[str, object] = {
        "type": "user",
        "message": {"role": "user", "content": blocks},
        "toolUseResult": "ok",
    }
    return json.dumps(body)


def _assistant(*blocks: dict[str, object], sidechain: bool = False) -> str:
    body: dict[str, object] = {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {"role": "assistant", "content": list(blocks)},
    }
    return json.dumps(body)


_TEXT: dict[str, object] = {"type": "text", "text": "Running each alone."}
_TOOL: dict[str, object] = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}


def _found(lines: list[str], asked: set[int]) -> set[int]:
    return turnlayer.discharged(parse_lines(lines), asked)


def test_an_announce_followed_by_a_tool_call_in_the_same_turn_is_discharged() -> None:
    """Line 2 says it, line 3 does it, before the turn ends."""
    lines = [_user("go"), _assistant(_TEXT), _assistant(_TOOL), _result(), _assistant(_TEXT)]
    assert _found(lines, {_ANNOUNCE}) == {_ANNOUNCE}


def test_an_announce_that_ends_the_turn_is_not_discharged() -> None:
    """The next tool call is the NEXT turn's, after a new prompt: the sentence stays debt."""
    lines = [_user("go"), _assistant(_TEXT), _user("again"), _assistant(_TOOL)]
    assert _found(lines, {_ANNOUNCE}) == set()


def test_a_tool_result_does_not_end_the_turn() -> None:
    """A call, its result, then an announce and another call: all one turn."""
    lines = [_user("go"), _assistant(_TOOL), _result(), _assistant(_TEXT), _assistant(_TOOL)]
    assert _found(lines, {_AFTER_RESULT}) == {_AFTER_RESULT}


def test_a_tool_result_between_the_sentence_and_the_call_does_not_end_the_turn() -> None:
    """The result sits between line 2 and the call at line 4: still one turn, still discharged."""
    lines = [_user("go"), _assistant(_TEXT), _result(), _assistant(_TOOL)]
    assert _found(lines, {_ANNOUNCE}) == {_ANNOUNCE}


def test_a_subagents_tool_call_does_not_discharge_the_sessions_announce() -> None:
    """Sidechain records are another agent's work."""
    lines = [_user("go"), _assistant(_TEXT), _assistant(_TOOL, sidechain=True)]
    assert _found(lines, {_ANNOUNCE}) == set()


def test_a_record_holding_both_the_sentence_and_the_call_is_discharged_by_itself() -> None:
    """The announcement and the call in one record."""
    lines = [_user("go"), _assistant(_TEXT, _TOOL)]
    assert _found(lines, {_ANNOUNCE}) == {_ANNOUNCE}


def test_a_line_that_is_not_an_assistant_record_is_never_discharged() -> None:
    """Asking about the prompt's own line answers nothing."""
    lines = [_user("go"), _assistant(_TEXT), _assistant(_TOOL)]
    assert _found(lines, {_PROMPT}) == set()


def _body(line: int, kind: str | None, names: list[str] | None = None) -> dict[str, object]:
    return {
        "line": line,
        "uuid": "u",
        "session": "",
        "repo": "mtools",
        "family": "amr",
        "text": "",
        "names": names or [],
        "at": "",
        "kind": kind,
    }


def _row(line: int, kind: str | None, names: list[str] | None = None) -> str:
    return json.dumps(_body(line, kind, names))


def test_the_rows_file_carries_a_kind_that_defaults_to_owed() -> None:
    """`announce` is read; an absent kind is owed; a non-string kind refuses the file."""
    rows, why = commitrows.read([_row(2, "announce"), _row(3, "owed")], "mtools")
    assert not why
    assert [r.kind for r in rows] == ["announce", "owed"]
    bare = _body(4, "x")
    del bare["kind"]
    assert [r.kind for r in commitrows.read([json.dumps(bare)], "mtools")[0]] == ["owed"]
    assert commitrows.read([_row(4, None)], "mtools")[0] == []


def test_only_a_discharged_announce_is_turned_and_it_is_not_counted() -> None:
    """An owed row on the same line stays open; a discharged announce naming memory is not debt."""
    rows, _ = commitrows.read(
        [_row(2, "announce", ["MEMORY.md"]), _row(5, "owed"), _row(7, "announce")], "mtools"
    )
    ledger = commitrows.resolve(rows, [], {2, 5})
    assert [(r.layer, r.state) for r in ledger] == [
        (commitledger.TURN, "resolved"),
        ("none", "open"),
        ("none", "open"),
    ]
    assert commitledger.counted(ledger) == {"none": 2}


def test_the_command_reads_the_transcript_and_prints_the_discharged_split(tmp_path: Path) -> None:
    """`--resolve --turns T` marks the announce the turn carried out; the other stays unattached."""
    transcript = tmp_path / "t.jsonl"
    lines = [_user("go"), _assistant(_TEXT), _assistant(_TOOL), _user("again"), _assistant(_TEXT)]
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows_file, queue = tmp_path / "rows.jsonl", tmp_path / "q.json"
    rows_file.write_text(_row(2, "announce") + "\n" + _row(5, "announce") + "\n", encoding="utf-8")
    empty: dict[str, object] = {"waypoints": list[object]()}
    queue.write_text(json.dumps(empty), encoding="utf-8")
    out = io.StringIO()
    args = [str(rows_file), "--resolve", "--queue", str(queue), "--repo", "mtools"]
    assert main([*args, "--turns", str(transcript)], out) == 0
    document, tally = out.getvalue().splitlines()
    parsed = cast("dict[str, object]", json.loads(document))
    listed = cast("list[dict[str, object]]", parsed["rows"])
    assert [r["layer"] for r in listed] == ["turn", "none"]
    assert [r["kind"] for r in listed] == ["announce", "announce"]
    assert tally == "# 1 counted: {'none': 1}, 0 uncertain"

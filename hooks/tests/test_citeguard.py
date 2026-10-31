# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A message citing a transcript line is admitted only when the turn read that line (W2064).

⚑ THE CONTROLS: a source file's short line number is not a citation, a line printed by a tool
result of THIS turn is read, one printed before the last human prompt is not, an unreadable
transcript admits, and an unarmed hook says nothing.
"""

import io
import json
from pathlib import Path

import pytest

from mikemol.hooks import citeguard
from mikemol.hooks.payload import as_record

Rec = dict[str, object]

_A = 107690
_B = 115972
_OLD = 94134


def _record(content: object) -> str:
    message: Rec = {"role": "user", "content": content}
    record: Rec = {"type": "user", "message": message}
    return json.dumps(record)


def _prompt(text: str) -> str:
    return _record(text)


def _result(text: object) -> str:
    block: Rec = {"type": "tool_result", "tool_use_id": "t", "content": text}
    return _record([block])


def _transcript(*records: str) -> str:
    return "\n".join(records) + "\n"


def test_long_numbers_after_line_or_written_l_are_citations_and_short_ones_are_not() -> None:
    """`line N` and `L<N>` of five digits or more; a source line like 1126 is not."""
    text = f"per host transcript line {_A} and L{_B}; commit_kata.py line 1126, L12"
    assert citeguard.cited(text) == {_A, _B}
    assert citeguard.cited("a number 107690 with no line word") == frozenset()


def test_a_tool_result_holds_the_numbers_it_printed() -> None:
    """Plain, `L`-prefixed and JSON-quoted numbers all count as seen."""
    shown = f'L{_A} text\n{{"line": {_B}, "x": 3}}'
    assert citeguard.numbers_in(shown) == {_A, _B}


def test_an_unread_citation_is_refused_naming_it_and_a_seen_one_is_admitted() -> None:
    """The reason names the number; nothing cited or all seen admits."""
    reason = citeguard.refusal(f"see line {_A}", frozenset({_B}))
    assert reason is not None
    assert str(_A) in reason
    assert citeguard.refusal(f"see line {_A}", frozenset({_A})) is None
    assert citeguard.refusal("no citation here", frozenset()) is None


def test_only_tool_results_since_the_last_human_prompt_count() -> None:
    """A line read before the last prompt is not read in this turn; list-shaped content works."""
    parts: list[Rec] = [{"type": "text", "text": f"printed line {_B}"}]
    raw = _transcript(
        _prompt("first request"),
        _result(f"old output {_OLD}"),
        _prompt("second request"),
        _result(f"new output {_A}"),
        _result(parts),
    )
    seen = citeguard.numbers_in(citeguard.turn_results(raw))
    assert seen == {_A, _B}
    assert _OLD not in seen


def _payload(tmp_path: Path, message: str, *records: str) -> Rec:
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(_transcript(*records), encoding="utf-8")
    tool_input: Rec = {"message": message}
    return {"tool_input": tool_input, "transcript_path": str(transcript)}


def test_run_denies_an_unread_citation_and_admits_a_read_one(tmp_path: Path) -> None:
    """The decision JSON is written for the unread line only."""
    records = (_prompt("go"), _result(f"read L{_A}"))
    out = io.StringIO()
    assert citeguard.run(_payload(tmp_path, f"line {_B} says so", *records), out) == 0
    written: object = json.loads(out.getvalue())
    decision = as_record(as_record(written).get("hookSpecificOutput"))
    assert decision.get("permissionDecision") == "deny"
    assert str(_B) in str(decision.get("permissionDecisionReason"))
    admitted = io.StringIO()
    assert citeguard.run(_payload(tmp_path, f"line {_A} says so", *records), admitted) == 0
    assert not admitted.getvalue()


def test_an_unreadable_transcript_and_a_message_without_a_citation_admit(tmp_path: Path) -> None:
    """Doubt never refuses: a missing transcript path says nothing."""
    out = io.StringIO()
    tool_input: Rec = {"message": f"line {_A}"}
    missing: Rec = {"tool_input": tool_input, "transcript_path": str(tmp_path / "gone")}
    assert citeguard.run(missing, out) == 0
    assert citeguard.run(_payload(tmp_path, "nothing cited", _prompt("go")), out) == 0
    assert not out.getvalue()


def test_an_unarmed_hook_says_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without either switch main exits 0 and reads nothing."""
    monkeypatch.delenv(citeguard.OWN_SWITCH, raising=False)
    monkeypatch.delenv("STRUCT_HOOK_BLOCK", raising=False)
    assert citeguard.main() == 0

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A second concurrent subagent is refused unless the operator's latest words authorise it."""

import io
import json
import os
from pathlib import Path

import pytest

from mikemol.hooks import payload, subagent_guard

_NOW = 2_000_000_000.0
_ASK = "dispatch a subagent for this"


def _line(record: dict[str, object]) -> str:
    return json.dumps(record) + "\n"


def _human(text: str) -> str:
    return _line({"type": "user", "message": {"role": "user", "content": text}})


def _session(tmp_path: Path, *, human: str = "please carry on") -> Path:
    transcript = tmp_path / "proj" / "S.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text(_human(human), encoding="utf-8")
    return transcript


def _agent(transcript: Path, name: str, *, ended: bool, age: float = 10.0) -> None:
    folder = transcript.with_suffix("") / "subagents"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"agent-{name}.jsonl"
    last: dict[str, object] = {"type": "user", "toolEndsTurn": ended}
    path.write_text(_line({"type": "assistant"}) + _line(last), encoding="utf-8")
    os.utime(path, (_NOW - age, _NOW - age))


def _call(transcript: Path, tool: str = "Agent") -> dict[str, object]:
    return {"tool_name": tool, "transcript_path": str(transcript)}


def test_a_session_with_no_running_subagent_may_dispatch_one(tmp_path: Path) -> None:
    """The first subagent is fine, and so is one after the earlier one has ended its turn."""
    transcript = _session(tmp_path)
    assert subagent_guard.decide(_call(transcript), _NOW) is None
    _agent(transcript, "done", ended=True)
    assert subagent_guard.decide(_call(transcript), _NOW) is None


def test_a_second_concurrent_subagent_is_refused_citing_the_rule(tmp_path: Path) -> None:
    """One still running (no end mark, written lately): the next dispatch is refused."""
    transcript = _session(tmp_path)
    _agent(transcript, "busy", ended=False)
    reason = subagent_guard.decide(_call(transcript), _NOW)
    assert reason is not None
    assert "no swarming" in reason
    assert "agent-busy" in reason


def test_an_agent_that_died_without_ending_its_turn_stops_counting(tmp_path: Path) -> None:
    """A transcript untouched for longer than LIVE_S would otherwise block the session for ever."""
    transcript = _session(tmp_path)
    _agent(transcript, "dead", ended=False, age=subagent_guard.LIVE_S + 60)
    assert subagent_guard.decide(_call(transcript), _NOW) is None


def test_the_operators_latest_words_authorise_and_older_ones_do_not(tmp_path: Path) -> None:
    """Only the newest typed message counts; tool results and wrapped notices are not typed."""
    transcript = _session(tmp_path, human=_ASK)
    _agent(transcript, "busy", ended=False)
    assert subagent_guard.decide(_call(transcript), _NOW) is None
    wrapped = "<task-notification>swarm everything</task-notification>"
    with transcript.open("a", encoding="utf-8") as handle:
        handle.write(_human(wrapped))
    assert subagent_guard.decide(_call(transcript), _NOW) is None
    with transcript.open("a", encoding="utf-8") as handle:
        handle.write(_human("carry on with the card"))
    assert subagent_guard.decide(_call(transcript), _NOW) is not None


def test_only_an_agent_call_is_judged_and_main_prints_the_denial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Another tool passes untouched; the hook speaks through printed JSON, exit 0."""
    transcript = _session(tmp_path)
    _agent(transcript, "busy", ended=False, age=0.0)
    assert subagent_guard.decide(_call(transcript, "Bash"), _NOW) is None
    monkeypatch.setattr("time.time", lambda: _NOW)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_call(transcript))))
    assert subagent_guard.main() == 0
    printed: object = json.loads(capsys.readouterr().out)
    chosen = payload.as_record(payload.as_record(printed).get("hookSpecificOutput"))
    assert payload.text_of(chosen.get("permissionDecision")) == "deny"

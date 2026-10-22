# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W513, W1832: standing rule 8 at Stop — a human hold set this turn states its ask and sends it.

Each fixture is a transcript JSONL written in tmp_path. The launcher's end-to-end witness is
`hooks/tests/test_standing_stop_launcher.py`, beside the launcher.

⚑ THE CARD IS THE ASK (operator 2026-10-22, host 695f3e0a line 90544): a hold with a well-formed
`--blocked-on 'operator: decide|act ...'` and a push naming it is met, and an AskUserQuestion meets
nothing, since a pending question froze a session for 84 minutes.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from mikemol.transcriptstruct.standing_stop import ask_formed, decide, main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_BARE = "mikemol-paths-forward --update W7 --status blocked --blocked-kind human --next n"
_HOLD = f"{_BARE} --blocked-on 'operator: decide keep or drop W7'"


def _user(text: str) -> dict[str, object]:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _tool(name: str, body: dict[str, object]) -> dict[str, object]:
    block = {"type": "tool_use", "id": "t", "name": name, "input": body}
    return {"type": "assistant", "message": {"role": "assistant", "content": [block]}}


def _result() -> dict[str, object]:
    block = {"type": "tool_result", "tool_use_id": "t", "content": "ok"}
    return {"type": "user", "message": {"role": "user", "content": [block]}}


def _ask(text: str) -> dict[str, object]:
    return _tool("AskUserQuestion", {"questions": [{"question": text}]})


def _push(text: str) -> dict[str, object]:
    return _tool("PushNotification", {"message": text})


def _transcript(tmp_path: Path, rows: list[dict[str, object]]) -> dict[str, object]:
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return {"hook_event_name": "Stop", "transcript_path": str(path), "stop_hook_active": False}


def _blocked(tmp_path: Path, rows: list[dict[str, object]]) -> str:
    decision, _ = decide(_transcript(tmp_path, rows))
    assert decision is not None
    assert decision["decision"] == "block"
    return decision["reason"]


def test_a_hold_with_a_stated_ask_and_a_push_naming_it_does_not_block(tmp_path: Path) -> None:
    """The card is the ask and the push carries it: nothing more is required."""
    rows = [_user("go"), _tool("Bash", {"command": _HOLD}), _result(), _push("W7: keep or drop?")]
    assert decide(_transcript(tmp_path, rows)) == (None, None)


def test_a_hold_with_no_push_blocks_naming_the_card_and_the_push(tmp_path: Path) -> None:
    """An ask nobody was told of waits for the operator to notice it by eye."""
    reason = _blocked(tmp_path, [_user("go"), _tool("Bash", {"command": _HOLD}), _result()])
    assert "W7 (no PushNotification naming it)" in reason


def test_a_hold_with_no_stated_ask_blocks_naming_the_ask(tmp_path: Path) -> None:
    """A bare `blocked_kind human` asks for nothing, which nemik files as unstated."""
    rows = [_user("go"), _tool("Bash", {"command": _BARE}), _result(), _push("W7 needs you")]
    assert "W7 (no `--blocked-on 'operator: decide|act ...'` ask)" in _blocked(tmp_path, rows)


def test_an_ask_question_never_meets_the_rule_and_the_reason_forbids_it(tmp_path: Path) -> None:
    """A blocking AskUserQuestion naming the card pairs nothing; the reason says never to ask."""
    rows = [_user("go"), _tool("Bash", {"command": _HOLD}), _result(), _ask("W7: which way?")]
    reason = _blocked(tmp_path, rows)
    assert "Never AskUserQuestion" in reason
    assert "no PushNotification naming it" in reason


def test_a_push_naming_another_card_does_not_meet_the_hold(tmp_path: Path) -> None:
    """A push about W8 leaves the W7 hold without its push."""
    rows = [_user("go"), _tool("Bash", {"command": _HOLD}), _result(), _push("W8: which way?")]
    assert "W7 (no PushNotification naming it)" in _blocked(tmp_path, rows)


def test_the_ask_is_formed_only_by_decide_or_act_with_something_after() -> None:
    """`operator: decide <q>` and `operator: act <cmd>` are asks, bare `operator` is not."""
    assert ask_formed(f"{_BARE} --blocked-on 'operator: act run the apply loop'")
    assert ask_formed(f"{_BARE} --blocked-on='operator: decide a or b'")
    assert not ask_formed(f"{_BARE} --blocked-on operator")
    assert not ask_formed(f"{_BARE} --blocked-on 'operator: decide'")
    assert not ask_formed(_BARE)


def test_a_hold_before_the_last_user_message_does_not_count(tmp_path: Path) -> None:
    """A hold set in an earlier turn is outside the span; tool results do not end the span."""
    rows = [_user("go"), _tool("Bash", {"command": _BARE}), _result(), _user("next")]
    assert decide(_transcript(tmp_path, rows)) == (None, None)


def test_a_non_human_hold_does_not_count(tmp_path: Path) -> None:
    """An agent-kind hold is not rule 8's subject."""
    command = _BARE.replace("human", "agent")
    rows = [_user("go"), _tool("Bash", {"command": command})]
    assert decide(_transcript(tmp_path, rows)) == (None, None)


def test_stop_hook_active_never_blocks(tmp_path: Path) -> None:
    """When Claude is already continuing from a Stop block, the hook does not block again."""
    payload = _transcript(tmp_path, [_user("go"), _tool("Bash", {"command": _BARE})])
    payload["stop_hook_active"] = True
    assert decide(payload) == (None, None)


def test_a_missing_transcript_path_blocks_once_naming_why() -> None:
    """No transcript_path, not yet active: block with the reason so the failure surfaces."""
    decision, _ = decide({"hook_event_name": "Stop", "stop_hook_active": False})
    assert decision is not None
    assert (decision["decision"], "not checked" in decision["reason"]) == ("block", True)


def test_a_missing_transcript_path_when_active_ends_the_turn_with_a_note() -> None:
    """No transcript_path while already continuing: no block, the reason as a note."""
    decision, note = decide({"hook_event_name": "Stop", "stop_hook_active": True})
    assert (decision, note is not None and "not checked" in note) == (None, True)


def test_main_prints_the_block_json_on_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() reads the payload from stdin and prints the harness's block decision."""
    payload = _transcript(tmp_path, [_user("go"), _tool("Bash", {"command": _BARE})])
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    code = main()
    assert (code, '"decision": "block"' in capsys.readouterr().out) == (0, True)


def test_main_blocks_once_on_a_payload_that_is_not_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A payload that is not JSON counts as not active, so it blocks naming why."""
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    code = main()
    out = capsys.readouterr().out
    assert (code, '"decision": "block"' in out, "not checked" in out) == (0, True, True)

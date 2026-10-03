# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W513: standing rule 8 at Stop — a human hold set this turn is asked this turn.

Each fixture is a transcript JSONL written in tmp_path. The launcher's end-to-end witness is
`hooks/tests/test_standing_stop_launcher.py`, beside the launcher.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from mikemol.transcriptstruct.standing_stop import decide, main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_HOLD = "mikemol-paths-forward --update W7 --status blocked --blocked-kind human --next n"


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


def _transcript(tmp_path: Path, rows: list[dict[str, object]]) -> dict[str, object]:
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return {"hook_event_name": "Stop", "transcript_path": str(path), "stop_hook_active": False}


def test_an_unpaired_hold_blocks_naming_the_card(tmp_path: Path) -> None:
    """A human hold with no AskUserQuestion since the user spoke blocks, naming W7."""
    payload = _transcript(tmp_path, [_user("go"), _tool("Bash", {"command": _HOLD}), _result()])
    decision, _ = decide(payload)
    assert decision is not None
    assert (decision["decision"], "W7" in decision["reason"]) == ("block", True)


def test_a_paired_hold_does_not_block(tmp_path: Path) -> None:
    """A hold followed by an AskUserQuestion naming the card is paired."""
    rows = [_user("go"), _tool("Bash", {"command": _HOLD}), _result(), _ask("W7: which way?")]
    assert decide(_transcript(tmp_path, rows)) == (None, None)


def test_a_question_naming_another_card_does_not_pair(tmp_path: Path) -> None:
    """An AskUserQuestion about W8 leaves the W7 hold unpaired."""
    rows = [_user("go"), _tool("Bash", {"command": _HOLD}), _result(), _ask("W8: which way?")]
    decision, _ = decide(_transcript(tmp_path, rows))
    assert decision is not None


def test_a_hold_before_the_last_user_message_does_not_count(tmp_path: Path) -> None:
    """A hold set in an earlier turn is outside the span; tool results do not end the span."""
    rows = [_user("go"), _tool("Bash", {"command": _HOLD}), _result(), _user("next")]
    assert decide(_transcript(tmp_path, rows)) == (None, None)


def test_a_non_human_hold_does_not_count(tmp_path: Path) -> None:
    """An agent-kind hold is not rule 8's subject."""
    command = _HOLD.replace("human", "agent")
    rows = [_user("go"), _tool("Bash", {"command": command})]
    assert decide(_transcript(tmp_path, rows)) == (None, None)


def test_stop_hook_active_never_blocks(tmp_path: Path) -> None:
    """When Claude is already continuing from a Stop block, the hook does not block again."""
    payload = _transcript(tmp_path, [_user("go"), _tool("Bash", {"command": _HOLD})])
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
    payload = _transcript(tmp_path, [_user("go"), _tool("Bash", {"command": _HOLD})])
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

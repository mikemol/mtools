# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Where the latest turn began and how many Stop blocks it has had, from the transcript (W1903).

⚑ A TOOL RESULT AND A STOP BLOCK'S FEEDBACK CONTINUE A TURN: only a prompt, a wake, a notification
or a peer message begins one, so a hook counting its own blocks since the start cannot be fooled by
the tool calls in between.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct import turnstart
from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.records import parse_lines

if TYPE_CHECKING:
    from pathlib import Path

_TWO = 2


def _user(content: str, at: str, *, result: bool = False) -> str:
    record: dict[str, object] = {
        "type": "user",
        "timestamp": at,
        "message": {"role": "user", "content": content},
    }
    if result:
        record["toolUseResult"] = "x"
    return json.dumps(record)


def _start(*lines: str) -> turnstart.TurnStart | None:
    return turnstart.turn_start(parse_lines(lines))


def test_the_turn_begins_at_the_last_prompt_not_at_a_tool_result_after_it() -> None:
    """A wake starts the turn; the tool result that follows it does not restart it."""
    found = _start(
        _user("older prompt", "2026-10-24T10:00:00Z"),
        _user("a task-notification arrived", "2026-10-24T11:00:00Z"),
        _user("ok", "2026-10-24T11:05:00Z", result=True),
    )
    assert found == turnstart.TurnStart(_TWO, "2026-10-24T11:00:00Z", 0)


def test_each_stop_block_after_the_start_is_counted_and_a_new_turn_resets_the_count() -> None:
    """The cap's counter is the Stop-hook records since the turn began."""
    blocked = [
        _user("a peer cross-session-message", "2026-10-24T11:00:00Z"),
        _user("Stop hook feedback: work W9", "2026-10-24T11:01:00Z"),
        _user("Stop hook feedback: work W9", "2026-10-24T11:02:00Z"),
    ]
    found = _start(*blocked)
    assert found is not None
    assert found.blocks == _TWO
    again = _start(*blocked, _user("a fresh prompt", "2026-10-24T12:00:00Z"))
    assert again is not None
    assert (again.at, again.blocks) == ("2026-10-24T12:00:00Z", 0)


def test_no_turn_starting_record_answers_none_and_the_command_prints_null(tmp_path: Path) -> None:
    """A transcript of only tool results has no start: never a guessed time."""
    assert _start(_user("ok", "2026-10-24T11:05:00Z", result=True)) is None
    log = tmp_path / "t.jsonl"
    log.write_text(_user("ok", "2026-10-24T11:05:00Z", result=True) + "\n", encoding="utf-8")
    out = io.StringIO()
    assert main([str(log), "--turn-start"], out) == 0
    assert out.getvalue() == "null\n"


def test_the_command_prints_the_start_and_its_blocks_as_one_json_line(tmp_path: Path) -> None:
    """The reader's answer to a Stop hook: line, time and blocks."""
    log = tmp_path / "t.jsonl"
    rows = [_user("a prompt", "2026-10-24T11:00:00Z"), _user("Stop hook x", "2026-10-24T11:01:00Z")]
    log.write_text("\n".join(rows) + "\n", encoding="utf-8")
    out = io.StringIO()
    assert main([str(log), "--turn-start"], out) == 0
    said = cast("dict[str, object]", json.loads(out.getvalue()))
    assert said == {"line": 1, "at": "2026-10-24T11:00:00Z", "blocks": 1}

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A turn's cache use, the gap before it and what woke it, read from the transcript (W1830).

⚑ A TURN IS AN API CALL: a response written as several assistant records repeats one usage, and
counting records would triple a cold call, so records sharing a message id are one turn.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.transcriptstruct import cacheturns
from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.records import parse_lines

if TYPE_CHECKING:
    from pathlib import Path

_BIG = 200_000
_SMALL = 24_000
_WARM_CREATION = 30_000
_AT = "2026-10-22T00:00:00.000Z"
_HOUR_AND_40_S = 3_700.0
_TWO = 2


def _line(record: dict[str, object]) -> str:
    return json.dumps(record)


def _assistant(ident: str, at: str, read: int, create: int, *, sidechain: bool = False) -> str:
    usage = {"cache_read_input_tokens": read, "cache_creation_input_tokens": create}
    message = {"id": ident, "model": "m", "usage": usage, "role": "assistant", "content": []}
    return _line(
        {"type": "assistant", "timestamp": at, "isSidechain": sidechain, "message": message}
    )


def _user(content: str) -> str:
    message = {"role": "user", "content": content}
    return _line({"type": "user", "timestamp": _AT, "message": message})


def _turns(*lines: str) -> list[cacheturns.Turn]:
    return cacheturns.turns(parse_lines(lines))


def test_records_sharing_a_message_id_are_one_turn() -> None:
    """A response of three content blocks repeats its usage on three records: one turn."""
    same = _assistant("a", _AT, 10, 5)
    found = _turns(same, same, _assistant("b", _AT, 1, 1))
    assert [t.cache_read for t in found] == [10, 1]


def test_the_gap_is_to_the_previous_turn_and_the_first_has_none() -> None:
    """The first turn has no gap, the next is seconds after it, and it is never negative."""
    found = _turns(
        _assistant("a", "2026-10-22T00:00:00.000Z", 1, 1),
        _assistant("b", "2026-10-22T01:01:40.000Z", 1, 1),
        _assistant("c", "2026-10-22T01:00:00.000Z", 1, 1),
    )
    assert found[0].gap_s is None
    assert found[1].gap_s == pytest.approx(_HOUR_AND_40_S)
    assert found[_TWO].gap_s == pytest.approx(0.0)


def test_a_turn_that_rebuilt_most_of_its_context_is_cold() -> None:
    """Large creation with small read is cold, a warm read is not, a small creation is not."""
    cold, warm, tiny = _turns(
        _assistant("a", _AT, _SMALL, _BIG),
        _assistant("b", _AT, _BIG, _WARM_CREATION),
        _assistant("c", _AT, 10, 100),
    )
    assert (cold.cold, warm.cold, tiny.cold) == (True, False, False)


def test_what_woke_a_turn_is_read_from_the_user_record_before_it() -> None:
    """A tick prompt, a notification, a peer message and a hook block are named, text is other."""
    lines: list[str] = []
    for ident, text in (
        ("a", "[paths-forward tick] Invoke the skill"),
        ("b", "<task-notification>x</task-notification>"),
        ("c", "<cross-session-message from=x>"),
        ("d", "Stop hook feedback: x"),
        ("e", "hello"),
    ):
        lines += [_user(text), _assistant(ident, _AT, 1, 1)]
    assert [t.woke for t in _turns(*lines)] == [
        "cron",
        "notification",
        "peer",
        "stop-hook",
        "operator-or-other",
    ]


def test_a_sidechain_turn_and_a_record_without_usage_are_not_turns() -> None:
    """A subagent's call is not this session's, and a record with no usage has nothing to read."""
    message = {"id": "z", "role": "assistant"}
    bare = _line({"type": "assistant", "timestamp": _AT, "message": message})
    assert not _turns(_assistant("a", _AT, 1, 1, sidechain=True), bare)


def test_the_mode_prints_a_row_per_turn_and_the_cold_count(tmp_path: Path) -> None:
    """`--cache-turns` ends with '# N turn(s), M cold' so the denominator is on the page."""
    path = tmp_path / "t.jsonl"
    rows = [_assistant("a", _AT, _SMALL, _BIG), _assistant("b", _AT, _BIG, _WARM_CREATION)]
    path.write_text("".join(row + "\n" for row in rows), encoding="utf-8")
    out = io.StringIO()
    assert main([str(path), "--cache-turns"], out) == 0
    lines = out.getvalue().splitlines()
    assert lines[-1] == "# 2 turn(s), 1 cold"
    assert cast("dict[str, object]", json.loads(lines[0]))["cold"] is True

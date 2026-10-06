# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `tick_stop`: only a held, fresh host tick lock blocks the Stop, and only once."""

from __future__ import annotations

import io
import json
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.hooks import entry, hook_argv, tick_stop
from mikemol.hooks.host_facts import HostLock

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
FRESH = "2026-10-06T11:58:00Z"
JUST_FRESH = "2026-10-06T11:30:01Z"
JUST_STALE = "2026-10-06T11:30:00Z"
LONG_DEAD = "2026-10-06T08:00:00Z"


def _held(taken_at: str | None) -> HostLock:
    """Build a held lock with the given stamp.

    Returns:
        a lock held by the host session.

    """
    return HostLock(holder="github-b3", taken_at=taken_at)


def _queue(root: Path, doc: dict[str, object]) -> None:
    """Write `doc` as the queue under `root/.claude`."""
    (root / ".claude").mkdir(exist_ok=True)
    (root / ".claude" / "paths-forward.json").write_text(json.dumps(doc), encoding="utf-8")


def _block_line() -> str:
    """Return the exact line a block prints.

    Returns:
        the JSON decision line, newline included.

    """
    decision: dict[str, str] = {"decision": "block", "reason": tick_stop.REASON}
    return json.dumps(decision) + "\n"


def test_a_fresh_held_lock_gives_the_reason() -> None:
    """A lock taken two minutes ago holds the turn open."""
    assert tick_stop.block_reason(_held(FRESH), NOW) == tick_stop.REASON


def test_the_stale_bound_is_exact_to_the_second() -> None:
    """One second under thirty minutes still blocks; exactly thirty minutes is a dead holder's."""
    assert tick_stop.block_reason(_held(JUST_FRESH), NOW) == tick_stop.REASON
    assert tick_stop.block_reason(_held(JUST_STALE), NOW) is None
    assert tick_stop.block_reason(_held(LONG_DEAD), NOW) is None


def test_no_lock_and_an_unreadable_queue_block_nothing() -> None:
    """Unheld, and a reading that did not happen, both let the turn end."""
    assert tick_stop.block_reason(HostLock(holder=None, taken_at=None), NOW) is None
    assert tick_stop.block_reason(None, NOW) is None


def test_a_stamp_that_cannot_be_read_blocks_nothing() -> None:
    """A missing, junk or zoneless stamp is absent: it must not stop a turn."""
    assert tick_stop.block_reason(_held(None), NOW) is None
    assert tick_stop.block_reason(_held("yesterday"), NOW) is None
    assert tick_stop.block_reason(_held("2026-10-06T11:58:00"), NOW) is None


def test_the_stamp_parses_with_z_or_an_offset_and_refuses_a_zoneless_one() -> None:
    """parse_time reads `Z` and `+00:00` alike and returns None without a zone."""
    z_form = tick_stop.parse_time("2026-10-06T11:58:00Z")
    assert z_form is not None
    assert z_form == tick_stop.parse_time("2026-10-06T11:58:00+00:00")
    assert tick_stop.parse_time("2026-10-06T11:58:00") is None
    assert tick_stop.parse_time("not a time") is None


def test_the_first_stop_with_a_held_lock_prints_the_block(tmp_path: Path) -> None:
    """The decision goes to stdout as JSON, and the exit code stays zero."""
    _queue(tmp_path, {"lock": {"holder": "github-b3", "taken_at": FRESH}})
    out, err = io.StringIO(), io.StringIO()
    code = tick_stop.run({"cwd": str(tmp_path)}, NOW, out, err)
    assert code == 0
    assert out.getvalue() == _block_line()
    assert not err.getvalue()


def test_an_active_stop_hook_says_so_on_stderr_and_does_not_block_again(tmp_path: Path) -> None:
    """Closed once per turn: stop_hook_active turns the block into a note, never a trap."""
    _queue(tmp_path, {"lock": {"holder": "github-b3", "taken_at": FRESH}})
    out, err = io.StringIO(), io.StringIO()
    code = tick_stop.run({"cwd": str(tmp_path), "stop_hook_active": True}, NOW, out, err)
    assert code == 0
    assert not out.getvalue()
    assert err.getvalue() == tick_stop.ACTIVE_NOTE


def test_nothing_is_said_when_the_queue_holds_no_lock_or_does_not_exist(tmp_path: Path) -> None:
    """An unheld queue and a missing queue are both silent."""
    _queue(tmp_path, {"waypoints": []})
    out, err = io.StringIO(), io.StringIO()
    assert tick_stop.run({"cwd": str(tmp_path)}, NOW, out, err) == 0
    empty = tmp_path / "empty"
    empty.mkdir()
    assert tick_stop.run({"cwd": str(empty)}, NOW, out, err) == 0
    assert not out.getvalue()
    assert not err.getvalue()


def test_main_reads_the_payload_on_stdin_and_uses_the_real_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A lock stamped now blocks through main, so the wall clock reaches the decision."""
    taken = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _queue(tmp_path, {"lock": {"holder": "github-b3", "taken_at": taken}})
    stop_payload: dict[str, str] = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(stop_payload)))
    assert tick_stop.main() == 0
    assert capsys.readouterr().out == _block_line()


def test_main_allows_a_payload_that_is_not_json_and_says_so(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A guard that cannot read its input must not trap the turn."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert tick_stop.main() == 0
    captured = capsys.readouterr()
    assert not captured.out
    assert "not JSON" in captured.err


def test_the_console_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The argv contract: a hook takes no arguments, and the refusal names the program."""
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-tick-stop", "--help"])
    assert entry.tick_stop_main() == hook_argv.EXIT_REFUSED
    assert "mikemol-hook-tick-stop" in capsys.readouterr().err

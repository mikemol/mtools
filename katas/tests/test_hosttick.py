# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `hosttick`: the lock, and the order in which a tick closes (W877)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.katas import hosttick
from mikemol.katas.hosttick import Closing, HostQueue

if TYPE_CHECKING:
    from pathlib import Path

_EXECUTABLE = 0o755
_TODAY = "2026-10-09"


def _queue(tmp_path: Path) -> tuple[HostQueue, Path]:
    """Build a host queue whose tool records each call's arguments, one line per call.

    Returns:
        the queue, and the file the tool appends its calls to.

    """
    record = tmp_path / "calls.txt"
    tool = tmp_path / "pf"
    tool.write_text(
        f'#!/bin/sh\necho "$*" >> {record}\necho "ok: $*"\n',
        encoding="utf-8",
    )
    tool.chmod(_EXECUTABLE)
    return HostQueue(tool, tmp_path / "state.json", "github-b3"), record


def _calls(record: Path) -> list[str]:
    """Read the recorded calls back.

    Returns:
        one string per call, the arguments after the tool's own name.

    """
    return record.read_text(encoding="utf-8").splitlines()


def test_begin_takes_the_lock_under_the_holders_name(tmp_path: Path) -> None:
    """The one call is `--lock HOLDER` on the host state file."""
    queue, record = _queue(tmp_path)
    out = hosttick.begin(queue)
    assert out.startswith("ok:")
    assert _calls(record) == [f"--state {queue.state} --lock github-b3"]


def test_end_runs_arm_ledger_evidence_flush_and_unlock_in_that_order(tmp_path: Path) -> None:
    """The flush callback sits between the evidence and the unlock, observed in one record."""
    queue, record = _queue(tmp_path)
    job = tmp_path / "cron.job"
    job.write_text("abc123\n", encoding="utf-8")

    def flush() -> None:
        with record.open("a", encoding="utf-8") as handle:
            handle.write("FLUSH\n")

    closing = Closing(_TODAY, "did a thing", "next thing", job)
    hosttick.end(queue, closing, flush)
    steps = [call.replace(f"--state {queue.state} ", "") for call in _calls(record)]
    assert steps == [
        "--armed abc123",
        "--ledger W2 advanced sweep did a thing",
        f"--update W2 --evidence-append {_TODAY} did a thing --next next thing",
        "FLUSH",
        "--unlock github-b3",
    ]


def test_end_without_a_note_only_flushes_and_unlocks(tmp_path: Path) -> None:
    """No ledger and no evidence when there is nothing to say."""
    queue, record = _queue(tmp_path)
    hosttick.end(queue, Closing(_TODAY), lambda: None)
    assert _calls(record) == [f"--state {queue.state} --unlock github-b3"]


def test_end_without_a_next_step_leaves_the_next_step_alone(tmp_path: Path) -> None:
    """`--next` is passed only when the caller gave one."""
    queue, record = _queue(tmp_path)
    hosttick.end(queue, Closing(_TODAY, "did a thing"), lambda: None)
    assert not any("--next" in call for call in _calls(record))


def test_a_missing_job_file_arms_nothing(tmp_path: Path) -> None:
    """A tick with no cron job file records no `--armed`."""
    queue, record = _queue(tmp_path)
    hosttick.end(queue, Closing(_TODAY, "x", job_file=tmp_path / "absent"), lambda: None)
    assert not any("--armed" in call for call in _calls(record))


def test_the_standing_waypoint_is_the_queues_not_a_constant(tmp_path: Path) -> None:
    """A queue naming another standing waypoint gets its ledger line there."""
    queue, record = _queue(tmp_path)
    other = HostQueue(queue.tool, queue.state, queue.holder, "W7")
    hosttick.end(other, Closing(_TODAY, "x"), lambda: None)
    assert any("--ledger W7 " in call for call in _calls(record))

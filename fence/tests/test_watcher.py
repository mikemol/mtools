# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the guard watcher: injected effects first, then once with a real child (W920).

⚑ THE HEALTHY RUN IS THE POSITIVE CONTROL: a watcher that signals everything passes every tripping
arm. The last arm uses a real shell, a real `sleep` beneath it and a real signal, because the
`/proc` read and the signal are what an injected fake cannot vouch for.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from typing import TYPE_CHECKING

from mikemol.fence import watcher

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from mikemol.fence.guard import Sample

_ROW = watcher.Row(
    name="kine-latency",
    above=4.0,
    hold=3,
    interval_s=0.01,
    signal=int(signal.SIGTERM),
    target="bazel",
)
_REAL_ROW = watcher.Row(
    name="t", above=1.0, hold=2, interval_s=0.01, signal=int(signal.SIGTERM), target="sleep"
)
_OVER = 9.0
_UNDER = 1.0
_WAIT_S = 10.0
_POLL_S = 0.02
_EXIT_AFTER_THREE = 3
_EXIT_AFTER_TWO = 2
_EXIT_AFTER_FIVE = 5
_APPEARS_AT = 3


def _series(values: list[Sample]) -> Callable[[], Sample]:
    """Build a reader that yields the values in order, then repeats the last.

    Returns:
        the zero-argument reading.

    """
    queue = list(values)

    def read() -> Sample:
        return queue.pop(0) if len(queue) > 1 else queue[0]

    return read


def _exits_after(calls: int) -> Callable[[float], bool]:
    """Build a wait that reports the command gone on its `calls`th call.

    Returns:
        the wait function.

    """
    seen = [0]

    def wait(_seconds: float) -> bool:
        seen[0] += 1
        return seen[0] >= calls

    return wait


def _found(*pids: int) -> Callable[[str], list[int]]:
    """Build a finder that returns the same pids for any name.

    Returns:
        the finder.

    """
    return lambda _name: list(pids)


class _Kills:
    """Record the signals sent, and fail for the pids it is told are already gone."""

    def __init__(self, gone: frozenset[int] = frozenset()) -> None:
        self.sent: list[tuple[int, int]] = []
        self.gone = gone

    def __call__(self, pid: int, sig: int) -> None:
        if pid in self.gone:
            raise ProcessLookupError(pid)
        self.sent.append((pid, sig))


def test_a_healthy_run_signals_nothing_and_ends_when_the_command_exits() -> None:
    """The positive control: readings under the limit never trip, and an exit ends the watch."""
    kills = _Kills()
    outcome = watcher.watch(
        _ROW, _series([_UNDER]), _exits_after(_EXIT_AFTER_THREE), _found(10), kills
    )
    assert (outcome.tripped, outcome.signalled, kills.sent) == (False, [], [])
    assert outcome.samples == [_UNDER] * _EXIT_AFTER_THREE


def test_the_hold_th_over_limit_sample_signals_every_matching_descendant() -> None:
    """Three over in a row trip; both pids get the row's signal, once, and the streak restarts."""
    kills = _Kills()
    outcome = watcher.watch(
        _ROW, _series([_OVER]), _exits_after(_ROW.hold + 1), _found(10, 11), kills
    )
    assert outcome.tripped
    assert outcome.signalled == [10, 11]
    assert kills.sent == [(10, _ROW.signal), (11, _ROW.signal)]
    assert len(outcome.samples) == _ROW.hold + 1


def test_a_trip_does_not_end_the_watch_so_the_next_invocation_is_guarded() -> None:
    """Persistent overload re-trips after another `hold` samples and signals again."""
    kills = _Kills()
    outcome = watcher.watch(_ROW, _series([_OVER]), _exits_after(_ROW.hold * 2), _found(10), kills)
    assert kills.sent == [(10, _ROW.signal), (10, _ROW.signal)]
    assert outcome.signalled == [10, 10]


def test_a_trip_before_the_target_exists_keeps_trying_until_it_does() -> None:
    """W921: the first trips find no bazel yet; the streak is kept; it is signalled on appearing."""
    kills = _Kills()
    asked: list[str] = []

    def find(name: str) -> list[int]:
        asked.append(name)
        return [] if len(asked) < _APPEARS_AT else [10]

    outcome = watcher.watch(_ROW, _series([_OVER]), _exits_after(_EXIT_AFTER_FIVE), find, kills)
    assert outcome.signalled == [10]
    assert len(asked) == _APPEARS_AT


def test_a_command_that_exits_mid_streak_ends_the_watch_untripped() -> None:
    """Two over, then the command exits: no trip, no signal."""
    kills = _Kills()
    outcome = watcher.watch(
        _ROW, _series([_OVER]), _exits_after(_EXIT_AFTER_TWO), _found(10), kills
    )
    assert (outcome.tripped, kills.sent) == (False, [])


def test_blind_samples_never_trip() -> None:
    """A guard that cannot read does not kill a healthy build."""
    kills = _Kills()
    outcome = watcher.watch(
        _ROW, _series([None]), _exits_after(_EXIT_AFTER_FIVE), _found(10), kills
    )
    assert (outcome.tripped, kills.sent) == (False, [])


def test_a_process_that_exited_before_the_signal_is_not_an_error() -> None:
    """The build finishing between the trip and the signal is skipped, the other is signalled."""
    kills = _Kills(gone=frozenset({10}))
    outcome = watcher.watch(_ROW, _series([_OVER]), _exits_after(_ROW.hold), _found(10, 11), kills)
    assert outcome.tripped
    assert outcome.signalled == [11]


def test_a_trip_with_no_matching_descendant_signals_nothing() -> None:
    """The guard reports the trip and guesses no victim."""
    kills = _Kills()
    outcome = watcher.watch(_ROW, _series([_OVER]), _exits_after(_ROW.hold), _found(), kills)
    assert (outcome.tripped, outcome.signalled, kills.sent) == (True, [], [])


def _proc_entry(proc: Path, pid: int, comm: str, ppid: int) -> None:
    """Write a fake `/proc/<pid>/stat` line."""
    entry = proc / str(pid)
    entry.mkdir()
    (entry / "stat").write_text(f"{pid} ({comm}) S {ppid} 1 1 0 0\n", encoding="utf-8")


def test_descendants_are_found_by_name_through_the_parent_links(tmp_path: Path) -> None:
    """Shallowest first; a sibling tree and a non-matching name are left alone."""
    _proc_entry(tmp_path, 2, "bash", 1)
    _proc_entry(tmp_path, 3, "bazel", 2)
    _proc_entry(tmp_path, 4, "java", 3)
    _proc_entry(tmp_path, 5, "bazel", 4)
    _proc_entry(tmp_path, 6, "bazel", 99)
    (tmp_path / "self").mkdir()
    assert watcher.descendants_named(1, "bazel", tmp_path) == [3, 5]
    assert watcher.descendants_named(1, "absent", tmp_path) == []


def test_a_name_with_spaces_and_parentheses_is_read_whole(tmp_path: Path) -> None:
    """The name lies between the first ( and the LAST ), so `a (b) c` matches as itself."""
    _proc_entry(tmp_path, 2, "a (b) c", 1)
    assert watcher.descendants_named(1, "a (b) c", tmp_path) == [2]
    assert watcher.descendants_named(1, "a", tmp_path) == []


def test_an_unreadable_proc_yields_no_descendants(tmp_path: Path) -> None:
    """A path that is not a directory is empty, not an exception."""
    assert watcher.descendants_named(1, "bazel", tmp_path / "absent") == []


def test_a_real_guard_interrupts_a_real_child_by_name_and_ends_with_the_command(
    tmp_path: Path,
) -> None:
    """A shell with a `sleep` child: the guard trips on 9.0 readings and SIGTERMs the sleep."""
    shell = shutil.which("sh")
    assert shell is not None
    marker = tmp_path / "child.pid"
    command = subprocess.Popen(
        [shell, "-c", f"sleep 30 & echo $! > {marker}; wait"],
        stdin=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + _WAIT_S
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(_POLL_S)
    started = time.monotonic()
    with watcher.Guard(_REAL_ROW, command.pid, lambda: _OVER, os.kill) as guard:
        command.wait(timeout=_WAIT_S)
    child = int(marker.read_text(encoding="utf-8"))
    assert guard.outcome.tripped
    assert set(guard.outcome.signalled) == {child}
    assert time.monotonic() - started < _WAIT_S

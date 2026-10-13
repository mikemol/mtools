# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The detached commit's body: run a command to its end, then leave `rc=N` as its log's last line.

Ported from the host katas.py `wait` (mtools:W796, W874), which a detached commit ran as
`katas.py _wait LOG ARGV...`. `commits.commit_state` reads the log this writes: output while it
runs, then a blank line and `rc=N` once the child has ended, so a log with no rc is still running.

⚑ THE CLEANUP RUNS WHATEVER THE RESULT, AND ON A SIGTERM. Leading `--rm PATH` pairs name files to
remove afterwards (a probe's temp index and the `index.lock` it held). A SIGTERM becomes an exit,
so the `finally` still runs: a probe killed without it left a stale `.git/index.lock` that blocked
every later git operation in the repo (host katas record, 2026-10-06).

⚑ A HANG IS AN ABSENCE, NOT A DEADLINE (W1130; operator: "avoid wall-clock timeouts"). The child is
ended, with rc 125, only after `Watch.patience` polls in which neither its log nor its process
tree's CPU changed (`hangwatch`, `proctree`). One wall-clock backstop remains, `TIMEOUT_S`, rc 124,
for a child that never looks hung and never ends; it sits above `mikemol-commit`'s own 10800 s so
the commit's own verdict arrives first when it can. W1132 removes the rest of the clock.

⚑ `--timeout S` (W1105) SETS THAT LIMIT PER RUN, and a child that ends 0 leaves the seconds it took
in `LOG.seconds`: the measure a flush derives its next ceiling from (W1106), so a gate that has
always taken minutes is not given an open-ended index hold.

CONSUMED BY: `detach.start`, which runs this module as `python -m mikemol.katas.waiter`.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.katas import hangwatch, proctree

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import TextIO

TIMEOUT_S = 11000.0
"""How long the child may run: above `mikemol-commit`'s own 10800 s."""

TIMED_OUT = 124
"""The status a child that outlasted its timeout is recorded with, as `mikemol-commit` spells it."""

HUNG = 125
"""The status a child that showed no progress is recorded with (log and tree CPU both unchanged)."""

POLL_S = 5.0
"""How often a running child is read; the wait ends the moment the child does."""

NOT_STARTED = 127
"""The status a command that could not be started is recorded with, as a shell spells it."""

TERMINATED = 143
"""The exit a SIGTERM becomes (128 + 15), so the cleanup still runs."""

SECONDS_SUFFIX = ".seconds"
"""What is appended to a log's name for the file recording how long its child took."""

EXIT_USAGE = 2
_REMOVE = "--rm"
_TIMEOUT = "--timeout"
_PAIR = 2
_MINIMUM_ARGS = 2


@dataclass(frozen=True)
class Watch:
    """How a running child is watched: the poll interval, the patience, and the CPU reader."""

    poll_s: float = POLL_S
    patience: int = hangwatch.PATIENCE
    cpu: Callable[[int], float | None] = proctree.cpu_seconds


def split_removals(argv: Sequence[str]) -> tuple[list[Path], list[str]]:
    """Peel the leading `--rm PATH` pairs off an argv.

    Returns:
        the paths to remove afterwards, and the command that remains.

    """
    removals: list[Path] = []
    rest = list(argv)
    while rest[:1] == [_REMOVE] and len(rest) >= _PAIR:
        removals.append(Path(rest[1]))
        rest = rest[_PAIR:]
    return removals, rest


def seconds_of(log: Path) -> Path:
    """Name the file beside a log that holds the seconds its last successful child took.

    Returns:
        the log's path with `.seconds` appended.

    """
    return log.with_name(log.name + SECONDS_SUFFIX)


def split_timeout(argv: Sequence[str]) -> tuple[float, list[str]]:
    """Peel a leading `--timeout S` pair off an argv.

    Returns:
        the limit in seconds (`TIMEOUT_S` when none, or when S is not a positive number), and the
        argv that remains.

    """
    rest = list(argv)
    if rest[:1] != [_TIMEOUT] or len(rest) < _PAIR:
        return TIMEOUT_S, rest
    try:
        limit = float(rest[1])
    except ValueError:
        limit = 0.0
    return (limit if limit > 0 else TIMEOUT_S), rest[_PAIR:]


def run(
    log: Path,
    argv: Sequence[str],
    removals: Sequence[Path] = (),
    timeout: float = TIMEOUT_S,
    watch: Watch | None = None,
) -> int:
    """Run `argv`, write its output then `rc=N` to `log`, and remove `removals` whatever happened.

    Returns:
        the child's status; HUNG when it showed no progress; TIMED_OUT at the backstop `timeout`.

    """
    started = time.monotonic()
    try:
        with log.open("w", encoding="utf-8") as sink:
            status = _stream(argv, sink, timeout, Watch() if watch is None else watch)
    finally:
        for path in removals:
            path.unlink(missing_ok=True)
    if status == 0:
        seconds_of(log).write_text(f"{time.monotonic() - started:.1f}\n", encoding="utf-8")
    with log.open("a", encoding="utf-8") as sink:
        sink.write(f"\nrc={status}\n")
    return status


def _end(child: subprocess.Popen[bytes]) -> None:
    """End a child and everything it started; it leads its own session, so its group is its tree."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(child.pid, signal.SIGKILL)
    child.wait()


def _stream(argv: Sequence[str], sink: TextIO, timeout: float, watch: Watch) -> int:
    """Run `argv` with its output going straight into `sink` as it is produced (W1125).

    ⚑ THE LOG GROWS WHILE THE CHILD RUNS. It was written whole after the child ended, so a running
    commit was a silent file; W1126's hang witness (no growth and no tree CPU) needs the growth to
    be there to observe. Both streams share the one file, in the order the child wrote them.

    Returns:
        the child's status; `TIMED_OUT` when it outlasted `timeout`; `NOT_STARTED` when it could not
        be started at all (the reason is in the log).

    """
    try:
        child = subprocess.Popen(
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=sink,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except OSError as problem:
        sink.write(f"cannot start {argv[0] if argv else '(nothing)'}: {problem}\n")
        sink.flush()
        return NOT_STARTED
    try:
        return _watch(child, sink, timeout, watch)
    finally:
        if child.poll() is None:
            _end(child)


def _watch(child: subprocess.Popen[bytes], sink: TextIO, timeout: float, watch: Watch) -> int:
    """Wait for `child`, ending it only if it is HUNG or the backstop passes (W1130).

    ⚑ A HANG IS AN ABSENCE, NOT A DEADLINE (operator rule: avoid wall-clock timeouts). Each poll
    reads the log's size and the CPU of the child's whole tree; `hangwatch` calls it hung only after
    `watch.patience` polls in a row in which neither changed. A slow child on a loaded host still
    advances its CPU every poll, so it is never ended for being slow.

    ⚑ ONE WALL-CLOCK BACKSTOP REMAINS, AND WHY: a child that keeps writing or computing forever (a
    runaway loop) never looks hung, and a flush must not hold an index lock for ever. `timeout` is
    that bound, deliberately far above any observed gate, and W1132 removes the rest of the clock.

    Returns:
        the child's status; `HUNG` when it showed no progress; `TIMED_OUT` at the backstop.

    """
    deadline = time.monotonic() + timeout
    state = hangwatch.State()
    while True:
        try:
            return child.wait(timeout=min(watch.poll_s, max(deadline - time.monotonic(), 0.0)))
        except subprocess.TimeoutExpired:
            pass
        reading = hangwatch.Reading(os.fstat(sink.fileno()).st_size, watch.cpu(child.pid))
        state = hangwatch.step(state, reading)
        if hangwatch.hung(state, watch.patience):
            _end(child)
            sink.write(f"no progress for {watch.patience} polls (log and CPU unchanged); ended\n")
            sink.flush()
            return HUNG
        if time.monotonic() >= deadline:
            _end(child)
            sink.write(f"timed out after {timeout:g} s (the backstop; no verdict)\n")
            sink.flush()
            return TIMED_OUT


def main(argv: Sequence[str] | None = None) -> int:
    """Read `LOG [--rm PATH ...] COMMAND ...` and run the command as `run` does.

    Returns:
        the command's status, or EXIT_USAGE when no command was given.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < _MINIMUM_ARGS:
        sys.stderr.write("usage: waiter LOG [--rm PATH ...] COMMAND [ARG ...]\n")
        return EXIT_USAGE
    signal.signal(signal.SIGTERM, lambda _signum, _frame: sys.exit(TERMINATED))
    limit, rest = split_timeout(args[1:])
    removals, command = split_removals(rest)
    return run(Path(args[0]), command, removals, limit)


if __name__ == "__main__":
    sys.exit(main())

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

⚑ A TIMEOUT IS A RESULT, NOT A HANG: the child is abandoned at `TIMEOUT_S` and the log says so with
rc 124, the status `mikemol-commit` itself reports for a commit that timed out. The limit sits above
that commit's own (10800 s), so the commit's own verdict arrives first when it can.

CONSUMED BY: `detach.start`, which runs this module as `python -m mikemol.katas.waiter`.
"""

from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

if TYPE_CHECKING:
    from collections.abc import Sequence

TIMEOUT_S = 11000.0
"""How long the child may run: above `mikemol-commit`'s own 10800 s."""

TIMED_OUT = 124
"""The status a child that outlasted its timeout is recorded with, as `mikemol-commit` spells it."""

TERMINATED = 143
"""The exit a SIGTERM becomes (128 + 15), so the cleanup still runs."""

EXIT_USAGE = 2
_REMOVE = "--rm"
_PAIR = 2
_MINIMUM_ARGS = 2


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


def run(
    log: Path,
    argv: Sequence[str],
    removals: Sequence[Path] = (),
    timeout: float = TIMEOUT_S,
) -> int:
    """Run `argv`, write its output then `rc=N` to `log`, and remove `removals` whatever happened.

    Returns:
        the child's status, or TIMED_OUT when it outlasted `timeout`.

    """
    try:
        try:
            done = capture(argv, timeout=timeout)
            status, body = done.returncode, done.stdout + done.stderr
        except subprocess.TimeoutExpired:
            status, body = TIMED_OUT, f"timed out after {timeout:g} s (no verdict)\n"
    finally:
        for path in removals:
            path.unlink(missing_ok=True)
    log.write_text(f"{body}\nrc={status}\n", encoding="utf-8")
    return status


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
    removals, command = split_removals(args[1:])
    return run(Path(args[0]), command, removals)


if __name__ == "__main__":
    sys.exit(main())

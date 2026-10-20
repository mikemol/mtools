# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Interrupt the bazel client a withdrawn gate is running, and nothing else (W1757).

A withdraw of an in-flight gate writes a marker the gate reads at a phase boundary, and the bazel
phase has none, so a gate known to be dead burned 20 to 36 minutes under load (W1753). Bazel has its
own cancellation: SIGINT to the CLIENT stops the build and the client exits, after which the gate
takes its normal release path (the exit 75 refusal, the lease and the pins freed).

⚑ THE CLIENT ONLY: not the server, which is a daemon that outlives gates and serves other work, and
not the process group, which would orphan the gate's other children (W1705). The client is a
DESCENDANT of the submission's process whose name is bazel's; the server was detached to its own
parent long ago, so walking the submission's own descendants cannot reach it.

⚑ THE PROCESS TABLE IS A SEAM: the walk is a pure function over (pid, parent, name) rows, tested
without a process.
"""

import os
import signal
from collections.abc import Callable, Sequence
from pathlib import Path

type Process = tuple[int, int, str]
type Table = Callable[[], Sequence[Process]]
type Kill = Callable[[int, int], None]

PROC = Path("/proc")
_NAMES = ("bazel", "bazelisk")


def is_client(name: str) -> bool:
    """Say whether a process name is a bazel client's.

    Returns:
        True for `bazel`, `bazelisk` and the downloaded `bazel-<version>-<platform>` names.

    """
    return name in _NAMES or name.startswith("bazel-")


def process_table() -> list[Process]:
    """Read every process's pid, parent and executable name from /proc.

    Returns:
        the rows; a process that vanishes while being read is skipped.

    """
    rows: list[Process] = []
    for entry in PROC.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
            argv0 = (entry / "cmdline").read_bytes().split(b"\0", maxsplit=1)[0]
        except OSError:
            continue
        parent = int(stat.rsplit(")", maxsplit=1)[1].split()[1])
        name = Path(argv0.decode("utf-8", "replace")).name
        rows.append((int(entry.name), parent, name))
    return rows


def clients_under(root: int, table: Sequence[Process]) -> list[int]:
    """Find the bazel clients among the descendants of `root`.

    Returns:
        their pids; `root` itself and anything outside its descendants are never named.

    """
    children: dict[int, list[Process]] = {}
    for row in table:
        children.setdefault(row[1], []).append(row)
    found: list[int] = []
    pending = [root]
    while pending:
        for pid, _parent, name in children.get(pending.pop(), []):
            pending.append(pid)
            if is_client(name):
                found.append(pid)
    return sorted(found)


def interrupt(root: int, kill: Kill = os.kill, table: Table = process_table) -> list[int]:
    """Send SIGINT to each bazel client under `root`.

    Returns:
        the pids signalled; a client that exited meanwhile is not an error.

    """
    sent: list[int] = []
    for pid in clients_under(root, table()):
        try:
            kill(pid, signal.SIGINT)
        except ProcessLookupError:
            continue
        sent.append(pid)
    return sent

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The detached commit's bookkeeping: the `mikemol-commit` argv, and what its log says happened.

Ported from the host katas.py `commit_state` and the argv half of `prepare_commit` (mtools:W796,
W872). The commit itself is `mikemol-commit`'s (hooks commit_kata): the lock riding along, the
tracked-only pathspec, the trailers and the COMMITTED/REFUSED line live there. This module only
names the request and reads the log a detached run leaves, whose last line is `rc=N`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

RUNNING = "RUNNING"
"""A log with no `rc=N` line yet: the commit is still going."""

DONE = "done"
"""A log whose `rc=` is 0."""

_RC = re.compile(r"rc=(\d+)\s*$")


@dataclass(frozen=True)
class Request:
    """One commit asked for: the repo, the waypoint it lands, its subject and body, its paths.

    `paths` empty means the queue files, which is `mikemol-commit`'s own default.
    """

    repo: str
    waypoint: str
    subject: str
    body: str = ""
    paths: tuple[str, ...] = ()


def commit_argv(binary: Path, request: Request) -> list[str]:
    """Build the `mikemol-commit` argv for one commit.

    Returns:
        the argv, program first.

    """
    argv = [str(binary), request.repo, "--waypoint", request.waypoint, "--subject", request.subject]
    if request.body:
        argv += ["--body", request.body]
    return [*argv, *request.paths]


def commit_state(log: Path) -> str:
    """Read what the last detached commit of a repo did, from its log.

    ⚑ A LOG THAT EXISTS WITHOUT AN `rc=` LINE IS RUNNING, not failed: the wrapper writes the rc only
    when the child ends. A missing log is no commit at all, the empty string.

    Returns:
        `RUNNING`, `done`, `FAILED rc=N`, or '' when there is no log.

    """
    if not log.exists():
        return ""
    match = _RC.search(log.read_text(encoding="utf-8", errors="replace"))
    if match is None:
        return RUNNING
    return DONE if int(match[1]) == 0 else f"FAILED rc={match[1]}"

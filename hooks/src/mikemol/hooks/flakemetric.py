# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Flaky passes per repository as a published series (W2009).

⚑ A FLAKE THAT NOBODY SEES IS A FLAKE THAT STAYS (github-8f 2026-10-25, the operator's flag): the
gate records a pass on a tree it already refused (`flakes`, W2007) and says so once, in the line
the committing session reads. A number on a panel is what lets a trend be seen from outside any
session. `emit` sends ONE absolute gauge, `mikemol.commit.flaky_passes`, carrying the repository as
an attribute and as the namespace, exactly as `commit_gauge` sends the queued and in-flight counts.

⚑ THE VALUE IS THE COUNT OF `flake` LINES IN THE REPOSITORY'S OWN LOG, not a delta: an absolute
gauge is read correctly by a scrape that missed a send, and it falls only when the log is cleared.

⚑ BEST EFFORT, NEVER RAISING INTO THE COMMIT: no `mikemol-otlp`, no store, or a child that cannot
start means the number is not shipped; the verdict goes on as it was.

CONSUMED BY: `commit_kata.main`, through `stackrun.Seams.flaked` (W2009).
"""

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from mikemol.hooks import flakes
from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.vlogdetach import spawn_detached

SERVICE = "mikemol-commit"
NAME = "mikemol.commit.flaky_passes"
Spawn = Callable[[Sequence[str]], None]


def plan(program: str, repo: str, count: int) -> list[str]:
    """Build the `mikemol-otlp metric` argv for one count.

    Returns:
        the gauge's argv.

    """
    shared = ["--service", SERVICE, "--namespace", repo, "--field", f"repo={repo}"]
    return [program, "metric", *shared, "--name", NAME, "--value", str(count)]


def emit(git_dir: Path, repo: str, env: Mapping[str, str], spawn: Spawn = spawn_detached) -> bool:
    """Send the repository's flake count, when a binary and a store exist.

    Returns:
        True when the send was started; False when there was nothing to send it with.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return False
    try:
        spawn(plan(program, repo, flakes.flake_count(git_dir)))
    except OSError:
        return False
    return True

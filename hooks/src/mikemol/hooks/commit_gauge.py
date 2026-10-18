# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Move this commit through the live counts and start the two gauge pushes (W1446).

⚑⚑ ONE CALL PER TRANSITION, TWO ABSOLUTE GAUGES: `note` records the state in the crash-safe map
(`commit_counts`) and starts a detached `mikemol-otlp metric` for `mikemol.commit.queued` and one
for `mikemol.commit.inflight`, each carrying the repo as an attribute and the namespace. Both are
sent every time, so a panel never reads one of them as stale while the other moved.

⚑ THE MAP LIVES IN THE REPOSITORY'S OWN GIT DIRECTORY (`<git dir>/mtools/commit.counts`), beside the
commit lease's ledger, because the lease is per repository and so is the count. It is not tracked.

⚑ BEST EFFORT, NEVER RAISING INTO THE COMMIT: a read-only git directory, a missing `mikemol-otlp`
or an absent `MIKEMOL_ENDPOINTS` mean the number is not shipped; the commit goes on. With no child
or no store the map is still kept, so the counts stay right for the next commit that can ship.

CONSUMED BY: `commit_kata.main` (W1446).
"""

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from mikemol.hooks import commit_counts
from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.vlogdetach import spawn_detached

SERVICE = "mikemol-commit"
QUEUED_NAME = "mikemol.commit.queued"
INFLIGHT_NAME = "mikemol.commit.inflight"
Spawn = Callable[[Sequence[str]], None]


def plan(program: str, repo: str, counts: commit_counts.Counts) -> list[list[str]]:
    """Build the two `mikemol-otlp metric` argvs for a pair of counts.

    Returns:
        the queued gauge's argv, then the in-flight gauge's.

    """
    shared = ["--service", SERVICE, "--namespace", repo, "--field", f"repo={repo}"]
    sends = ((QUEUED_NAME, counts.queued), (INFLIGHT_NAME, counts.inflight))
    return [[program, "metric", *shared, "--name", name, "--value", str(v)] for name, v in sends]


def note(
    ledger: Path,
    key: str,
    state: str | None,
    env: Mapping[str, str],
    spawn: Spawn = spawn_detached,
) -> commit_counts.Counts | None:
    """Record this commit's state and start the gauge pushes, when a child and a store exist.

    Returns:
        the live counts after the change, or None when the map could not be written.

    """
    named = tuple(w for w in env.get(commit_counts.WAYPOINTS_ENV, "").split(",") if w)
    try:
        counts = commit_counts.transition(ledger / "commit.counts", key, state, waypoints=named)
    except OSError:
        return None
    program = binary(env)
    if program is None or not store_named(env):
        return counts
    for argv in plan(program, ledger.parent.parent.name, counts):
        try:
            spawn(argv)
        except OSError:
            break
    return counts

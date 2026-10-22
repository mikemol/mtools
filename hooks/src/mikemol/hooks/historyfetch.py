# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a repository's gate-step history from the trace store, to classify a refusal (W1721).

`gatehistory` turns the round spans `mikemol-otlp query-traces` prints into each step's record, and
`gateclass` turns a record into new, intermittent or broken. This is the seam between them and the
store: it asks for the repository's `train.round` spans and returns the history, or None.

⚑ NO ANSWER IS NO HISTORY, NEVER AN EMPTY ONE: no emitter, no store, a failed query or a reply that
holds no round returns None, and the caller then says nothing about the kind of red. An empty
history would read every failing step as NEW (a regression), a claim the absence of a reading cannot
support. A refusal is never delayed by this beyond the one query, and never changed by it.

CONSUMED BY: `commit_kata`, which hands it to the stack and train runners as their history seam.
"""

from collections.abc import Callable, Mapping
from pathlib import Path

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.gatehistory import history, rounds_of
from mikemol.hooks.runproc import run_process

SERVICE = "mikemol-train"
NAME = "train.round"
LIMIT = 50
Run = Callable[[list[str], Path], tuple[int, str]]


def fetch(
    repo: str, env: Mapping[str, str], run: Run = run_process
) -> dict[str, tuple[bool, ...]] | None:
    """Ask the store for `repo`'s round spans and fold them into each step's record.

    Returns:
        step label to its record, newest first; None when nothing could be read or no round of the
        repository ran its steps.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return None
    argv = [program, "query-traces", "--service", SERVICE, "--name", NAME, "--limit", str(LIMIT)]
    status, out = run(argv, Path.cwd())
    if status != 0:
        return None
    rounds = rounds_of(out.splitlines(), repo)
    return history(rounds) if rounds else None

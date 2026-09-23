# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An environment with git's per-invocation variables removed — ONE spelling of the rule.

Interned from substrate's `substrate/git_env.py` (working tree, 2026-09-23) at its request, as the
first item of the census reply's movable-now batch. The RULE is carried unchanged: no `GIT_*`
variable survives, and nothing is allowlisted.

⚑⚑⚑ WHY THIS EXISTS. Inside a git hook, git exports `GIT_DIR`, `GIT_INDEX_FILE`, `GIT_WORK_TREE`
and friends. A child that runs `git` inherits them, and a TEST FIXTURE that does `git init <tmp>;
git add; git commit` then acts on the CALLER's repository, not its temp one — `cwd=` does not
override an exported `GIT_DIR`. Measured in mtools on 2026-09-23: a probe run with `GIT_DIR` on this
repository made nine commits here from fixture code (recovered, never pushed). substrate's audit
found the same shape in a selftest its pre-commit gate reaches.

⚑⚑ THE FIX BELONGS AT THE RUNNER, NOT IN EACH FIXTURE. Every suite is a subprocess of a runner, so
stripping `GIT_*` from the environment the runner hands it covers every fixture at once, including
ones not yet written. mtools' shell runners spell the same rule as `git_scrubbed` (e4a171b); this is
the importable spelling, and the one substrate switches to.

⚑ THE NEGATIVE CONTROL IS CODIFIED HERE FOR THE FIRST TIME. substrate's was a manual measurement
(a hostile `GIT_DIR`: its suite passes through the scrubbing runner and misbehaves run directly);
`tests/test_git_env.py` makes it a fixture against a DECOY repository, and substrate pins its
switch to that test.

⚑ A SUITE LOSES NOTHING IT SHOULD HAVE: a suite reading the working tree does so from `cwd`, and git
finds the repository from there; only the hook's per-invocation redirections are dropped.
"""

from __future__ import annotations

import os

#: The prefix every per-invocation git variable carries.
PREFIX = "GIT_"


def clean_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return `base` (default: this process's environment) without any `GIT_*` variable.

    Returns:
        a new mapping; `base` itself is never modified.

    """
    source = dict(os.environ) if base is None else base
    return {key: value for key, value in source.items() if not key.startswith(PREFIX)}

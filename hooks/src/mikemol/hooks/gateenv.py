# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The environment the commit gate runs in: mtools' own variables are an allow-list (W1448).

⚑⚑ A TEST'S RESULT MUST NOT DEPEND ON WHO SUBMITTED THE COMMIT. The gate used to inherit the
submitter's whole environment, so arming `MIKEMOL_ENDPOINTS` on a submission (to make that commit
emit spans) made an otlp test resolve the real logs store, SEND a record to it and fail
(2026-10-17, mtools:W1446's first gate run; github-8f's ruling). Every `MIKEMOL_*` variable is
therefore REMOVED from what the gate sees unless it is on the list below, which is the set the gate
path itself reads (the snapshot, the isolation, the claim, the load wait).

⚑ SCOPED TO OUR OWN NAMESPACE ON PURPOSE. A full `env -i` plus an allow-list is the principled
form (the units do it), but the pre-commit hooks of the other repos need variables this module
cannot know (proxies, tokens, tool homes), and a gate that fails to start in a peer repo costs more
than it protects. Everything outside `MIKEMOL_` passes untouched; narrowing that is a separate,
per-repo declaration (carded as the follow-up to W1448).

A variable the gate needs but this list lacks shows as an obvious gate failure the first time it
runs; the fix is one name added here, with its reason.
"""

import os
from collections.abc import Mapping, Sequence

PREFIX = "MIKEMOL_"
GATE_VERBS = frozenset({"commit", "hook"})
# ⚑ EACH NAME IS READ ON THE GATE PATH (snapshot, isolation, claim, load wait); none is telemetry.
KEEP = frozenset(
    {
        "MIKEMOL_REAL_ROOT",
        "MIKEMOL_SNAPSHOT_ROOT",
        "MIKEMOL_COMMIT_ISOLATED",
        "MIKEMOL_COMMIT_MAXLOAD",
        "MIKEMOL_COMMIT_LOAD_WAIT_S",
        "MIKEMOL_GITHUB_ROOT",
        "MIKEMOL_FENCE_BIN",
        "MIKEMOL_COMMIT_LOCK_HELD",
        "MIKEMOL_COMMIT_TIMEOUT_S",
        "MIKEMOL_COMMIT_LOCK_TIMEOUT",
        "MIKEMOL_COMMIT_WITHDRAW_MARKER",
    }
)


def subcommand(argv: Sequence[str]) -> str:
    """Name the git subcommand of an argv, skipping the global `-C <path>` options.

    Returns:
        the first word that is neither `-C`, its value, nor another option; empty when none.

    """
    skip = False
    for word in argv:
        if skip:
            skip = False
        elif word == "-C":
            skip = True
        elif not word.startswith("-"):
            return word
    return ""


def child_env(argv: Sequence[str], extra: Mapping[str, str]) -> dict[str, str] | None:
    """Build the environment a git child gets: the caller's, plus `extra`, scrubbed for the gate.

    ⚑ ONLY THE COMMANDS THAT RUN A HOOK ARE SCRUBBED (`commit` and `hook`): plumbing such as
    `rev-parse` or `update-index` runs no repository code, so it keeps the whole environment.

    Returns:
        None when there is nothing to add and the child is not a gate (it inherits as ever), else
        the merged environment, with the `MIKEMOL_*` variables off the list removed for a gate.

    """
    gate = subcommand(argv) in GATE_VERBS
    if not extra and not gate:
        return None
    merged = {**os.environ, **extra}
    return scrubbed(merged) if gate else merged


def scrubbed(env: Mapping[str, str]) -> dict[str, str]:
    """Drop every `MIKEMOL_*` variable that is not on the gate's list.

    Returns:
        a copy of the environment without them; everything else is kept as it was.

    """
    return {k: v for k, v in env.items() if not k.startswith(PREFIX) or k in KEEP}

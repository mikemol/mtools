# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count each commit's verdict as a metric, so failed, stalled and idle are queries (W1730).

github-8f, 2026-10-19, relaying the operator ("when in doubt, look for how to use Victoria to make
the class of problem moot"): a host tick read FAILED, RUNNING and idle from spot probes, and each
misled it. `mikemol.commit.verdict{repo, verdict, stage}` is sent from the place that prints the
verdict, beside W1446's two gauges, so the same answers are a windowed query and an alert.

⚑ THE LABELS ARE BOUNDED. `verdict` is one of five words, `stage` is the name of the last gate phase
that printed a mark (a fixed set of phase names, `-` when none), and `repo` is the repository: no
subject, sha or check label reaches a series, so the count of series cannot grow with the work.

⚑ THE STAGE IS WHERE THE RUN STOPPED MARKING, NOT WHICH CHECK FAILED (W1728): the gate does not
stop at its first failure, so the failed checks are in the REFUSED line's own clause.

⚑ BEST EFFORT, NEVER RAISING INTO THE COMMIT: no `mikemol-otlp`, no store or a failed spawn means
the sample is not shipped, and the verdict is already printed.

CONSUMED BY: `commit_kata.commit` (W1730).
"""

from collections.abc import Callable, Mapping, Sequence

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.gatephase import marks
from mikemol.hooks.vlogdetach import spawn_detached

SERVICE = "mikemol-commit"
NAME = "mikemol.commit.verdict"
NO_STAGE = "-"
WITHDRAW_RC = 75
"""The gate's exit when a withdraw marker was read at a phase boundary."""
Spawn = Callable[[Sequence[str]], None]
Printed = tuple[str, int, str]
"""A verdict as printed: its line, the commit's exit code and the gate's shown output."""

_WORDS = (
    ("COMMITTED ", "COMMITTED"),
    ("REFUSED ", "REFUSED"),
    ("NOT COMMITTED ", "NOT_COMMITTED"),
    ("RACED ", "RACED"),
)


def kind_of(line: str, rc: int) -> str:
    """Name a verdict line's kind, the way the counter labels it.

    Returns:
        COMMITTED, REFUSED, NOT_COMMITTED or RACED from the line's first words, WITHDRAWN for a
        refusal whose exit is the withdraw code, and NOT_COMMITTED for anything else.

    """
    for prefix, kind in _WORDS:
        if line.startswith(prefix):
            return "WITHDRAWN" if kind == "REFUSED" and rc == WITHDRAW_RC else kind
    return "NOT_COMMITTED"


def stage_of(shown: str) -> str:
    """Name the last gate phase the output marked.

    Returns:
        the last mark's name, or `-` when the output carries no mark.

    """
    found = marks(shown)
    return found[-1].name if found else NO_STAGE


def plan(program: str, repo: str, kind: str, stage: str) -> list[str]:
    """Build the `mikemol-otlp metric` argv for one verdict.

    Returns:
        the argv; the value is 1 and the labels are repo, verdict and stage.

    """
    argv = [program, "metric", "--service", SERVICE, "--namespace", repo, "--name", NAME]
    argv += ["--value", "1", "--field", f"repo={repo}", "--field", f"verdict={kind}"]
    argv += ["--field", f"stage={stage}"]
    return argv


def emit(
    repo: str, printed: Printed, env: Mapping[str, str], spawn: Spawn = spawn_detached
) -> bool:
    """Start the counter child for a printed verdict, when a child and a store exist.

    Returns:
        whether the child was started; False with no binary or store, or a failed spawn.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return False
    line, rc, shown = printed
    try:
        spawn(plan(program, repo, kind_of(line, rc), stage_of(shown)))
    except OSError:
        return False
    return True

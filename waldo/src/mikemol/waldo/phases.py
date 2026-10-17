# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A recipe is an ordered list of phases; the pure model of one and who may run when (W1067).

From cassian's vault-apply recipe (P-1..P10): "run ONE phase at a time". Which phase is done is read
from the world by a witness the phase declares, never remembered; which phase may run now is a pure
function of the marker (W1064), the phases already done, and the phase's own rules.

⚑ A PHASE'S DONE-NESS IS A READING, NOT A FLAG. `Phase.done` is a witness over the world (the
`rekey/root-revoked` marker in cassian's P8); `read_done` runs them. A phase with no `done` witness
cannot be told apart from one never run, so it is never reported done and, if it is a point of no
return, the recipe is unsound (`lint` says so) because nothing could refuse its re-run.

⚑ A POINT OF NO RETURN IS NEVER RE-RUN. When its done-witness shows it happened, `eligibility`
refuses; an ordinary phase may be re-run (idempotent), but not this one.

⚑ A PHASE WAITS FOR ITS PREDECESSORS BY NAME. `after` lists the phases that must be done first; the
reasons a phase cannot run are listed all together, so one `status` tells the operator everything.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from mikemol.waldo.contract import Contract
from mikemol.waldo.marker import mismatches
from mikemol.waldo.witness import Run, Witness, judge

DONE = "done"
READY = "ready"
WAITING = "waiting"


@dataclass(frozen=True)
class ConfirmSpec:
    """How a point of no return is confirmed: the variable, where to read it, what to read."""

    name: str
    source: str
    reading: Witness
    pattern: str


@dataclass(frozen=True)
class Phase:
    """One phase: what it needs, what it records, how to tell it happened, if it can be undone.

    `entry` witnesses are re-run when the phase starts (never trusted from an earlier pass),
    `contract` is the waldo contract the phase applies (None for a phase that only records), and
    `confirm` makes the phase wait for a confirmation read off the thing it will change.

    `act` is a command (argv) that IS the phase (W1355): run only while the `done` witness is false,
    and judged by that witness afterwards. A phase carries an act or a contract, never both.
    """

    name: str
    needs: Mapping[str, str] = field(default_factory=dict)
    sets: Mapping[str, str] = field(default_factory=dict)
    after: tuple[str, ...] = ()
    done: Witness | None = None
    point_of_no_return: bool = False
    entry: tuple[Witness, ...] = ()
    contract: Contract | None = None
    confirm: ConfirmSpec | None = None
    act: tuple[str, ...] = ()


@dataclass(frozen=True)
class Recipe:
    """An ordered list of phases."""

    phases: tuple[Phase, ...]

    def find(self, name: str) -> Phase | None:
        """Find a phase by name.

        Returns:
            the Phase, or None when there is no such phase.

        """
        return next((phase for phase in self.phases if phase.name == name), None)


@dataclass(frozen=True)
class Status:
    """Where one phase stands: done, ready to run, or waiting, and why."""

    name: str
    state: str
    why: tuple[str, ...]


def _act_findings(phase: Phase) -> list[str]:
    """Find what is unsound about a phase's act (W1355).

    Returns:
        a finding when the phase carries both an act and a contract, and one when it carries an act
        with no done witness (nothing could tell the act ran, or refuse its re-run).

    """
    findings: list[str] = []
    if phase.act and phase.contract is not None:
        findings.append(f"{phase.name}: a phase carries an act or a contract, not both")
    if phase.act and phase.done is None:
        findings.append(f"{phase.name}: a phase with an act needs a done witness")
    return findings


def lint(recipe: Recipe) -> list[str]:
    """Find what is unsound in a recipe.

    Returns:
        one line per finding: a repeated phase name, an `after` that names no earlier phase, a
        point of no return with no done-witness (nothing could refuse its re-run), and an unsound
        act (both an act and a contract, or an act with no done-witness).

    """
    findings: list[str] = []
    seen: list[str] = []
    for phase in recipe.phases:
        if phase.name in seen:
            findings.append(f"{phase.name}: the phase name is used twice")
        findings.extend(
            f"{phase.name}: after {earlier} names no earlier phase"
            for earlier in phase.after
            if earlier not in seen
        )
        if phase.point_of_no_return and phase.done is None:
            findings.append(f"{phase.name}: a point of no return needs a done witness")
        findings.extend(_act_findings(phase))
        seen.append(phase.name)
    return findings


def read_done(recipe: Recipe, run: Run, started: float | None = None) -> dict[str, bool]:
    """Run each phase's done-witness and say which phases the world shows done.

    Returns:
        done or not, by phase name; a phase with no done-witness is never done.

    """
    shown: dict[str, bool] = {}
    for phase in recipe.phases:
        if phase.done is None or not phase.done.argv:
            shown[phase.name] = False
            continue
        code, out = run(phase.done.argv)
        shown[phase.name] = judge(phase.done, code, out, started=started).rc == 0
    return shown


def eligibility(
    recipe: Recipe,
    phase: Phase,
    marker: Mapping[str, str] | None,
    done: Mapping[str, bool],
) -> list[str]:
    """List why a phase may not run now.

    Returns:
        the reasons, all together; empty means it may run.

    """
    reasons: list[str] = []
    if phase.point_of_no_return and done.get(phase.name, False):
        reasons.append("already done: a point of no return is never re-run")
    if phase.act and done.get(phase.name, False):
        reasons.append("already done: an act runs only while its done witness is false")
    reasons.extend(
        f"waiting for {earlier}, which is not done"
        for earlier in phase.after
        if recipe.find(earlier) is not None and not done.get(earlier, False)
    )
    if phase.needs:
        reasons.extend(mismatches(marker, phase.needs))
    return reasons


def statuses(
    recipe: Recipe, marker: Mapping[str, str] | None, done: Mapping[str, bool]
) -> list[Status]:
    """Say where every phase stands.

    Returns:
        one Status per phase, in order: done when the world shows it (even if it could run again),
        ready when it may run, waiting with the reasons otherwise.

    """
    rows: list[Status] = []
    for phase in recipe.phases:
        if done.get(phase.name, False):
            rows.append(Status(phase.name, DONE, ()))
            continue
        reasons = eligibility(recipe, phase, marker, done)
        rows.append(Status(phase.name, WAITING if reasons else READY, tuple(reasons)))
    return rows


def names(recipe: Recipe) -> Sequence[str]:
    """Give the phase names in order.

    Returns:
        the names.

    """
    return [phase.name for phase in recipe.phases]

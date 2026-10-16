# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run ONE phase of a recipe: marker, order, entry, confirmation, the act, the marker (W1068).

From cassian's `p0..p10` functions, each of which asserts its standing flags, re-proves its
preconditions at its own entry, demands a confirmation if it cannot be undone, applies, witnesses,
and writes the marker. The order is fixed, every step stops the run at its failure, and a phase that
was refused leaves the marker exactly as it found it:

    1. lint the recipe (an unsound recipe runs nothing)
    2. read the marker; an ambiguous marker is exit 7, not a guess
    3. read which phases the world shows done
    4. eligibility: order, standing flags, a point of no return not already done
    5. the phase's `entry` witnesses, run fresh
    6. confirmation, if the phase has one: the value read off the target is reproduced
    7. the phase's contract through the pipeline (dry stops after the compare)
    8. only after success: the phase's `sets` merged into the marker, written by rename

⚑ THE MARKER MOVES LAST AND ONLY ON SUCCESS. A refused, failed or dry phase never writes it, so the
marker cannot get ahead of the world. A phase that succeeded but whose marker could not be written
is reported as such (exit 1, `marker-not-written`) because the world has moved and the marker
has not.

⚑ THE CONFIRMATION IS REPORTED AS A FINGERPRINT, never as the value; a refusal names the variable
and where to read it, with the standard command to re-run, and not the answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.waldo import marker
from mikemol.waldo.confirm import ConfirmError, check, instructions, issue
from mikemol.waldo.marker import MarkerError
from mikemol.waldo.phases import eligibility, lint, read_done
from mikemol.waldo.pipeline import EXIT_CANNOT, EXIT_FAILED, EXIT_OK, EXIT_REFUSED, Stop, execute
from mikemol.waldo.witness import run_all

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from mikemol.waldo.phases import Phase, Recipe
    from mikemol.waldo.pipeline import Seams, Verdict


@dataclass(frozen=True)
class Setting:
    """What the caller supplies: the marker file, the seams, the environment, the command."""

    marker: Path
    seams: Seams
    env: Mapping[str, str]
    command: str | None = None


def _refused(why: str, **more: object) -> Stop:
    return Stop(EXIT_REFUSED, {"state": "refused", "why": why, **more})


def _entry(phase: Phase, setting: Setting) -> Stop | None:
    """Re-run the phase's entry witnesses.

    Returns:
        a Stop naming the failing witnesses, or None when each holds.

    """
    results = run_all(
        phase.entry,
        setting.seams.run,
        started=setting.seams.clock(),
        unevaluated=setting.seams.unevaluated,
    )
    failed = [r.name for r in results if r.rc != 0 and not r.unevaluated]
    if failed:
        return _refused("an entry assertion failed", failed=failed)
    blind = [r.name for r in results if r.unevaluated]
    if blind:
        # ⚑ AN ENVIRONMENT FAULT IS NOT A BROKEN ENTRY ASSERTION (W1272): nothing was measured, so
        # the phase cannot start, and says so as cannot-run.
        why = "an entry assertion could not be evaluated"
        cannot: Verdict = {"state": "cannot-run", "why": why}
        return Stop(EXIT_CANNOT, {**cannot, "unevaluated": blind})
    return None


def _confirmation(phase: Phase, setting: Setting) -> tuple[Stop | None, str]:
    """Demand the phase's confirmation.

    Returns:
        (a Stop when it is not confirmed, "") or (None, the accepted value's fingerprint); a phase
        with no confirmation gives (None, "").

    """
    spec = phase.confirm
    if spec is None:
        return None, ""
    _code, reading = setting.seams.run(spec.reading.argv)
    try:
        challenge = issue(spec.name, spec.source, reading, spec.pattern)
        return None, check(challenge, setting.env)
    except ConfirmError as problem:
        extra: dict[str, object] = {}
        if setting.command is not None and spec.name not in setting.env:
            extra["how"] = instructions(
                issue(spec.name, spec.source, reading, spec.pattern), setting.command
            )
        return _refused(str(problem), **extra), ""


def _before(
    recipe: Recipe,
    phase: Phase,
    setting: Setting,
    state: Mapping[str, str] | None,
) -> tuple[Stop | None, str]:
    """Run steps 3 to 6: done-ness, eligibility, entry witnesses, confirmation.

    Returns:
        (a Stop, "") when the phase may not start, or (None, the confirmation's fingerprint).

    """
    done = read_done(recipe, setting.seams.run, started=setting.seams.clock())
    reasons = eligibility(recipe, phase, state, done)
    if reasons:
        return _refused("the phase may not run now", reasons=reasons), ""
    stopped = _entry(phase, setting)
    if stopped is not None:
        return stopped, ""
    return _confirmation(phase, setting)


def run_phase(
    recipe: Recipe, name: str, setting: Setting, *, dry: bool = False
) -> tuple[int, Verdict]:
    """Run the named phase and say what happened.

    Returns:
        (exit code, verdict); the verdict always has a `state` and the `phase`.

    """
    phase = recipe.find(name)
    findings = lint(recipe)
    if phase is None or findings:
        why = f"no phase {name}" if phase is None else "the recipe is unsound"
        return EXIT_CANNOT, {"state": "cannot-run", "phase": name, "why": why, "findings": findings}
    try:
        state = marker.read(setting.marker)
    except MarkerError as problem:
        return EXIT_CANNOT, {"state": "cannot-run", "phase": name, "why": str(problem)}
    stopped, confirmed = _before(recipe, phase, setting, state)
    if stopped is not None:
        return stopped.code, {**stopped.verdict, "phase": name}
    code, verdict = (
        execute(phase.contract, setting.seams, dry=dry)
        if phase.contract is not None
        else (EXIT_OK, {"state": "matches" if dry else "recorded"})
    )
    verdict = {**verdict, "phase": name}
    if confirmed:
        verdict["confirmed"] = confirmed
    if code != EXIT_OK or dry:
        return code, verdict
    try:
        marker.write(setting.marker, {**(state or {}), **phase.sets})
    except MarkerError as problem:
        return EXIT_FAILED, {**verdict, "state": "marker-not-written", "why": str(problem)}
    return EXIT_OK, {**verdict, "marker": dict(phase.sets)}

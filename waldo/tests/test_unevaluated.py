# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for a witness that cannot be evaluated (mtools:W1272, luthen-observability:W1076).

⚑ AN ENVIRONMENT FAULT IS NOT A FAILED CHANGE. A witness whose command could not reach its target
(kubectl with no kubeconfig, a refused connection) measured nothing, so the waldo's own classifier
can mark it unevaluated and the verdict says so: `applied-witness-unevaluated`, not
`applied-witness-failed`. ⚑ THE CONTROLS ARE THE FAILURES THAT MUST STAY FAILURES: a real unmet
condition, a non-zero exit with a different message, an exit 0 whose output merely contains the
fault text, and a run with no classifier at all each still read as failed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

from mikemol.waldo.contract import parse
from mikemol.waldo.phases import Phase, Recipe
from mikemol.waldo.pipeline import EXIT_CANNOT, EXIT_OK, EXIT_REFUSED, Seams, execute
from mikemol.waldo.runphase import Setting, run_phase
from mikemol.waldo.witness import Witness, run_all

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.waldo.contract import Contract

_NS = 'module.w45.kubernetes_namespace_v1.throwaway["amr-skills"]'
_ROW = {"address": _NS, "actions": ["create"]}
_FAULT = "The connection to the server localhost:8080 was refused"
_AFTER: dict[str, object] = {"name": "rolled", "argv": ["roll"], "must_contain": ["rolled out"]}
_OTHER: dict[str, object] = {"name": "seen", "argv": ["see"], "must_contain": ["seen"]}
_BEFORE: dict[str, object] = {"name": "reach", "argv": ["reach"], "must_contain": ["reachable"]}
_OK = {"roll": (0, "rolled out"), "see": (0, "seen"), "reach": (0, "reachable")}


def _blind(code: int, out: str) -> bool:
    return code != 0 and "localhost:8080" in out


def _plan(_contract: Contract) -> tuple[str | None, str]:
    return "plan-1", ""


def _summarize(_artifact: str, _contract: Contract) -> object:
    return [_ROW]


class _World:
    """Scripted command results and a recorded apply."""

    def __init__(self, **changed: tuple[int, str]) -> None:
        self.runs = {**_OK, **changed}
        self.applied = 0

    def seams(self, *, classified: bool = True) -> Seams:
        base = Seams(_plan, _summarize, self._apply, self.run, lambda: 1_000.0)
        return replace(base, unevaluated=_blind) if classified else base

    def _apply(self, _artifact: str, _contract: Contract) -> tuple[int, str]:
        self.applied += 1
        return 0, "applied"

    def run(self, argv: Sequence[str]) -> tuple[int, str]:
        return self.runs[argv[0]]


def _contract(*after: dict[str, object], before: tuple[dict[str, object], ...] = ()) -> Contract:
    return parse({"allowed": [_ROW], "before": list(before), "after": list(after)})


def test_an_environment_fault_in_an_after_witness_is_unevaluated_not_failed() -> None:
    """The change applied; the witness could not reach its target, so the state says so."""
    world = _World(roll=(1, _FAULT))
    code, verdict = execute(_contract(_AFTER), world.seams())
    assert (code, verdict["state"]) == (EXIT_CANNOT, "applied-witness-unevaluated")
    assert (verdict["failed"], verdict["unevaluated"]) == ([], ["rolled"])
    assert world.applied == 1
    (row,) = cast("list[dict[str, object]]", verdict["witnesses"])
    assert row["unevaluated"] is True
    assert row["rc"] == 1


def test_a_real_unmet_condition_or_a_different_error_still_fails() -> None:
    """The controls: an exit 0 missing its text, and a non-zero exit with another message."""
    quiet = _World(roll=(0, "nothing rolled"))
    code, verdict = execute(_contract(_AFTER), quiet.seams())
    assert (code, verdict["state"]) == (EXIT_REFUSED, "applied-witness-failed")
    assert verdict["unevaluated"] == []
    other = _World(roll=(1, "error: image pull backoff"))
    code, verdict = execute(_contract(_AFTER), other.seams())
    assert (code, verdict["state"]) == (EXIT_REFUSED, "applied-witness-failed")
    assert (verdict["failed"], verdict["unevaluated"]) == (["rolled"], [])


def test_a_real_failure_outranks_an_unevaluated_witness_and_both_are_listed() -> None:
    """One witness failed and one could not be evaluated: failed wins the state, both are named."""
    world = _World(roll=(0, "nothing rolled"), see=(1, _FAULT))
    code, verdict = execute(_contract(_AFTER, _OTHER), world.seams())
    assert (code, verdict["state"]) == (EXIT_REFUSED, "applied-witness-failed")
    assert (verdict["failed"], verdict["unevaluated"]) == (["rolled"], ["seen"])


def test_an_exit_zero_is_always_judged_even_when_its_output_names_the_fault() -> None:
    """The classifier is asked only of a non-zero exit: this witness exited 0 and is met.

    The classifier here looks at the text alone, so it WOULD flag this output if it were asked.
    """

    def by_text(_code: int, out: str) -> bool:
        return "localhost:8080" in out

    world = _World(roll=(0, f"rolled out (log mentions {_FAULT})"))
    seams = replace(world.seams(), unevaluated=by_text)
    code, verdict = execute(_contract(_AFTER), seams)
    assert (code, verdict["state"]) == (EXIT_OK, "applied")


def test_with_no_classifier_the_fault_reads_as_a_failure_as_before() -> None:
    """The default is unchanged: no classifier, every non-zero exit is a failed witness."""
    world = _World(roll=(1, _FAULT))
    code, verdict = execute(_contract(_AFTER), world.seams(classified=False))
    assert (code, verdict["state"]) == (EXIT_REFUSED, "applied-witness-failed")


def test_an_environment_fault_in_a_precondition_cannot_run_and_applies_nothing() -> None:
    """A precondition that could not be evaluated is cannot-run; a real failure still refuses."""
    world = _World(reach=(1, _FAULT))
    code, verdict = execute(_contract(_AFTER, before=(_BEFORE,)), world.seams())
    assert (code, verdict["state"]) == (EXIT_CANNOT, "cannot-run")
    assert verdict["why"] == "a precondition could not be evaluated"
    assert world.applied == 0
    real = _World(reach=(0, "cluster is down"))
    code, verdict = execute(_contract(_AFTER, before=(_BEFORE,)), real.seams())
    assert (code, verdict["state"]) == (EXIT_REFUSED, "refused")
    assert real.applied == 0


def test_run_all_flags_only_what_the_classifier_flags_and_keeps_the_exit_code() -> None:
    """The flagged result keeps rc 1 and carries the flag; the other result is judged normally."""
    world = _World(roll=(1, _FAULT), see=(0, "seen"))
    witnesses = (
        Witness("rolled", ("roll",), must_contain=("rolled out",)),
        Witness("seen", ("see",)),
    )
    results = run_all(witnesses, world.run, unevaluated=_blind)
    got = [(r.name, r.rc, r.unevaluated) for r in results]
    assert got == [("rolled", 1, True), ("seen", 0, False)]


def test_an_entry_assertion_that_cannot_be_evaluated_stops_the_phase_as_cannot_run(
    tmp_path: Path,
) -> None:
    """An environment fault in a phase's entry is not a broken entry assertion; nothing applies."""
    phase = Phase(
        "p1",
        sets={"phase": "1"},
        done=Witness("d1", ("see",), must_contain=("done",)),
        entry=(Witness("scoped", ("roll",), must_contain=("scoped",)),),
        contract=parse({"allowed": [_ROW], "required": []}),
    )
    world = _World(roll=(1, _FAULT), see=(0, "pending"))
    setting = Setting(tmp_path / "phase.marker", world.seams(), {}, None)
    code, verdict = run_phase(Recipe((phase,)), "p1", setting)
    assert (code, verdict["state"]) == (EXIT_CANNOT, "cannot-run")
    assert verdict["unevaluated"] == ["scoped"]
    assert world.applied == 0

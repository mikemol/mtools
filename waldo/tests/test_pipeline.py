# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pipeline: the plan compared is the plan applied; a refusal applies nothing.

W1059. ⚑ THE APPLIED RUN IS THE POSITIVE CONTROL: a plan within the set is applied once, with the
very artifact that was planned, and its witnesses pass; every refusal below is then a refusal of
that same set of seams and not of a pipeline that refuses everything.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.waldo.contract import parse
from mikemol.waldo.custody import Secret
from mikemol.waldo.pipeline import (
    EXIT_CANNOT,
    EXIT_FAILED,
    EXIT_OK,
    EXIT_REFUSED,
    Seams,
    execute,
    verdict_line,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.waldo.contract import Contract

_NS = 'module.w45.kubernetes_namespace_v1.throwaway["amr-skills"]'
_JOB = 'module.forgejo.kubernetes_job_v1.forgejo_admin["forgejo"]'
_CREATE = {"address": _NS, "actions": ["create"]}
_UPDATE = {"address": _JOB, "actions": ["update"]}
_LEAKED = "value-that-must-not-leak"
_FAILED_APPLY = 7
_DOC = {
    "allowed": [_CREATE],
    "after": [{"name": "rolled", "argv": ["roll"], "must_contain": ["rolled out"]}],
}


def _parsed(text: str) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(text))


class _World:
    """The seams' stand-in: records what ran and answers from scripted values."""

    def __init__(
        self,
        rows: object = (_CREATE,),
        runs: dict[str, list[tuple[int, str]]] | None = None,
        apply_result: tuple[int, str] = (0, "applied"),
        plan_result: tuple[str | None, str] = ("plan-1", ""),
    ) -> None:
        self.rows = rows
        self.runs = runs if runs is not None else {"roll": [(0, "rolled out")]}
        self.apply_result = apply_result
        self.plan_result = plan_result
        self.applied: list[str] = []
        self.planned = 0
        self.ran: list[str] = []

    def seams(self) -> Seams:
        return Seams(self._plan, self._summarize, self._apply, self._run, lambda: 1_000.0)

    def _plan(self, _contract: Contract) -> tuple[str | None, str]:
        self.planned += 1
        return self.plan_result

    def _summarize(self, _artifact: str, _contract: Contract) -> object:
        rows = self.rows
        return [*cast("tuple[object, ...]", rows)] if isinstance(rows, tuple) else rows

    def _apply(self, artifact: str, _contract: Contract) -> tuple[int, str]:
        self.applied.append(artifact)
        return self.apply_result

    def _run(self, argv: Sequence[str]) -> tuple[int, str]:
        self.ran.append(argv[0])
        return self.runs[argv[0]].pop(0)


def test_a_plan_within_the_set_is_applied_with_the_same_artifact_and_witnessed() -> None:
    """The positive control: applied once with plan-1, the witness met, exit 0."""
    world = _World()
    code, verdict = execute(parse(_DOC), world.seams())
    assert code == EXIT_OK
    assert verdict["state"] == "applied"
    assert world.applied == ["plan-1"]
    assert verdict["failed"] == []
    assert verdict["planned"] == [f"create {_NS}"]


def test_an_empty_plan_is_converged_and_still_witnessed() -> None:
    """A converged set applies nothing but its witnesses still run."""
    world = _World(rows=[])
    code, verdict = execute(parse(_DOC), world.seams())
    assert (code, verdict["state"]) == (EXIT_OK, "converged")
    assert not world.applied
    assert world.ran == ["roll"]


def test_a_planned_change_outside_the_set_applies_nothing_and_prints_the_diff() -> None:
    """Refused with the plus line and the planned rows; apply and witnesses never run."""
    world = _World(rows=[_CREATE, _UPDATE])
    code, verdict = execute(parse(_DOC), world.seams())
    assert code == EXIT_REFUSED
    assert verdict["state"] == "refused"
    assert verdict["diff"] == [f"+ {_JOB} update"]
    assert not world.applied
    assert not world.ran


def test_a_dry_run_stops_at_matches() -> None:
    """Dry plans and compares, applies nothing and runs no after-witness."""
    world = _World()
    code, verdict = execute(parse(_DOC), world.seams(), dry=True)
    assert (code, verdict["state"]) == (EXIT_OK, "matches")
    assert not world.applied
    assert not world.ran


def test_a_plan_that_is_not_admitted_is_refused_with_a_scrubbed_tail() -> None:
    """The plan step's own output reaches the verdict with the secret scrubbed out."""
    world = _World(plan_result=(None, f"denied for {_LEAKED}"))
    code, verdict = execute(parse(_DOC), world.seams(), secrets=[Secret(_LEAKED)])
    assert code == EXIT_REFUSED
    assert verdict["why"] == "the plan was not admitted"
    assert _LEAKED not in verdict_line(verdict)


def test_an_unreadable_plan_is_cannot_run() -> None:
    """A malformed change row is exit 2, and nothing is applied."""
    world = _World(rows=[{"actions": ["create"]}])
    code, verdict = execute(parse(_DOC), world.seams())
    assert (code, verdict["state"]) == (EXIT_CANNOT, "cannot-run")
    assert not world.applied


def test_an_unsound_contract_runs_nothing() -> None:
    """A witness that cannot fail is found by lint before any step runs: exit 2, no plan made."""
    world = _World()
    vacuous = {"name": "vacuous", "argv": ["x"], "must_match": [".*"]}
    bad = {"allowed": [_CREATE], "after": [vacuous]}
    code, verdict = execute(parse(bad), world.seams())
    assert (code, verdict["state"]) == (EXIT_CANNOT, "cannot-run")
    assert world.planned == 0


def test_a_failed_precondition_refuses_before_any_plan() -> None:
    """The before-witness runs first; its failure ends the run with no plan made."""
    doc = {**_DOC, "before": [{"name": "clean", "argv": ["chk"], "must_contain": ["clean"]}]}
    world = _World(runs={"chk": [(0, "dirty")], "roll": []})
    code, verdict = execute(parse(doc), world.seams())
    assert code == EXIT_REFUSED
    assert verdict["why"] == "a precondition failed"
    assert world.planned == 0


def test_a_failed_apply_is_reported_scrubbed_and_not_witnessed() -> None:
    """Exit 1 with the apply's rc, the secret scrubbed from its tail, and no witness run."""
    world = _World(apply_result=(_FAILED_APPLY, f"boom {_LEAKED}"))
    code, verdict = execute(parse(_DOC), world.seams(), secrets=[Secret(_LEAKED)])
    assert (code, verdict["state"], verdict["rc"]) == (EXIT_FAILED, "apply-failed", _FAILED_APPLY)
    assert _LEAKED not in verdict_line(verdict)
    assert not world.ran


def test_a_failed_witness_after_an_apply_names_the_act_and_the_witness() -> None:
    """Applied but unproven is exit 1 with the state saying both."""
    world = _World(runs={"roll": [(0, "still rolling")]})
    code, verdict = execute(parse(_DOC), world.seams())
    assert (code, verdict["state"]) == (EXIT_REFUSED, "applied-witness-failed")
    assert verdict["failed"] == ["rolled"]


def test_an_advances_witness_compares_the_reading_before_the_act_with_after() -> None:
    """A version that moved passes; a standing green does not, though both read green."""
    doc = {
        "allowed": [_CREATE],
        "after": [{"name": "version", "argv": ["ver"], "advances": [r"v=(\d+)"]}],
    }
    moved = _World(runs={"ver": [(0, "v=1"), (0, "v=2")]})
    assert execute(parse(doc), moved.seams())[1]["state"] == "applied"
    standing = _World(runs={"ver": [(0, "v=1"), (0, "v=1")]})
    code, verdict = execute(parse(doc), standing.seams())
    assert (code, verdict["state"]) == (EXIT_REFUSED, "applied-witness-failed")


def test_the_verdict_is_one_json_line() -> None:
    """A line with no newline that parses back to the same verdict."""
    _, verdict = execute(parse(_DOC), _World().seams())
    line = verdict_line(verdict)
    assert "\n" not in line
    assert _parsed(line) == verdict

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the phase model: done is read from the world, and the reasons come all together.

W1067. ⚑ THE READY PHASE IS THE POSITIVE CONTROL: a phase whose predecessor is done and whose marker
flags hold is `ready`, so `waiting` with its reasons, and the refusal to re-run a point of no
return, are about those reasons and not about every phase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.waldo.phases import (
    DONE,
    READY,
    WAITING,
    Phase,
    Recipe,
    Status,
    eligibility,
    lint,
    names,
    read_done,
    statuses,
)
from mikemol.waldo.witness import Witness

if TYPE_CHECKING:
    from collections.abc import Sequence

_QUIESCED = Witness("quiesced", ("q",), must_contain=("suspend=true",))
_REVOKED = Witness("revoked", ("r",), must_contain=("root-revoked",))
_P1 = Phase("p1", sets={"phase": "1"}, done=_QUIESCED)
_P2 = Phase("p2", needs={"phase": "1"}, after=("p1",))
_P8 = Phase("p8", after=("p2",), done=_REVOKED, point_of_no_return=True)
_RECIPE = Recipe((_P1, _P2, _P8))


class _Runner:
    """A stand-in that answers each done-witness from a table."""

    def __init__(self, answers: dict[str, tuple[int, str]]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        self.asked.append(argv[0])
        return self.answers[argv[0]]


def test_the_phase_names_come_back_in_order() -> None:
    """The recipe's order is the order of its phases."""
    assert list(names(_RECIPE)) == ["p1", "p2", "p8"]
    assert _RECIPE.find("p2") == _P2
    assert _RECIPE.find("p9") is None


def test_a_phase_whose_predecessor_is_done_and_marker_holds_is_ready() -> None:
    """The positive control: no reasons, so it may run."""
    assert not eligibility(_RECIPE, _P2, {"phase": "1"}, {"p1": True})


def test_the_reasons_a_phase_cannot_run_are_listed_together() -> None:
    """An undone predecessor and a wrong marker value both appear in one answer."""
    reasons = eligibility(_RECIPE, _P2, {"phase": "0"}, {"p1": False})
    assert reasons == [
        "waiting for p1, which is not done",
        "phase: expected '1', the marker has '0'",
    ]


def test_a_phase_that_needs_flags_cannot_start_without_a_marker() -> None:
    """No marker at all is a reason, not a crash."""
    reasons = eligibility(_RECIPE, _P2, None, {"p1": True})
    assert reasons == ["no marker: the recipe has not recorded a phase yet"]


def test_an_ordinary_done_phase_may_run_again_but_a_point_of_no_return_may_not() -> None:
    """Idempotent phases repeat; the irreversible one is refused once its witness shows it done."""
    assert not eligibility(_RECIPE, _P1, None, {"p1": True})
    done = {"p1": True, "p2": True, "p8": True}
    assert eligibility(_RECIPE, _P8, None, done) == [
        "already done: a point of no return is never re-run"
    ]


def test_read_done_runs_each_witness_and_a_phase_without_one_is_never_done() -> None:
    """Done is what the world shows; a phase with no witness cannot be shown done."""
    runner = _Runner({"q": (0, "suspend=true"), "r": (0, "still live")})
    shown = read_done(_RECIPE, runner)
    assert shown == {"p1": True, "p2": False, "p8": False}
    assert runner.asked == ["q", "r"]


def test_a_done_witness_that_exits_non_zero_is_not_done() -> None:
    """A failing command is not a shown phase, whatever it printed."""
    runner = _Runner({"q": (3, "suspend=true"), "r": (0, "root-revoked")})
    assert read_done(_RECIPE, runner) == {"p1": False, "p2": False, "p8": True}


def test_statuses_say_done_ready_or_waiting_with_the_reasons() -> None:
    """One call tells the operator where every phase stands."""
    rows = statuses(_RECIPE, {"phase": "1"}, {"p1": True, "p2": False, "p8": False})
    assert rows == [
        Status("p1", DONE, ()),
        Status("p2", READY, ()),
        Status("p8", WAITING, ("waiting for p2, which is not done",)),
    ]


def test_a_sound_recipe_lints_clean() -> None:
    """The control: ordered names, earlier-only predecessors, a witnessed point of no return."""
    assert not lint(_RECIPE)


def test_lint_finds_each_unsoundness() -> None:
    """A repeated name, a forward or unknown predecessor, and an unwitnessed point of no return."""
    repeated = Recipe((_P1, _P1))
    assert lint(repeated) == ["p1: the phase name is used twice"]
    forward = Recipe((Phase("a", after=("b",)), Phase("b")))
    assert lint(forward) == ["a: after b names no earlier phase"]
    unwitnessed = Recipe((Phase("x", point_of_no_return=True),))
    assert lint(unwitnessed) == ["x: a point of no return needs a done witness"]

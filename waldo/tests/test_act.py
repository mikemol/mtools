# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for a phase that carries a command as its act (W1355).

⚑ THE FIRST RUN IS THE POSITIVE CONTROL: the act runs while its done witness is false, the witness
then holds, and the marker records the phase. Each refusal after it (the witness already true, an
act that fails, an act that exits 0 and changes nothing, an unsound recipe) leaves the marker as it
found it, and the act is shown not to have run where it must not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.waldo import marker
from mikemol.waldo.contract import parse
from mikemol.waldo.phases import Phase, Recipe
from mikemol.waldo.pipeline import EXIT_CANNOT, EXIT_FAILED, EXIT_OK, EXIT_REFUSED, Seams
from mikemol.waldo.runphase import Setting, run_phase
from mikemol.waldo.witness import Witness

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.waldo.contract import Contract

_ACT = ("do-it",)
_DONE = Witness("d", ("chk",), must_contain=("done",))
_PHASE = Phase("p1", sets={"phase": "1"}, done=_DONE, act=_ACT)
_ROW = {"address": 'module.w1.thing["x"]', "actions": ["create"]}


def _plan(_contract: Contract) -> tuple[str | None, str]:
    return "plan-1", ""


def _summarize(_artifact: str, _contract: Contract) -> object:
    return [_ROW]


def _apply(_artifact: str, _contract: Contract) -> tuple[int, str]:
    return 0, "applied"


class _World:
    """A scripted world: the done witness reads `state`; the act sets it, fails, or does nothing."""

    def __init__(self, state: str = "pending", act_code: int = 0, act_effect: bool = True) -> None:
        self.state = state
        self.act_code = act_code
        self.act_effect = act_effect
        self.acted = 0

    def seams(self) -> Seams:
        return Seams(_plan, _summarize, _apply, self._run, lambda: 1_000.0)

    def _run(self, argv: Sequence[str]) -> tuple[int, str]:
        if tuple(argv) == _ACT:
            self.acted += 1
            if self.act_effect:
                self.state = "done"
            return self.act_code, ""
        return 0, self.state


def _setting(world: _World, tmp_path: Path) -> Setting:
    return Setting(tmp_path / "phase.marker", world.seams(), {}, None)


def test_the_act_runs_while_its_witness_is_false_and_the_marker_records_it(tmp_path: Path) -> None:
    """The positive control: acted once, the done witness now holds, the marker moved."""
    world = _World()
    setting = _setting(world, tmp_path)
    code, verdict = run_phase(Recipe((_PHASE,)), "p1", setting)
    assert (code, verdict["state"], verdict["phase"]) == (EXIT_OK, "acted", "p1")
    assert world.acted == 1
    assert marker.read(setting.marker) == {"phase": "1"}


def test_an_act_whose_witness_already_holds_is_refused_and_not_run(tmp_path: Path) -> None:
    """The world already shows the phase done: the act is not run again and nothing is written."""
    world = _World(state="done")
    setting = _setting(world, tmp_path)
    code, verdict = run_phase(Recipe((_PHASE,)), "p1", setting)
    assert code == EXIT_REFUSED
    assert "an act runs only while its done witness is false" in str(verdict["reasons"])
    assert world.acted == 0
    assert marker.read(setting.marker) is None


def test_an_act_that_fails_is_failed_and_the_marker_does_not_move(tmp_path: Path) -> None:
    """A non-zero act exit is `act-failed` with its code, never a marker write."""
    world = _World(act_code=3, act_effect=False)
    setting = _setting(world, tmp_path)
    code, verdict = run_phase(Recipe((_PHASE,)), "p1", setting)
    assert (code, verdict["state"], verdict["rc"]) == (EXIT_FAILED, "act-failed", 3)
    assert marker.read(setting.marker) is None


def test_an_act_that_exits_zero_but_changes_nothing_is_not_done(tmp_path: Path) -> None:
    """The world judges the act: exit 0 with the witness still false is `not-done`."""
    world = _World(act_effect=False)
    setting = _setting(world, tmp_path)
    code, verdict = run_phase(Recipe((_PHASE,)), "p1", setting)
    assert (code, verdict["state"]) == (EXIT_FAILED, "not-done")
    assert world.acted == 1
    assert marker.read(setting.marker) is None


def test_a_dry_run_says_it_would_act_and_runs_nothing(tmp_path: Path) -> None:
    """Dry stops before the act: `would-act`, the act not run, no marker."""
    world = _World()
    setting = _setting(world, tmp_path)
    code, verdict = run_phase(Recipe((_PHASE,)), "p1", setting, dry=True)
    assert (code, verdict["state"]) == (EXIT_OK, "would-act")
    assert world.acted == 0
    assert marker.read(setting.marker) is None


def test_a_phase_with_both_an_act_and_a_contract_is_unsound(tmp_path: Path) -> None:
    """The recipe runs nothing and the finding says a phase carries one or the other."""
    both = Phase(
        "p1",
        done=_DONE,
        act=_ACT,
        contract=parse({"allowed": [_ROW], "required": []}),
    )
    world = _World()
    code, verdict = run_phase(Recipe((both,)), "p1", _setting(world, tmp_path))
    assert code == EXIT_CANNOT
    assert "an act or a contract, not both" in str(verdict["findings"])
    assert world.acted == 0


def test_a_phase_with_an_act_and_no_done_witness_is_unsound(tmp_path: Path) -> None:
    """Without a witness nothing could tell the act ran or refuse its re-run, so it is unsound."""
    blind = Phase("p1", act=_ACT)
    world = _World()
    code, verdict = run_phase(Recipe((blind,)), "p1", _setting(world, tmp_path))
    assert code == EXIT_CANNOT
    assert "needs a done witness" in str(verdict["findings"])
    assert world.acted == 0

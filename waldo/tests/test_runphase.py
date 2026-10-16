# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for run_phase: the marker moves last and only on success, and nothing else moves it.

W1068. ⚑ THE FIRST PHASE RUN IS THE POSITIVE CONTROL: p1 applies, is witnessed, and writes the
marker, so each refusal after it (order, a failed entry witness, a missing or wrong confirmation, a
point of no return already done, an ambiguous marker) is shown to leave the marker byte-for-byte as
it found it, with nothing applied.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.waldo import marker
from mikemol.waldo.confirm import MIN_LENGTH
from mikemol.waldo.contract import parse
from mikemol.waldo.custody import fingerprint
from mikemol.waldo.marker import MarkerError
from mikemol.waldo.phases import ConfirmSpec, Phase, Recipe
from mikemol.waldo.pipeline import EXIT_CANNOT, EXIT_FAILED, EXIT_OK, EXIT_REFUSED, Seams
from mikemol.waldo.runphase import Setting, run_phase
from mikemol.waldo.witness import Witness

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

    from mikemol.waldo.contract import Contract

_NS = 'module.w45.kubernetes_namespace_v1.throwaway["amr-skills"]'
_ACCESSOR = "wX9fQ2LmP4rT8vNb"
_VAR = "P2_CONFIRM"
_COMMAND = "env -C /home/someone/github/r /home/someone/.venv/bin/python3 -m recipe --set p2"
_ROW = {"address": _NS, "actions": ["create"]}
_CONTRACT = parse({"allowed": [_ROW], "required": []})
_EARLIER = {"phase": "1", "owner": "recipe"}
_LATER = {"phase": "2", "owner": "recipe"}
_P1 = Phase(
    "p1",
    sets={"phase": "1"},
    done=Witness("d1", ("chk1",), must_contain=("done",)),
    contract=_CONTRACT,
)
_P2 = Phase(
    "p2",
    needs={"phase": "1"},
    sets={"phase": "2"},
    after=("p1",),
    done=Witness("d2", ("chk2",), must_contain=("done",)),
    point_of_no_return=True,
    entry=(Witness("scoped", ("ent",), must_contain=("scoped",)),),
    contract=_CONTRACT,
    confirm=ConfirmSpec(_VAR, "the lookup", Witness("rd", ("rd",), exit_only=True), r"acc=(\S+)"),
)
_RECIPE = Recipe((_P1, _P2))
_MIN = MIN_LENGTH


def _plan(_contract: Contract) -> tuple[str | None, str]:
    return "plan-1", ""


def _summarize(_artifact: str, _contract: Contract) -> object:
    return [_ROW]


class _World:
    """The seams' stand-in: scripted command output, a recorded apply, a marker file."""

    def __init__(self, outputs: dict[str, str] | None = None) -> None:
        self.outputs = {
            "chk1": "pending",
            "chk2": "pending",
            "ent": "scoped",
            "rd": f"acc={_ACCESSOR}",
            **(outputs or {}),
        }
        self.applied = 0

    def seams(self) -> Seams:
        return Seams(_plan, _summarize, self._apply, self._run, lambda: 1_000.0)

    def _apply(self, _artifact: str, _contract: Contract) -> tuple[int, str]:
        self.applied += 1
        return 0, "applied"

    def _run(self, argv: Sequence[str]) -> tuple[int, str]:
        return 0, self.outputs[argv[0]]


def _setting(world: _World, tmp_path: Path, env: dict[str, str] | None = None) -> Setting:
    return Setting(tmp_path / "phase.marker", world.seams(), env or {}, _COMMAND)


def test_the_first_phase_applies_and_writes_the_marker(tmp_path: Path) -> None:
    """The positive control: applied once and the marker records the phase."""
    world = _World()
    setting = _setting(world, tmp_path)
    code, verdict = run_phase(_RECIPE, "p1", setting)
    assert (code, verdict["state"], verdict["phase"]) == (EXIT_OK, "applied", "p1")
    assert world.applied == 1
    assert marker.read(setting.marker) == {"phase": "1"}


def test_a_phase_out_of_order_is_refused_and_leaves_no_marker(tmp_path: Path) -> None:
    """p2 before p1: refused with the reasons, nothing applied, no marker written."""
    world = _World()
    setting = _setting(world, tmp_path)
    code, verdict = run_phase(_RECIPE, "p2", setting)
    assert code == EXIT_REFUSED
    assert verdict["why"] == "the phase may not run now"
    assert "waiting for p1, which is not done" in str(verdict["reasons"])
    assert world.applied == 0
    assert marker.read(setting.marker) is None


def _ready(tmp_path: Path, outputs: dict[str, str] | None = None) -> tuple[_World, Setting]:
    """Make a world where p1 is done and the marker records it.

    Returns:
        the world and the setting that points at its marker.

    """
    world = _World({"chk1": "done", **(outputs or {})})
    setting = _setting(world, tmp_path)
    marker.write(setting.marker, _EARLIER)
    return world, setting


def test_a_failed_entry_witness_refuses_and_leaves_the_marker(tmp_path: Path) -> None:
    """The precondition is re-run at entry: not scoped now means no apply and no marker move."""
    world, setting = _ready(tmp_path, {"ent": "ROOT"})
    code, verdict = run_phase(_RECIPE, "p2", setting, dry=False)
    assert (code, verdict["why"], verdict["failed"]) == (
        EXIT_REFUSED,
        "an entry assertion failed",
        ["scoped"],
    )
    assert world.applied == 0
    assert marker.read(setting.marker) == _EARLIER


def test_a_missing_confirmation_is_refused_with_how_and_without_the_answer(tmp_path: Path) -> None:
    """No variable: refused, the instructions name the standard command, the accessor is absent."""
    world, setting = _ready(tmp_path)
    code, verdict = run_phase(_RECIPE, "p2", setting)
    assert code == EXIT_REFUSED
    assert _VAR in str(verdict["how"])
    assert _COMMAND in str(verdict["how"])
    assert _ACCESSOR not in str(verdict)
    assert world.applied == 0
    assert marker.read(setting.marker) == _EARLIER


def test_a_wrong_confirmation_is_refused_and_not_echoed(tmp_path: Path) -> None:
    """A wrong answer: refused, nothing applied, neither value in the verdict."""
    world, setting = _ready(tmp_path)
    wrong = "this-is-not-the-accessor"
    setting = Setting(setting.marker, setting.seams, {_VAR: wrong}, _COMMAND)
    code, verdict = run_phase(_RECIPE, "p2", setting)
    assert code == EXIT_REFUSED
    assert "does not match" in str(verdict["why"])
    assert wrong not in str(verdict)
    assert _ACCESSOR not in str(verdict)
    assert world.applied == 0


def test_the_right_confirmation_applies_records_a_fingerprint_and_moves_the_marker(
    tmp_path: Path,
) -> None:
    """The point of no return runs once confirmed; only the fingerprint is reported."""
    world, setting = _ready(tmp_path)
    setting = Setting(setting.marker, setting.seams, {_VAR: _ACCESSOR}, _COMMAND)
    code, verdict = run_phase(_RECIPE, "p2", setting)
    assert (code, verdict["state"]) == (EXIT_OK, "applied")
    assert verdict["confirmed"] == fingerprint(_ACCESSOR)
    assert _ACCESSOR not in str(verdict)
    assert world.applied == 1
    assert marker.read(setting.marker) == _LATER


def test_a_dry_run_stops_at_matches_and_never_moves_the_marker(tmp_path: Path) -> None:
    """Dry confirms nothing is written even when everything would pass."""
    world, setting = _ready(tmp_path)
    setting = Setting(setting.marker, setting.seams, {_VAR: _ACCESSOR}, _COMMAND)
    code, verdict = run_phase(_RECIPE, "p2", setting, dry=True)
    assert (code, verdict["state"]) == (EXIT_OK, "matches")
    assert world.applied == 0
    assert marker.read(setting.marker) == _EARLIER


def test_a_point_of_no_return_already_done_is_not_run_again(tmp_path: Path) -> None:
    """The world shows p2 done: refused, even with the right confirmation."""
    world, setting = _ready(tmp_path, {"chk2": "done"})
    setting = Setting(setting.marker, setting.seams, {_VAR: _ACCESSOR}, _COMMAND)
    code, verdict = run_phase(_RECIPE, "p2", setting)
    assert code == EXIT_REFUSED
    assert "never re-run" in str(verdict["reasons"])
    assert world.applied == 0


def test_a_contract_that_refuses_leaves_the_marker(tmp_path: Path) -> None:
    """The pipeline's refusal (a plan outside the set) is the phase's, and the marker stays."""
    outside = {"address": "module.other.thing", "actions": ["delete"]}
    world = _World()
    seams = Seams(
        world.seams().plan,
        lambda _artifact, _contract: [outside],
        world.seams().apply,
        world.seams().run,
        lambda: 1_000.0,
    )
    setting = Setting(tmp_path / "phase.marker", seams, {}, _COMMAND)
    code, verdict = run_phase(_RECIPE, "p1", setting)
    assert (code, verdict["state"]) == (EXIT_REFUSED, "refused")
    assert marker.read(setting.marker) is None


def test_a_phase_without_a_contract_only_records_its_marker(tmp_path: Path) -> None:
    """A recording phase: no apply, state `recorded`, the marker moves."""
    recipe = Recipe((Phase("note", sets={"seen": "yes"}),))
    setting = _setting(_World(), tmp_path)
    code, verdict = run_phase(recipe, "note", setting)
    assert (code, verdict["state"]) == (EXIT_OK, "recorded")
    assert marker.read(setting.marker) == {"seen": "yes"}


def test_an_unknown_phase_and_an_unsound_recipe_are_cannot_run(tmp_path: Path) -> None:
    """Exit 2 with the reason; nothing is read or written."""
    setting = _setting(_World(), tmp_path)
    code, verdict = run_phase(_RECIPE, "p9", setting)
    assert (code, verdict["why"]) == (EXIT_CANNOT, "no phase p9")
    unsound = Recipe((Phase("x", point_of_no_return=True),))
    code, verdict = run_phase(unsound, "x", setting)
    assert (code, verdict["why"]) == (EXIT_CANNOT, "the recipe is unsound")
    assert marker.read(setting.marker) is None


def test_an_ambiguous_marker_is_cannot_run_not_a_guess(tmp_path: Path) -> None:
    """A marker with a repeated key stops the run before anything is read or applied."""
    world = _World()
    setting = _setting(world, tmp_path)
    setting.marker.write_text("phase = 1\nphase = 2\n", encoding="utf-8")
    code, verdict = run_phase(_RECIPE, "p1", setting)
    assert (code, verdict["state"]) == (EXIT_CANNOT, "cannot-run")
    assert world.applied == 0


def test_a_marker_that_cannot_be_written_after_success_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The world moved and the marker did not: exit 1 and a state that says so."""

    def refuse(_path: Path, _values: object, _header: str = "") -> None:
        message = "disk says no"
        raise MarkerError(message)

    monkeypatch.setattr(marker, "write", refuse)
    world = _World()
    code, verdict = run_phase(_RECIPE, "p1", _setting(world, tmp_path))
    assert (code, verdict["state"]) == (EXIT_FAILED, "marker-not-written")
    assert world.applied == 1

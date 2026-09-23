# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the check: each property fires on its defect, and a clean state fires none.

⚑ THE CLEAN STATE IS THE POSITIVE CONTROL for every "no finding" arm below: without it, an arm
that asserts a finding is absent cannot be told from a check that reports nothing at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import check as chk
from mikemol.pathsforward.model import State, validate

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_COUNTER = 3
_ABOVE = 999
_BAD = "Wx"
_HISTORICAL = "W50b"
_HISTORICAL_REASON = "issued by a tick that broke the integer rule; kept as a historical name"
_MISSING = "/nonexistent/x"
_NOTE = "file.md"
_GONE = "gone.md"
_DOTTED = "v1."
# summit's W37 evidence, verbatim in the parts that name labels, plus one real missing path.
_W37_EVIDENCE = (
    "Summit ran it: exit 1, 'state=open, bazel exit 7: Unable to load package for "
    "//paperkit:components.bzl' — F-arm on a synthetic dep: @@//pkg:f → open, //pkg:f from "
    f"inside the dep → @dep//pkg:f closed. Also {_MISSING} is missing."
)


def _wp(sym: str, status: str = "ready", **extra: object) -> Rec:
    """Build a waypoint.

    Returns:
        the waypoint.

    """
    w: Rec = {"symbol": sym, "title": sym, "status": status, "blocked_on": [],
              "blocked_kind": None, "enables": [], "evidence": ""}
    w.update(extra)
    return w


def _res(sym: str, reason: str = "r") -> Rec:
    """Build a residue entry.

    Returns:
        the entry.

    """
    return {"symbol": sym, "reason": reason}


def _state(root: Path, waypoints: list[Rec] | None = None,
           residue: list[Rec] | None = None) -> State:
    """Build a state over W1..W3: W1, W2 live and W3 residue unless overridden.

    Returns:
        the state.

    """
    return validate({
        "counter": _COUNTER, "project_root": str(root),
        "waypoints": [_wp("W1"), _wp("W2")] if waypoints is None else waypoints,
        "residue": [_res("W3")] if residue is None else residue,
    })


def test_a_clean_state_has_no_findings(tmp_path: Path) -> None:
    """The positive control: a clean state yields no finding from any property."""
    assert chk.check(_state(tmp_path)) == []


def test_a_vanished_symbol_is_not_coverable(tmp_path: Path) -> None:
    """An issued symbol in neither list is a coverage finding."""
    found = chk.coverage(_state(tmp_path, waypoints=[_wp("W1")]))
    assert found == [f"W2: issued (counter={_COUNTER}) but in neither waypoints nor residue"]


def test_a_duplicate_live_symbol_is_found(tmp_path: Path) -> None:
    """A symbol claimed twice fails the check (el-openglo's `--check` passed it)."""
    found = chk.check(_state(tmp_path, waypoints=[_wp("W1"), _wp("W1"), _wp("W2")]))
    assert "W1: claimed 2 times" in found


def test_a_symbol_live_and_residue_is_a_duplicate(tmp_path: Path) -> None:
    """A symbol in both lists is claimed twice."""
    state = _state(tmp_path, residue=[_res("W3"), _res("W2")])
    assert chk.duplicates(state) == ["W2: claimed 2 times"]


def test_a_malformed_symbol_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    """`Wx` is reported (gabion crashed with ValueError on `int()`)."""
    state = _state(tmp_path, waypoints=[_wp("W1"), _wp("W2"), _wp("Wx")])
    assert "'Wx': not a W<n> symbol" in chk.check(state)


def test_a_symbol_above_the_counter_is_found(tmp_path: Path) -> None:
    """`W999` above counter=3 is found (el-openglo's `--check` passed it)."""
    state = _state(tmp_path, waypoints=[_wp("W1"), _wp("W2"), _wp(f"W{_ABOVE}")])
    assert chk.above_counter(state) == [f"W{_ABOVE}: above counter={_COUNTER}"]


def test_a_reasonless_drop_is_found(tmp_path: Path) -> None:
    """A residue entry whose reason is blank is found."""
    state = _state(tmp_path, residue=[_res("W3", "  ")])
    assert chk.reasons(state) == ["W3: residue without a reason"]


def test_a_dangling_symbol_edge_is_found(tmp_path: Path) -> None:
    """An `enables` target that looks like a symbol and resolves nowhere is found."""
    state = _state(tmp_path, waypoints=[_wp("W1", enables=["W9"]), _wp("W2")])
    assert chk.edges(state) == ["W1 -> W9: dangling edge"]


def test_a_party_in_blocked_on_is_not_an_edge(tmp_path: Path) -> None:
    """A `blocked_on` naming a party, not a symbol, is not a dangling edge."""
    w1 = _wp("W1", "blocked", blocked_on=["mikemol", "W2"], blocked_kind="human")
    assert chk.edges(_state(tmp_path, waypoints=[w1, _wp("W2")])) == []


def test_a_bogus_status_is_found(tmp_path: Path) -> None:
    """`status=bogus` is outside the enum and found."""
    state = _state(tmp_path, waypoints=[_wp("W1", "bogus"), _wp("W2")])
    assert chk.statuses(state) == ["W1: invalid status 'bogus'"]


def test_a_dropped_status_names_the_residue_move(tmp_path: Path) -> None:
    """`status=dropped` in the live list is a finding pointing at --drop (D5 default)."""
    state = _state(tmp_path, waypoints=[_wp("W1", "dropped"), _wp("W2")])
    assert "use --drop" in chk.statuses(state)[0]


@pytest.mark.parametrize(("on", "kind"), [([], "human"), (["mikemol"], None), (["x"], "robot")])
def test_an_underspecified_block_is_found(tmp_path: Path, on: list[str], kind: str | None) -> None:
    """A blocked waypoint without a party or an agent|human kind is found."""
    w1 = _wp("W1", "blocked", blocked_on=on, blocked_kind=kind)
    assert len(chk.blocked(_state(tmp_path, waypoints=[w1, _wp("W2")]))) == 1


def test_a_complete_block_is_not_found(tmp_path: Path) -> None:
    """A blocked waypoint with a party and a kind is not found."""
    w1 = _wp("W1", "blocked", blocked_on=["mikemol"], blocked_kind="human")
    assert chk.blocked(_state(tmp_path, waypoints=[w1, _wp("W2")])) == []


def test_a_bare_string_list_field_is_found(tmp_path: Path) -> None:
    """`blocked_on="mikemol"` is found as the wrong type (el-openglo's `--set` stored it)."""
    state = _state(tmp_path, waypoints=[_wp("W1", blocked_on="mikemol"), _wp("W2")])
    assert chk.field_types(state) == ["W1: blocked_on is str, not a list"]


@pytest.mark.parametrize("root", ["relative/path", ""])
def test_a_relative_or_empty_root_is_found(tmp_path: Path, root: str) -> None:
    """A project_root that is relative or empty is found."""
    state = _state(tmp_path)
    state.doc["project_root"] = root
    assert len(chk.root(state)) == 1


def test_a_missing_root_is_found(tmp_path: Path) -> None:
    """A project_root that does not exist is found."""
    assert len(chk.root(_state(tmp_path / "absent"))) == 1


def test_evidence_naming_a_missing_path_is_found(tmp_path: Path) -> None:
    """An evidence path that does not exist is found; one that exists is not (positive control)."""
    (tmp_path / "here.txt").write_text("x", encoding="utf-8")
    ev = f"commit abc; ({tmp_path}/here.txt), {tmp_path}/gone.txt; relative/x"
    state = _state(tmp_path, waypoints=[_wp("W1", evidence=ev), _wp("W2")])
    assert chk.evidence_findings(state) == [
        f"W1: evidence names {tmp_path}/gone.txt, which does not exist"]


def test_a_historical_name_in_residue_with_a_reason_is_admitted(tmp_path: Path) -> None:
    """`W50b` in residue with a reason is admitted; a live `Wx` beside it is still found."""
    state = _state(tmp_path, waypoints=[_wp("W1"), _wp("W2"), _wp(_BAD)],
                   residue=[_res("W3"), _res(_HISTORICAL, _HISTORICAL_REASON)])
    assert chk.malformed(state) == [f"{_BAD!r}: not a W<n> symbol"]


def test_a_historical_name_is_refused_live(tmp_path: Path) -> None:
    """`W50b` in the live waypoints is refused, reason or not."""
    state = _state(tmp_path, waypoints=[_wp("W1"), _wp("W2"), _wp(_HISTORICAL)])
    assert chk.malformed(state) == [f"{_HISTORICAL!r}: not a W<n> symbol"]


def test_a_reasonless_historical_name_in_residue_is_refused(tmp_path: Path) -> None:
    """`W50b` in residue with a blank reason is refused as malformed."""
    state = _state(tmp_path, residue=[_res("W3"), _res(_HISTORICAL, "  ")])
    assert chk.malformed(state) == [f"{_HISTORICAL!r}: not a W<n> symbol"]


def test_a_bazel_label_is_not_an_evidence_path(tmp_path: Path) -> None:
    """Summit's W37 labels are not reported; a real missing path beside them is (control)."""
    state = _state(tmp_path, waypoints=[_wp("W1", evidence=_W37_EVIDENCE), _wp("W2")])
    assert chk.evidence_findings(state) == [f"W1: evidence names {_MISSING}, which does not exist"]


def test_a_sentence_final_mark_is_not_part_of_an_evidence_path(tmp_path: Path) -> None:
    """A real file ending a sentence (`.`, `).`, `,`) is found, not reported missing."""
    (tmp_path / _NOTE).write_text("x", encoding="utf-8")
    ev = f"see {tmp_path}/{_NOTE}. Also ({tmp_path}/{_NOTE}). And {tmp_path}/{_NOTE},"
    state = _state(tmp_path, waypoints=[_wp("W1", evidence=ev), _wp("W2")])
    assert chk.evidence_findings(state) == []


def test_a_missing_path_is_reported_without_its_sentence_period(tmp_path: Path) -> None:
    """A missing path ending a sentence is still reported (control), named without the period."""
    state = _state(tmp_path, waypoints=[_wp("W1", evidence=f"wrote {tmp_path}/{_GONE}."),
                                        _wp("W2")])
    assert chk.evidence_findings(state) == [
        f"W1: evidence names {tmp_path}/{_GONE}, which does not exist"]


def test_a_dot_that_is_part_of_a_real_name_is_kept(tmp_path: Path) -> None:
    """A real name ending in `.`, then a sentence period, resolves to that real name."""
    (tmp_path / _DOTTED).write_text("x", encoding="utf-8")
    state = _state(tmp_path, waypoints=[_wp("W1", evidence=f"kept {tmp_path}/{_DOTTED}."),
                                        _wp("W2")])
    assert chk.evidence_findings(state) == []


def test_the_bare_check_does_not_read_evidence(tmp_path: Path) -> None:
    """The bare check is cheap: a missing evidence path is not one of its findings."""
    state = _state(tmp_path, waypoints=[_wp("W1", evidence=f"{tmp_path}/gone"), _wp("W2")])
    assert chk.check(state) == []

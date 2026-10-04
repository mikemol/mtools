# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the ladder: rungs in rank order, a floor that fails closed, a flip-set graded."""

from __future__ import annotations

import pytest

from mikemol.grade import grade

_ASCENDING = ["broken", "vacuous", "indeterminate", "existence", "behavioral", "imported"]


def _behavioral(key: str, tests: list[grade.Json]) -> grade.Record:
    """Build a behavioral grade record flipped by `tests`.

    Returns:
        The record.

    """
    return {"key": key, "grade": "behavioral", "tests": tests}


def test_the_ladder_ranks_are_the_documented_total_order() -> None:
    """RANK_C lists the six rungs in strictly ascending rank and GRADE_C inverts it."""
    assert list(grade.RANK_C) == _ASCENDING
    assert sorted(grade.RANK_C.values()) == list(grade.RANK_C.values())
    assert len(set(grade.RANK_C.values())) == len(_ASCENDING)
    assert {grade.GRADE_C[v]: v for v in grade.GRADE_C} == grade.RANK_C
    assert grade.RANK_C["vacuous"] == 0
    assert grade.RANK_C["broken"] < grade.RANK_C["vacuous"]


def test_the_orthogonal_axes_hold_their_documented_values() -> None:
    """Corroboration, decisions, resolution and baseline are separate ordered axes."""
    assert grade.CORRO_C == {"single": 0, "correlated": 1, "distinct": 2, "independent": 3}
    assert grade.DECISIONS_C == {"unasserted": 0, "asserted": 1}
    assert grade.RESOLUTION_C == {"truncated": 0, "resolved": 1}
    assert grade.BASELINE_C == {"unreachable": 0, "refuted": 1, "established": 2}
    assert grade.STRENGTH["vacuous"] < grade.STRENGTH["existence"] < grade.STRENGTH["behavioral"]
    assert grade.ORDER == {"existence": 1, "behavioral": 2}


def test_scopes_moved_from_bib_keep_their_values_and_order() -> None:
    """SCOPES is paperkit's `bib._SCOPES` verbatim and SCOPE_C ranks it fragment < full."""
    assert grade.SCOPES == ("fragment", "full")
    assert grade.SCOPE_C == {"fragment": 0, "full": 1}
    assert "full" in grade.SCOPE_C
    assert "partial" not in grade.SCOPE_C


def test_rungs_is_the_ladder_in_display_order() -> None:
    """Descending by default, ascending on request."""
    assert grade.rungs() == list(reversed(_ASCENDING))
    assert grade.rungs(descending=True) == list(reversed(_ASCENDING))
    assert grade.rungs(descending=False) == _ASCENDING


def test_below_is_exactly_the_rungs_ranked_under_the_floor() -> None:
    """For every floor the failing set is the strictly lower rungs, lowest first."""
    for position, floor in enumerate(_ASCENDING):
        assert grade.below(floor) == _ASCENDING[:position]
    assert "imported" not in grade.below("behavioral")
    assert "indeterminate" in grade.below("behavioral")
    assert "broken" in grade.below("behavioral")


def test_below_refuses_a_floor_that_is_not_a_rung() -> None:
    """A typo'd floor raises instead of grading everything green."""
    with pytest.raises(KeyError):
        grade.below("behaviorall")


def test_a_failing_baseline_is_broken_and_refuted() -> None:
    """A check that does not pass in a pristine sandbox grades broken, baseline refuted."""
    rec = grade.grade_from_sens(baseline=False, sens=[])
    assert rec["grade"] == "broken"
    assert rec["baseline"] == "refuted"
    assert rec["tests"] == []
    assert rec["why"] == "check does not pass in a pristine sandbox — repo is not green"
    assert rec["not_higher"] == "—"
    assert rec["not_lower"] == "—"


def test_an_unreachable_baseline_is_broken_but_does_not_claim_the_repo_is_red() -> None:
    """The same grade, a different axis value, and a why that names the toolchain."""
    rec = grade.grade_from_sens(baseline=False, sens=["x.tex"], reachable=False)
    assert rec["grade"] == "broken"
    assert rec["baseline"] == "unreachable"
    assert rec["tests"] == []
    assert isinstance(rec["why"], str)
    assert rec["why"].startswith("check could not be REACHED in a pristine sandbox")
    assert rec["why"].endswith("(this is NOT a statement that the repo is red)")


def test_a_flip_set_grades_behavioral_and_keeps_the_flipped_tests() -> None:
    """Some mutation flipping the check proves it falsifiable."""
    rec = grade.grade_from_sens(baseline=True, sens=["a.tex", "b.tex"])
    assert rec["grade"] == "behavioral"
    assert rec["tests"] == ["a.tex", "b.tex"]
    assert rec["baseline"] == "established"
    assert rec["why"] == "falsifiable — corrupting 2 input(s) flips it red"
    assert rec["not_lower"] == (
        "not indeterminate/vacuous: a mutation DOES flip it (sensitive to 2 input(s))"
    )
    assert isinstance(rec["not_higher"], str)
    assert rec["not_higher"].startswith("behavioral is the top tier")


def test_an_empty_flip_set_grades_indeterminate_without_a_baseline_value() -> None:
    """No mutation flips it: indeterminate, no tests, and the record names no baseline."""
    rec = grade.grade_from_sens(baseline=True, sens=[])
    assert rec["grade"] == "indeterminate"
    assert rec["tests"] == []
    assert "baseline" not in rec
    assert isinstance(rec["why"], str)
    assert rec["why"].startswith("no generic mutation flips it")
    assert isinstance(rec["not_higher"], str)
    assert rec["not_higher"].startswith("to rise: a targeted counter-fixture")
    assert rec["not_lower"] == "not provably vacuous: it runs a cmd:, not a presupposed file:"


def test_reachability_does_not_move_the_rung() -> None:
    """Reachable or not, a passing baseline grades the same."""
    reached = grade.grade_from_sens(baseline=True, sens=["a"], reachable=True)
    unreached = grade.grade_from_sens(baseline=True, sens=["a"], reachable=False)
    assert reached == unreached


def test_content_sensitivity_marks_only_behavioral_records_flipped_by_content() -> None:
    """A behavioral check flipped by the document's own file is content sensitive."""
    own = _behavioral("own", ["sandbox/warrants.bib"])
    engine = _behavioral("engine", ["engine/grader.py"])
    mixed = _behavioral("mixed", ["engine/grader.py", "paper/rubric.tsv"])
    weak: grade.Record = {"key": "weak", "grade": "indeterminate", "tests": ["warrants.bib"]}
    records = [own, engine, mixed, weak]
    out = grade.mark_content_sensitive(records, {"warrants.bib", "rubric.tsv"})
    assert out is records
    assert own["content_sensitive"] is True
    assert engine["content_sensitive"] is False
    assert mixed["content_sensitive"] is True
    assert "content_sensitive" not in weak


def test_content_sensitivity_of_a_record_without_a_test_list_is_false() -> None:
    """A tests value that is not a list holds no test files."""
    odd: grade.Record = {"key": "odd", "grade": "behavioral", "tests": "warrants.bib"}
    grade.mark_content_sensitive([odd], {"warrants.bib"})
    assert odd["content_sensitive"] is False

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the clamp: no claim is better grounded than the weakest premise it rests on."""

from __future__ import annotations

from mikemol.grade import grade

_BEHAVIORAL_OVER_VACUOUS = 3
_BEHAVIORAL_OVER_EXISTENCE = 1
_BEHAVIORAL_OVER_BROKEN = 4
_IMPORTED_OVER_BROKEN = 5


def _rec(
    key: str,
    rung: str,
    rests_on: list[str] | None = None,
    delegates_to: dict[str, grade.Json] | None = None,
) -> grade.Record:
    """Build a grade record resting on `rests_on` and optionally delegating to an owner claim.

    Returns:
        The record.

    """
    rec: grade.Record = {"key": key, "grade": rung}
    if rests_on is not None:
        rec["rests-on"] = list(rests_on)
    if delegates_to is not None:
        rec["delegates_to"] = delegates_to
    return rec


_EDGE: dict[str, grade.Json] = {"owner": "o", "claim": "c"}
_OWNED: dict[tuple[str, str], grade.Json] = {("o", "c"): "vacuous"}


def test_a_claim_is_clamped_to_the_weakest_premise_it_rests_on() -> None:
    """A behavioral claim resting on a vacuous one is effectively vacuous, pinned by it."""
    above = _rec("a", "behavioral", ["b"])
    below = _rec("b", "vacuous")
    out = grade.clamp([above, below])
    assert out == [above, below]
    assert above["effective_grade"] == "vacuous"
    assert above["clamp"] == _BEHAVIORAL_OVER_VACUOUS
    assert above["clamped_by"] == "b"
    assert above["clamp_path"] == ["b"]
    assert below["effective_grade"] == "vacuous"
    assert below["clamp"] == 0
    assert below["clamped_by"] is None
    assert below["clamp_path"] == []


def test_the_clamp_is_transitive_and_carries_the_whole_chain() -> None:
    """Claim a rests on b rests on c: a is pinned by b but its path runs on to c."""
    top = _rec("a", "behavioral", ["b"])
    mid = _rec("b", "behavioral", ["c"])
    leaf = _rec("c", "existence")
    grade.clamp([top, mid, leaf])
    assert top["effective_grade"] == "existence"
    assert top["clamp"] == _BEHAVIORAL_OVER_EXISTENCE
    assert top["clamped_by"] == "b"
    assert top["clamp_path"] == ["b", "c"]
    assert mid["clamped_by"] == "c"
    assert mid["clamp_path"] == ["c"]


def test_the_weakest_of_several_premises_pins_the_claim() -> None:
    """The minimum over all rests-on edges wins, not the first."""
    claim = _rec("a", "imported", ["b", "c"])
    grade.clamp([claim, _rec("b", "existence"), _rec("c", "indeterminate")])
    assert claim["effective_grade"] == "indeterminate"
    assert claim["clamped_by"] == "c"


def test_a_stronger_premise_does_not_raise_a_claim() -> None:
    """The clamp only lowers: an existence claim on a behavioral premise stays existence."""
    claim = _rec("a", "existence", ["b"])
    grade.clamp([claim, _rec("b", "behavioral")])
    assert claim["effective_grade"] == "existence"
    assert claim["clamp"] == 0
    assert claim["clamped_by"] is None


def test_a_cycle_and_a_self_edge_terminate_without_clamping() -> None:
    """Grounding edges that loop back are skipped on the stack."""
    first = _rec("a", "behavioral", ["b", "a"])
    second = _rec("b", "behavioral", ["a"])
    grade.clamp([first, second])
    assert first["effective_grade"] == "behavioral"
    assert second["effective_grade"] == "behavioral"
    assert first["clamped_by"] is None


def test_an_unknown_grade_ranks_as_vacuous() -> None:
    """An unrecognised grade string reads as rank 0."""
    odd = _rec("a", "mystery")
    grade.clamp([odd])
    assert odd["effective_grade"] == "vacuous"
    assert odd["clamp"] == 0


def test_an_empty_record_list_clamps_to_itself() -> None:
    """Nothing to grade, nothing returned."""
    assert grade.clamp([]) == []


def test_scope_defaults_to_full_and_discloses_a_declared_fragment() -> None:
    """`entails` is carried through as `scope`; its absence reads as full."""
    plain = _rec("a", "behavioral")
    partial = _rec("b", "behavioral")
    partial["entails"] = "fragment"
    grade.clamp([plain, partial])
    assert plain["scope"] == "full"
    assert partial["scope"] == "fragment"
    assert partial["effective_grade"] == "behavioral"


def test_a_premise_with_no_record_imposes_no_constraint_and_is_not_truncation() -> None:
    """Without the bib's key set, a missing premise reads as outside this argument."""
    claim = _rec("a", "behavioral", ["elsewhere"])
    grade.clamp([claim])
    assert claim["effective_grade"] == "behavioral"
    assert claim["unresolved"] == []
    assert claim["resolution"] == "resolved"
    assert claim["effective_min"] == "behavioral"
    assert claim["effective_max"] == "behavioral"
    assert claim["interval_width"] == 0


def test_a_premise_outside_the_key_set_is_still_outside_this_argument() -> None:
    """With keys supplied, a missing premise that is not in the bib is still no constraint."""
    claim = _rec("a", "behavioral", ["elsewhere"])
    grade.clamp([claim], keys={"a"})
    assert claim["unresolved"] == []
    assert claim["resolution"] == "resolved"


def test_a_premise_in_the_key_set_but_never_graded_is_a_truncated_unfold() -> None:
    """The claim stays optimistically behavioral but its interval widens to the floor."""
    claim = _rec("a", "behavioral", ["ungraded"])
    grade.clamp([claim], keys={"a", "ungraded"})
    assert claim["effective_grade"] == "behavioral"
    assert claim["unresolved"] == ["ungraded"]
    assert claim["resolution"] == "truncated"
    assert claim["effective_min"] == "broken"
    assert claim["effective_max"] == "behavioral"
    assert claim["interval_width"] == _BEHAVIORAL_OVER_BROKEN


def test_an_unresolved_premise_is_appended_to_an_existing_unresolved_list() -> None:
    """Earlier unresolved entries are kept."""
    claim = _rec("a", "behavioral", ["ungraded"])
    claim["unresolved"] = ["earlier"]
    grade.clamp([claim], keys={"ungraded"})
    assert claim["unresolved"] == ["earlier", "ungraded"]


def test_truncation_is_transitive_though_the_claim_own_edges_resolve() -> None:
    """A claim resting on a truncated premise reads truncated, with a wide interval."""
    above = _rec("x", "behavioral", ["a"])
    truncated = _rec("a", "behavioral", ["ungraded"])
    grade.clamp([above, truncated], keys={"ungraded"})
    assert above["unresolved"] == []
    assert above["resolution"] == "truncated"
    assert above["effective_grade"] == "behavioral"
    assert above["effective_min"] == "broken"


def test_truncation_walk_survives_a_cycle() -> None:
    """A loop of resolved claims is resolved, not an endless walk."""
    first = _rec("a", "behavioral", ["b"])
    second = _rec("b", "behavioral", ["a"])
    grade.clamp([first, second])
    assert first["resolution"] == "resolved"
    assert second["resolution"] == "resolved"


def test_a_delegation_clamps_to_the_owners_bare_grade() -> None:
    """A weak owner grade pulls an imported claim down and is carried for the reader."""
    claim = _rec("a", "imported", delegates_to=_EDGE)
    grade.clamp([claim], owner_grades=_OWNED)
    assert claim["effective_grade"] == "vacuous"
    assert claim["clamped_by"] == "o#c"
    assert claim["clamp_path"] == ["o#c"]
    assert claim["delegated"] == {
        "grade": "vacuous",
        "effective_grade": "vacuous",
        "clamped_by": None,
    }
    assert claim["resolution"] == "resolved"
    assert claim["effective_min"] == "vacuous"
    assert claim["interval_width"] == 0


def test_a_delegation_reads_the_owners_effective_grade_and_continues_its_pin() -> None:
    """The owner's pair is bounded by its EFFECTIVE grade and its own pin extends the path."""
    pair: grade.Json = {"grade": "behavioral", "effective_grade": "existence", "clamped_by": "p"}
    claim = _rec("a", "imported", delegates_to=_EDGE)
    grade.clamp([claim], owner_grades={("o", "c"): pair})
    assert claim["effective_grade"] == "existence"
    assert claim["clamped_by"] == "o#c"
    assert claim["clamp_path"] == ["o#c", "p"]
    assert claim["delegated"] == pair
    assert claim["effective_min"] == "existence"


def test_a_delegation_pair_without_an_effective_grade_falls_back_to_its_grade() -> None:
    """Only `grade` present: that is the bound."""
    claim = _rec("a", "imported", delegates_to=_EDGE)
    grade.clamp([claim], owner_grades={("o", "c"): {"grade": "indeterminate"}})
    assert claim["effective_grade"] == "indeterminate"


def test_a_strong_owner_imposes_no_clamp() -> None:
    """An imported owner leaves an imported claim where it was."""
    claim = _rec("a", "imported", delegates_to=_EDGE)
    grade.clamp([claim], owner_grades={("o", "c"): "imported"})
    assert claim["effective_grade"] == "imported"
    assert claim["clamped_by"] is None
    assert claim["clamp_path"] == []
    assert claim["resolution"] == "resolved"


def test_a_delegation_with_no_owner_grade_is_unresolved_and_widens_the_interval() -> None:
    """The edge imposes nothing, says so by name, and the interval records the cost."""
    claim = _rec("a", "imported", delegates_to=_EDGE)
    grade.clamp([claim])
    assert claim["effective_grade"] == "imported"
    assert claim["clamp"] == 0
    assert claim["unresolved"] == ["o#c"]
    assert claim["resolution"] == "truncated"
    assert claim["effective_min"] == "broken"
    assert claim["interval_width"] == _IMPORTED_OVER_BROKEN


def test_a_half_named_delegation_cannot_be_looked_up_and_is_unresolved() -> None:
    """A delegation with no claim name is unresolved, named with None for the missing half."""
    claim = _rec("a", "imported", delegates_to={"owner": "o"})
    grade.clamp([claim], owner_grades=_OWNED)
    assert claim["unresolved"] == ["o#None"]


def test_an_empty_or_non_mapping_delegation_is_no_delegation() -> None:
    """Neither an empty mapping nor a stray string delegates."""
    empty = _rec("a", "imported", delegates_to={})
    stray = _rec("b", "imported")
    stray["delegates_to"] = "o#c"
    grade.clamp([empty, stray], owner_grades=_OWNED)
    assert empty["effective_grade"] == "imported"
    assert empty["unresolved"] == []
    assert stray["effective_grade"] == "imported"
    assert stray["unresolved"] == []


def test_a_non_string_rests_on_item_is_not_an_edge() -> None:
    """Only string premise keys are edges; a non-list rests-on holds none."""
    claim = _rec("a", "behavioral")
    claim["rests-on"] = [7, "b"]
    other = _rec("c", "behavioral")
    other["rests-on"] = "b"
    grade.clamp([claim, other, _rec("b", "vacuous")])
    assert claim["clamped_by"] == "b"
    assert other["clamped_by"] is None

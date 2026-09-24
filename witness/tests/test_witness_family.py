# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.witness.witness_family`: substrate's 18 selftest arms, ported."""

from __future__ import annotations

import pytest

from mikemol.witness import witness_family as wf

_THREE_CASES = 3
_FOUR_CASES = 4


def _family() -> wf.Family:
    """Build a two-member family whose second member protects the first.

    Returns:
        the family.

    """
    return wf.of(
        key="T99-demo",
        apex="every subject resolves",
        subject="entries in a corpus",
        members=[
            wf.Member(
                name="a_resolvable_target_is_not_reported",
                claim="a target that exists is left alone",
            ),
            wf.Member(
                name="a_dangling_target_is_reported",
                claim="the positive control: a missing target IS named",
                cases=2,
                premises=("a_resolvable_target_is_not_reported",),
            ),
        ],
    )


def _split() -> wf.Family:
    """Build a family whose second member is itself a family: the n-split shape.

    Returns:
        the family.

    """
    inner = wf.of(
        key="T99-demo-inner",
        apex="the walk returns a usable population",
        subject="the files the walk returns",
        members=[
            wf.Member(name="the_population_is_non_empty", claim="zero reads as a clean tree"),
            wf.Member(name="the_population_is_sorted", claim="a caller need not re-sort"),
        ],
    )
    return wf.of(
        key="T99-demo",
        apex="a",
        subject="s",
        members=[
            wf.Member(name="a_flat_member", claim="one fact"),
            wf.Member(name="a_split_member", claim="two facts, now named", family=inner),
        ],
    )


def test_the_count_is_derived_from_the_members() -> None:
    """The total is the sum of member cases, not a typed constant or the member count.

    ⚑ A member declaring two cases contributes two, so a family returning its member COUNT reads
    2 here instead of 3.
    """
    assert _family().count == _THREE_CASES


def test_adding_a_member_moves_the_count() -> None:
    """The count tracks the roster: the property a hand-summed constant cannot have.

    ⚑⚑ The measured defect: a hand-summed `_CASE_COUNT` stays put when a member is added.
    """
    base = _family()
    grown = wf.of(
        key=base.key,
        apex=base.apex,
        subject=base.subject,
        members=[*base.members, wf.Member(name="a_third_case", claim="another fact")],
    )
    assert grown.count == _FOUR_CASES


def test_a_premise_naming_a_member_is_not_dangling() -> None:
    """A resolvable premise edge is left alone."""
    assert _family().dangling_premises() == ()


def test_a_premise_naming_nothing_is_reported() -> None:
    """A premise no member supplies is NAMED: the positive control.

    ⚑⚑ Without it, a family whose control was deleted still reads as protected.
    """
    broken = wf.of(
        key="T99-demo",
        apex="a",
        subject="s",
        members=[wf.Member(name="only_member", claim="c", premises=("a_deleted_control",))],
    )
    assert broken.dangling_premises() == (("only_member", "a_deleted_control"),)


def test_a_duplicate_member_name_is_refused() -> None:
    """Two members sharing a name raise at construction, naming it.

    ⚑ Addressability is the point of a name: a duplicate makes `member()` and premises ambiguous.
    """
    with pytest.raises(ValueError, match="same"):
        wf.of(
            key="T99-demo",
            apex="a",
            subject="s",
            members=[wf.Member(name="same", claim="one"), wf.Member(name="same", claim="two")],
        )


def test_a_missing_member_lookup_names_the_roster() -> None:
    """An unknown member raises and says what IS there: a typo is the common reason to arrive."""
    with pytest.raises(KeyError, match="a_dangling_target_is_reported"):
        _family().member("no_such_member")


def test_an_unprotected_member_is_censused_not_flagged() -> None:
    """Members nothing rests on are reported; members cited as a premise are not.

    ⚑ A census, not a finding: most members legitimately stand alone.
    """
    got = _family().unprotected()
    assert "a_dangling_target_is_reported" in got
    assert "a_resolvable_target_is_not_reported" not in got


def test_the_rendered_family_surfaces_a_dangling_premise() -> None:
    """The render marks a dangling premise: a defect printed as inventory reads as inventory."""
    broken = wf.of(
        key="T99-demo",
        apex="a",
        subject="s",
        members=[wf.Member(name="only_member", claim="c", premises=("gone",))],
    )
    assert "DANGLING PREMISE" in wf.render(broken)


def test_the_summary_reports_its_denominator() -> None:
    """An empty roster says so rather than rendering nothing.

    ⚑ An empty string cannot tell *no families* from *nothing read*.
    """
    assert "no families" in wf.summarize([])


def test_the_summary_totals_every_family() -> None:
    """The roster line sums cases across families, not members."""
    assert "6 case(s)" in wf.summarize([_family(), _family()])


def test_the_member_roster_keeps_its_order() -> None:
    """`names` preserves roster order: it is the reading order of the projected prose."""
    assert _family().names == (
        "a_resolvable_target_is_not_reported",
        "a_dangling_target_is_reported",
    )


def test_a_split_members_count_comes_from_its_family() -> None:
    """A member holding a sub-family reports the sub-family's total.

    ⚑⚑ Splitting must not move the population: a count that changed during a split is a dropped
    or invented assertion.
    """
    assert _split().count == _THREE_CASES


def test_a_member_declaring_both_a_family_and_cases_is_refused() -> None:
    """A split member cannot also hand-declare a total: two authorities on one size."""
    inner = wf.of(key="i", apex="a", subject="s", members=[wf.Member(name="one", claim="c")])
    with pytest.raises(ValueError, match="cases"):
        wf.of(
            key="T99-demo",
            apex="a",
            subject="s",
            members=[wf.Member(name="both", claim="c", cases=5, family=inner)],
        )


def test_the_leaves_flatten_to_dotted_paths() -> None:
    """Nesting resolves to one flat roster a runner can address."""
    assert _split().leaves() == (
        "a_flat_member",
        "a_split_member.the_population_is_non_empty",
        "a_split_member.the_population_is_sorted",
    )


def test_depth_reports_the_nesting() -> None:
    """A flat family is depth 1 and a split one is 2: both arms, or a constant would pass."""
    assert _family().depth() == 1
    assert _split().depth() == len(["outer", "inner"])


def test_an_unsplit_member_is_censused() -> None:
    """A member asserting several facts under one name is named as the split work list.

    ⚑⚑ Measured in substrate: 92 of 285 arms were in that state.
    """
    assert _family().unsplit() == (("a_dangling_target_is_reported", 2),)


def test_a_split_member_is_not_censused_as_unsplit() -> None:
    """Splitting a member removes it from the work list: the positive control.

    ⚑ Without it, a census naming every member would satisfy the case above.
    """
    assert _split().unsplit() == ()


def test_the_render_marks_an_unsplit_member() -> None:
    """The render says which members still hold several unnamed facts."""
    assert "UNSPLIT" in wf.render(_family())

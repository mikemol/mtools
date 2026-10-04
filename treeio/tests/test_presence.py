# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `presence`: the three-valued answer of a read, and its refusal of unknown names."""

from __future__ import annotations

import pytest

from mikemol.treeio.presence import Presence


def test_the_roster_is_the_definition_in_declaration_order() -> None:
    """The roster lists exactly PRESENT, ABSENT and BROKEN, so no member can be omitted."""
    assert Presence.all() == (Presence.PRESENT, Presence.ABSENT, Presence.BROKEN)


def test_only_broken_is_a_defect() -> None:
    """A defect is a read that did not happen: BROKEN, and neither PRESENT nor ABSENT."""
    assert [p.is_defect for p in Presence.all()] == [False, False, True]


def test_every_member_has_its_own_gloss() -> None:
    """Each member explains itself, and the explanations differ."""
    glosses = [p.gloss for p in Presence.all()]
    assert len(set(glosses)) == len(glosses)
    assert "zero-byte" in Presence.ABSENT.gloss
    assert "NEVER silently a miss" in Presence.BROKEN.gloss
    assert "possibly b''" in Presence.PRESENT.gloss


def test_a_member_equals_its_name_as_a_string() -> None:
    """A caller that has not migrated and compares to a bare name keeps working."""
    assert Presence.ABSENT == "ABSENT"
    assert Presence.ABSENT != "BROKEN"
    assert Presence.ABSENT != Presence.PRESENT
    twin = Presence("ABSENT", is_defect=True, gloss="a distinct object with the same name")
    assert twin == Presence.ABSENT
    assert twin is not Presence.ABSENT
    assert twin.is_defect is True
    assert twin.gloss == "a distinct object with the same name"


def test_a_member_hashes_like_its_name() -> None:
    """A member and its name land on the same dictionary key."""
    table: dict[object, int] = {"ABSENT": 1}
    assert table[Presence.ABSENT] == 1
    assert hash(Presence.BROKEN) == hash("BROKEN")


def test_members_order_by_name_against_members_and_strings() -> None:
    """Sorting follows the names, whether the other side is a member or a string."""
    assert sorted(Presence.all()) == [Presence.ABSENT, Presence.BROKEN, Presence.PRESENT]
    assert Presence.ABSENT < "BROKEN"
    assert not Presence.PRESENT < "BROKEN"
    assert Presence.ABSENT < Presence.BROKEN


def test_a_member_renders_as_its_name_and_reprs_as_a_constructor() -> None:
    """The string form is the bare name and the repr names the type."""
    assert str(Presence.BROKEN) == "BROKEN"
    assert repr(Presence.BROKEN) == "Presence('BROKEN')"


def test_of_round_trips_every_member() -> None:
    """Resolving a member's own name returns that member."""
    for member in Presence.all():
        assert Presence.of(member.name) is member


def test_of_refuses_an_unknown_name_and_lists_the_known_ones() -> None:
    """An unrecognised name raises rather than defaulting, and the message names the roster."""
    with pytest.raises(KeyError) as caught:
        Presence.of("MAYBE")
    message = str(caught.value)
    assert "unknown presence 'MAYBE'" in message
    assert "known: PRESENT, ABSENT, BROKEN" in message

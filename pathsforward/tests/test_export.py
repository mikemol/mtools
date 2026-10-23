# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The version-2 export keeps withheld cards out whole and publishes the rest untouched (W1837).

⚑ ONLY THE BOOLEAN TRUE WITHHOLDS: a card with the flag false, absent, or spelled as a string is
published, and the published card is the input card itself, no field cut and none added.
"""

from __future__ import annotations

from typing import cast

from mikemol.pathsforward import export

Rec = dict[str, object]
_AT = "2026-10-22T22:00:00Z"
_MARKER = "an address literal in evidence"


def _card(sym: str, **extra: object) -> Rec:
    card: Rec = {"symbol": sym, "title": f"t{sym}", "evidence": "plain"}
    card.update(extra)
    return card


def _cards(built: Rec) -> list[Rec]:
    return cast("list[Rec]", built["cards"])


def _withheld(built: Rec) -> list[str]:
    return cast("list[str]", built["withheld"])


def test_a_flagged_card_is_a_bare_ref_and_absent_from_cards() -> None:
    """The withheld card leaves no field behind: its text appears nowhere in the export."""
    flagged = _card("W2", withheld=True, evidence=_MARKER)
    built = export.build("mtools", _AT, [_card("W1"), flagged, _card("W3")])
    assert _withheld(built) == ["mtools:W2"]
    assert [c["symbol"] for c in _cards(built)] == ["W1", "W3"]
    assert _MARKER not in repr(built)


def test_an_unflagged_card_is_published_exactly_as_it_is() -> None:
    """No field is cut and none added: the published card equals the input."""
    plain = _card("W1", manifest=["a.py"], size_class="small")
    built = export.build("mtools", _AT, [plain])
    assert _cards(built) == [plain]


def test_only_the_boolean_true_withholds() -> None:
    """A false flag, a missing one and a string are all published."""
    cards = [_card("W1", withheld=False), _card("W2"), _card("W3", withheld="true")]
    built = export.build("mtools", _AT, cards)
    assert _withheld(built) == []
    assert len(_cards(built)) == len(cards)


def test_the_envelope_names_the_version_the_repo_and_the_time() -> None:
    """Version 2, the repo and as_of, and an empty queue gives empty lists."""
    built = export.build("mtools", _AT, [])
    assert built == {
        "version": 2,
        "repo": "mtools",
        "as_of": _AT,
        "cards": [],
        "withheld": [],
    }


def test_the_time_is_the_newest_stamp_on_any_card_and_the_epoch_when_there_is_none() -> None:
    """last_worked on a live card and dropped_at on a residue entry both count, newest wins."""
    older = _card("W1", last_worked="2026-10-20T00:00:00Z")
    newer = {"symbol": "W2", "dropped_at": "2026-10-22T00:00:00Z"}
    assert export.stamp_of([older, newer]) == "2026-10-22T00:00:00Z"
    assert export.stamp_of([_card("W3")]) == export.EPOCH
    assert export.stamp_of([]) == export.EPOCH


def test_a_flagged_card_with_no_symbol_leaves_nothing_in_either_list() -> None:
    """It cannot be cited, so no ref, and it must not leave, so not in cards."""
    built = export.build("mtools", _AT, [{"title": "t", "withheld": True}])
    assert _cards(built) == []
    assert _withheld(built) == []

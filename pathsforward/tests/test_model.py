# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the model: a malformed document is refused, a malformed symbol never crashes."""

from __future__ import annotations

import pytest

from mikemol.pathsforward.model import (
    MalformedStateError,
    State,
    strlist,
    symbol_number,
    text,
    ticks,
    validate,
)

_SEVEN = 7
_THREE = 3


def _doc(**over: object) -> dict[str, object]:
    """Build a minimal valid document, with overrides.

    Returns:
        the document.

    """
    doc: dict[str, object] = {"counter": 1, "waypoints": [{"symbol": "W1"}], "residue": []}
    doc.update(over)
    return doc


def test_a_symbol_parses_to_its_number() -> None:
    """`W7` parses to 7."""
    assert symbol_number("W7") == _SEVEN


@pytest.mark.parametrize("bad", ["Wx", "W0", "W07", "w7", "W", "W7b", 7, None])
def test_a_malformed_symbol_parses_to_none(bad: object) -> None:
    """A malformed symbol parses to None rather than raising (gabion crashed on `Wx`)."""
    assert symbol_number(bad) is None


def test_validate_accepts_a_minimal_document() -> None:
    """A minimal document validates, and its lists are the document's own."""
    doc = _doc()
    state = validate(doc)
    assert isinstance(state, State)
    state.waypoints.append({"symbol": "W2"})
    assert doc["waypoints"] is state.waypoints


def test_validate_creates_an_absent_residue() -> None:
    """An absent residue is created empty."""
    doc = _doc()
    del doc["residue"]
    assert validate(doc).residue == []


@pytest.mark.parametrize("raw", [[], "x", None])
def test_validate_refuses_a_non_object(raw: object) -> None:
    """A document that is not an object is refused."""
    with pytest.raises(MalformedStateError, match="not a JSON object"):
        validate(raw)


def test_validate_refuses_non_list_waypoints() -> None:
    """A `waypoints` that is not a list is refused (summit's `_waypoints`)."""
    with pytest.raises(MalformedStateError, match="`waypoints` is not a list"):
        validate(_doc(waypoints="not a list"))


def test_validate_refuses_a_non_object_record() -> None:
    """A record that is not an object is refused."""
    with pytest.raises(MalformedStateError, match=r"`residue\[0\]` is not an object"):
        validate(_doc(residue=["W3"]))


def test_validate_refuses_a_record_without_a_string_symbol() -> None:
    """A record whose symbol is not a string is refused."""
    with pytest.raises(MalformedStateError, match="no string `symbol`"):
        validate(_doc(waypoints=[{"symbol": 1}]))


@pytest.mark.parametrize("counter", [True, -1, "3", None])
def test_validate_refuses_a_bad_counter(counter: object) -> None:
    """A counter that is not a non-negative integer is refused; a bool is not an integer here."""
    with pytest.raises(MalformedStateError, match="`counter`"):
        validate(_doc(counter=counter))


def test_text_reads_absent_and_null_as_empty() -> None:
    """An absent or null field reads as the empty string, anything else as its str."""
    assert (text({}, "k"), text({"k": None}, "k"), text({"k": _THREE}, "k")) == ("", "", "3")


def test_strlist_reads_a_bare_string_as_one_element() -> None:
    """A bare string is one element, never an iterable of characters."""
    assert strlist({"on": "mikemol"}, "on") == ["mikemol"]


def test_strlist_reads_a_list_and_an_absence() -> None:
    """A list reads as its elements' strings, and an absence as []."""
    assert (strlist({"on": ["a", _THREE]}, "on"), strlist({}, "on")) == (["a", "3"], [])


def test_ticks_reads_only_an_integer() -> None:
    """ticks_blocked reads an int, and a bool or an absence as 0."""
    got = (ticks({"ticks_blocked": _THREE}), ticks({"ticks_blocked": True}), ticks({}))
    assert got == (_THREE, 0, 0)

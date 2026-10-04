# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that no character `str.splitlines()` splits on can enter a ledger line."""

from __future__ import annotations

import pytest

from mikemol.pathsforward.ledger import Entry, MalformedEntryError, Parsed, line, parse

_STAMP = "2026-09-23T12:00:00Z"
_BMP = 0x10000
_BREAKS = tuple(chr(i) for i in range(_BMP) if len(f"a{chr(i)}b".splitlines()) > 1)


def _entry(**fields: str) -> Entry:
    """Build an entry with legal columns, overriding the named fields.

    Returns:
        the entry.

    """
    base = {
        "kind": "tick",
        "symbol": "--",
        "outcome": "done",
        "mechanism": "manual",
        "note": "n",
        "evidence": "",
    }
    return Entry(**{**base, **fields})


def test_derived_set_has_positive_controls() -> None:
    """The derived boundary set is non-empty and holds at least CR and U+2028."""
    assert _BREAKS
    assert chr(0x0D) in _BREAKS
    assert chr(0x2028) in _BREAKS


@pytest.mark.parametrize("ch", _BREAKS)
def test_note_refuses_every_boundary(ch: str) -> None:
    """A note holding any splitlines boundary is refused, naming its code point."""
    with pytest.raises(MalformedEntryError, match=f"U\\+{ord(ch):04X}"):
        line(_entry(note=f"a{ch}b"), _STAMP)


@pytest.mark.parametrize("ch", _BREAKS)
def test_evidence_refuses_every_boundary(ch: str) -> None:
    """Evidence holding any splitlines boundary is refused, naming its code point."""
    with pytest.raises(MalformedEntryError, match=f"U\\+{ord(ch):04X}"):
        line(_entry(evidence=f"a{ch}b"), _STAMP)


@pytest.mark.parametrize("ch", _BREAKS)
def test_token_columns_refuse_every_boundary(ch: str) -> None:
    """Every boundary is whitespace to `isspace()`, so each token column already refuses it."""
    assert ch.isspace()
    for field in ("kind", "outcome", "mechanism"):
        with pytest.raises(MalformedEntryError):
            line(_entry(**{field: f"a{ch}b"}), _STAMP)
    with pytest.raises(MalformedEntryError):
        line(_entry(symbol=f"W1{ch}"), _STAMP)


def test_tab_and_unicode_round_trip() -> None:
    """A note with a tab and unicode text but no boundary is accepted and parses back."""
    entry = _entry(note="tab\there → café ok", evidence="e\tv")
    parsed = parse(line(entry, _STAMP))
    assert isinstance(parsed, Parsed)
    assert parsed.entry == entry


def test_trailing_backslash_round_trips() -> None:
    """A note ending in a backslash still round-trips."""
    entry = _entry(note="ends with \\")
    parsed = parse(line(entry, _STAMP))
    assert isinstance(parsed, Parsed)
    assert parsed.entry == entry

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.witness.raw_bib`: substrate's `raw_bib_selftest` arms, ported."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.witness import raw_bib

if TYPE_CHECKING:
    from pathlib import Path

# A bib carrying a field the engine's whitelist drops, and an edge field it accepts.
_ONE = """@misc{ALPHA,
  section  = {s},
  claim    = {a claim},
  enables  = {BETA},
  check    = {item:ALPHA}
}

@misc{BETA,
  section  = {s},
  claim    = {another claim},
  rests-on = {ALPHA},
  check    = {item:BETA}
}
"""

# A second bib re-declaring one of the first's keys.
_TWO = """@misc{BETA,
  section = {s},
  claim   = {a REDECLARED claim},
  check   = {item:BETA}
}
"""

_ENTRY_COUNT = 2


def _bib(tmp_path: Path, name: str, text: str) -> Path:
    """Write a fixture bib.

    Returns:
        its path.

    """
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_every_entry_is_read(tmp_path: Path) -> None:
    """Both records parse."""
    assert len(raw_bib.read(_bib(tmp_path, "one.bib", _ONE)).entries) == _ENTRY_COUNT


def test_a_field_the_engine_drops_is_still_visible(tmp_path: Path) -> None:
    """The reader keeps a field the engine's whitelist would discard.

    ⚑ The whole point: a reader filtered to the engine's vocabulary would answer "no entries carry
    a dropped field" by construction, a green verdict about its own blindness.
    """
    assert "enables" in raw_bib.read(_bib(tmp_path, "one.bib", _ONE)).entries["ALPHA"]


def test_a_dropped_edge_is_reported_against_the_accepted_set(tmp_path: Path) -> None:
    """The join names the entries whose edges the engine will not render."""
    corpus = raw_bib.read(_bib(tmp_path, "one.bib", _ONE))
    assert raw_bib.entries_with_dropped_edges(corpus, frozenset({"rests-on"})) == ("ALPHA",)


def test_widening_the_accepted_set_empties_the_join(tmp_path: Path) -> None:
    """An accepted edge is not reported: the join's positive control.

    ⚑ Without it, a join reporting every entry would pass the case above.
    """
    corpus = raw_bib.read(_bib(tmp_path, "one.bib", _ONE))
    accepted = frozenset({"rests-on", "enables"})
    assert raw_bib.entries_with_dropped_edges(corpus, accepted) == ()


def test_a_redeclared_key_is_a_reported_collision(tmp_path: Path) -> None:
    """Composing two bibs reports the duplicate, and the later declaration wins.

    ⚑⚑ The measured defect: a plain merge loses the earlier declaration with no signal, which is
    how 84 records reported as 77.
    """
    got = raw_bib.read([_bib(tmp_path, "one.bib", _ONE), _bib(tmp_path, "two.bib", _TWO)])
    assert [c.key for c in got.collisions] == ["BETA"]
    assert got.entries["BETA"]["claim"] == "a REDECLARED claim"


def test_the_collision_is_not_an_entry(tmp_path: Path) -> None:
    """The collision record does not appear in the entry map.

    ⚑ A first cut stored it under a reserved key, a PHANTOM ENTRY inflating the very count being
    corrected.
    """
    got = raw_bib.read([_bib(tmp_path, "one.bib", _ONE), _bib(tmp_path, "two.bib", _TWO)])
    assert len(got.entries) == _ENTRY_COUNT


def test_an_absent_bib_says_absent(tmp_path: Path) -> None:
    """A missing file raises with ABSENT named."""
    with pytest.raises(raw_bib.BibError, match="ABSENT"):
        raw_bib.read_text(tmp_path / "no-such.bib")


def test_a_directory_is_not_an_absence(tmp_path: Path) -> None:
    """A directory raises distinctly from a missing file: one line for three facts is the defect."""
    with pytest.raises(raw_bib.BibError, match="DIRECTORY"):
        raw_bib.read_text(tmp_path)


def test_a_mangled_bib_is_broken_not_empty(tmp_path: Path) -> None:
    """Invalid UTF-8 raises rather than decoding into fiction.

    ⚑⚑ The worst direction: replacement characters parse into plausible entries that corroborate
    themselves, where a missing row would at least move a denominator.
    """
    path = tmp_path / "bad.bib"
    path.write_bytes(b"@misc{X,\n  claim = {\xff\xfe}\n}\n")
    with pytest.raises(raw_bib.BibError, match="BROKEN"):
        raw_bib.read_text(path)

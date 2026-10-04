# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_bibkeys`: keys are read through `raw_bib`.

⚑⚑⚑ THE THIRD OUTCOME IS THE POINT: an UNREADABLE read is `None`, never `set()`, and the other
direction holds too — a directory with no bibs is genuinely empty, because nothing ran to fail.

⚑ THE FIXTURES ARE `.bib` FILES THIS SUITE WRITES under `tmp_path`, with stray non-entry rows (a
denominator line and a flag line) beside the entries, so the non-key rows are cased without any
real ledger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ledger import finding_bibkeys

if TYPE_CHECKING:
    from pathlib import Path

_ENTRY = "@misc{{{key},\n  title = {{t}},\n}}\n"


def _ledgers(tmp_path: Path) -> Path:
    """Make a ledger directory: two readable bibs and two non-bib siblings.

    Returns:
        the directory.

    """
    where = tmp_path / "agents"
    where.mkdir()
    noise = "entries: 2 over the given bibs\n⚑ one entry carries a dropped field\n\n"
    (where / "zeta.bib").write_text(noise + _ENTRY.format(key="tmi-F6-ground-truth"), "utf-8")
    (where / "alpha.bib").write_text(_ENTRY.format(key="gate-G57-a-first-unit"), "utf-8")
    (where / "notes.md").write_text("", encoding="utf-8")
    (where / "script.py").write_text("", encoding="utf-8")
    return where


def test_no_bibs_is_empty_not_unreadable(tmp_path: Path) -> None:
    """A directory with no bibs, and an absent one, are EMPTY — nothing ran, so nothing failed."""
    assert finding_bibkeys.bib_keys(tmp_path) == (set(), [])
    assert finding_bibkeys.bib_keys(tmp_path / "not-a-directory") == (set(), [])


def test_the_listing_is_bib_only_and_sorted(tmp_path: Path) -> None:
    """Only `.bib` files are listed, sorted rather than in filesystem order."""
    names = [p.name for p in finding_bibkeys.ledger_bibs(_ledgers(tmp_path))]
    assert names == ["alpha.bib", "zeta.bib"]


def test_the_keys_are_read_through_raw_bib_and_the_non_key_rows_are_not(tmp_path: Path) -> None:
    """Each entry's key is read; a denominator row and a flag row are never interned as keys."""
    keys, bibs = finding_bibkeys.bib_keys(_ledgers(tmp_path))
    assert keys == {"gate-G57-a-first-unit", "tmi-F6-ground-truth"}
    assert [p.name for p in bibs] == ["alpha.bib", "zeta.bib"]


def test_a_directory_named_like_a_bib_is_unreadable_never_empty(tmp_path: Path) -> None:
    """A `.bib` that is a directory yields `None`: THE THIRD OUTCOME, never `set()`."""
    where = _ledgers(tmp_path)
    (where / "broken.bib").mkdir()
    keys, bibs = finding_bibkeys.bib_keys(where)
    assert keys is None
    assert bibs


def test_a_bib_that_is_not_utf8_is_unreadable(tmp_path: Path) -> None:
    """A bib that cannot be decoded is BROKEN, which is unreadable — not empty, not a crash."""
    where = _ledgers(tmp_path)
    (where / "mangled.bib").write_bytes(b"\xff\xfe\x00@misc{k,")
    keys, _ = finding_bibkeys.bib_keys(where)
    assert keys is None

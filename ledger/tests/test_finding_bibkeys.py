# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_bibkeys`: substrate's suite, with the lister supplied.

⚑⚑⚑ THE THIRD OUTCOME IS THE POINT: an UNREADABLE read is `None`, never `set()`, and the other
direction holds too — a directory with no bibs is genuinely empty, because nothing ran to fail.

⚑ THE LISTER IS A SCRIPT THIS SUITE WRITES, emitting the hazardous rows a real one leads with (a
denominator and a ⚑ warning), so the non-key rows are cased without any real bib tool.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.ledger import finding_bibkeys

if TYPE_CHECKING:
    from pathlib import Path

_KEYS = ("gate-G57-a-first-unit", "tmi-F6-ground-truth")


def _lister(tmp_path: Path, *, code: int = 0) -> list[str]:
    """Write a lister that records its argv and prints a denominator, a warning, and `_KEYS`.

    Returns:
        the argv to run it.

    """
    script = tmp_path / "lister.py"
    rows = ["entries: 2 over the given bibs", "⚑ one entry carries a dropped field"]
    rows += [f"{key} @misc title" for key in _KEYS]
    script.write_text(
        "import pathlib, sys\n"
        f"pathlib.Path({str(tmp_path / 'argv')!r}).write_text('\\n'.join(sys.argv[1:]))\n"
        f"print({chr(10).join(rows)!r})\n"
        f"sys.exit({code})\n",
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


def _ledgers(tmp_path: Path) -> Path:
    """Make a ledger directory holding two bibs and two non-bib siblings.

    Returns:
        the directory.

    """
    where = tmp_path / "agents"
    where.mkdir()
    for name in ("zeta.bib", "alpha.bib", "notes.md", "script.py"):
        (where / name).write_text("", encoding="utf-8")
    return where


def test_no_bibs_is_empty_not_unreadable(tmp_path: Path) -> None:
    """A directory with no bibs, and an absent one, are EMPTY — nothing ran, so nothing failed."""
    lister = _lister(tmp_path)
    assert finding_bibkeys.bib_keys(tmp_path, lister=lister, cwd=tmp_path) == (set(), [])
    missing = tmp_path / "not-a-directory"
    assert finding_bibkeys.bib_keys(missing, lister=lister, cwd=tmp_path) == (set(), [])
    assert not (tmp_path / "argv").exists()


def test_the_listing_is_bib_only_and_sorted(tmp_path: Path) -> None:
    """Only `.bib` files are listed, sorted rather than in filesystem order."""
    names = [p.name for p in finding_bibkeys.ledger_bibs(_ledgers(tmp_path))]
    assert names == ["alpha.bib", "zeta.bib"]


def test_the_keys_are_read_and_the_non_key_rows_are_not(tmp_path: Path) -> None:
    """The lister's keys are read; its denominator and warning rows are never interned as keys."""
    keys, bibs = finding_bibkeys.bib_keys(
        _ledgers(tmp_path), lister=_lister(tmp_path), cwd=tmp_path
    )
    assert keys == set(_KEYS)
    assert [p.name for p in bibs] == ["alpha.bib", "zeta.bib"]


def test_the_lister_is_handed_every_bib_in_order(tmp_path: Path) -> None:
    """The bib paths are appended to the caller's lister argv, in the sorted read order."""
    where = _ledgers(tmp_path)
    finding_bibkeys.bib_keys(where, lister=_lister(tmp_path), cwd=tmp_path)
    handed = (tmp_path / "argv").read_text(encoding="utf-8").splitlines()
    assert handed == [str(where / "alpha.bib"), str(where / "zeta.bib")]


def test_a_failing_lister_is_unreadable_never_empty(tmp_path: Path) -> None:
    """A lister exiting non-zero yields `None`: THE THIRD OUTCOME, never smoothed into `set()`."""
    keys, bibs = finding_bibkeys.bib_keys(
        _ledgers(tmp_path), lister=_lister(tmp_path, code=1), cwd=tmp_path
    )
    assert keys is None
    assert bibs


def test_a_lister_that_never_started_is_unreadable(tmp_path: Path) -> None:
    """A lister that does not exist never ran, which is unreadable — not empty, not a crash."""
    absent = [str(tmp_path / "no-such-bib-tool")]
    keys, _ = finding_bibkeys.bib_keys(_ledgers(tmp_path), lister=absent, cwd=tmp_path)
    assert keys is None

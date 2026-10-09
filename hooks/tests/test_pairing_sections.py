# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pairing check's section agreement: warrant sections against rubric rows."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_COUNTER = Path(__file__).parent.parent.parent / "count_test_functions.py"
_CHECK = "python -m pytest tests/test_m.py -k test_a"
_TEST = "def test_a() -> None:\n    pass\n"


def _bib(*sections: str, claim: str = "c") -> str:
    """Write a ledger whose single test is warranted once per section given.

    Returns:
        the bib text; each entry names the same test, so only the sections differ.

    """
    return "".join(
        f"\n@misc{{d-{n},\n  section = {{{s}}},\n  claim = {{{claim}}},\n"
        f"  check = {{{_CHECK}}},\n}}\n"
        for n, s in enumerate(sections)
    )


def _dist(root: Path, bib: str, rubric: str | None, name: str = "rubric.tsv") -> Path:
    """Build a distribution holding one test, a ledger and an optional rubric.

    Returns:
        the distribution directory.

    """
    dist = root / "d"
    (dist / "tests").mkdir(parents=True)
    (dist / "tests" / "test_m.py").write_text(_TEST, encoding="utf-8")
    (dist / "warrants.bib").write_text(bib, encoding="utf-8")
    if rubric is not None:
        (dist / name).write_text(rubric, encoding="utf-8")
    return dist


def _pairing(dist: Path) -> subprocess.CompletedProcess[str]:
    """Run the counter's pairing mode over one distribution.

    Returns:
        the completed process.

    """
    return subprocess.run(
        [sys.executable, str(_COUNTER), "--pairing", str(dist)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_rubric_that_agrees_with_the_warrants_is_clean(tmp_path: Path) -> None:
    """Every warrant section has a titled row and every row has a warrant: no finding."""
    dist = _dist(tmp_path, _bib("a"), "# a comment\na\tThe A Section\n\n")
    done = _pairing(dist)
    assert done.returncode == 0
    assert "0 finding(s)" in done.stdout


def test_a_section_with_no_rubric_row_is_named(tmp_path: Path) -> None:
    """A warrant filed under a section the rubric does not list is refused by name."""
    done = _pairing(_dist(tmp_path, _bib("a", "b"), "a\tThe A Section\n"))
    assert done.returncode == 1
    assert "SECTION WITHOUT RUBRIC ROW b" in done.stdout


def test_a_rubric_row_with_no_warrant_is_named(tmp_path: Path) -> None:
    """A heading nothing is filed under is refused by name."""
    done = _pairing(_dist(tmp_path, _bib("a"), "a\tThe A Section\nz\tNo warrant here\n"))
    assert done.returncode == 1
    assert "RUBRIC ROW WITHOUT WARRANT z" in done.stdout


@pytest.mark.parametrize("row", ["aThe A Section\n", "a\t\n", "a\n"])
def test_a_row_that_lost_its_tab_or_title_is_named(tmp_path: Path, row: str) -> None:
    """An edit tool that drops a trailing TAB welds key and title, or leaves no title at all."""
    done = _pairing(_dist(tmp_path, _bib("a"), row))
    assert done.returncode == 1
    assert "RUBRIC ROW WITHOUT TITLE" in done.stdout


def test_a_section_quoted_inside_a_claim_is_prose_not_a_section(tmp_path: Path) -> None:
    """The gate's old grep read a section field anywhere; an entry's own field is the only one."""
    bib = _bib("a", claim="the field reads section = {ghost} in the old tool")
    done = _pairing(_dist(tmp_path, bib, "a\tThe A Section\n"))
    assert done.returncode == 0
    assert "ghost" not in done.stdout


def test_a_distribution_without_a_rubric_has_no_section_findings(tmp_path: Path) -> None:
    """The root and atoms carry a ledger and no rubric; their pairing is unchanged."""
    done = _pairing(_dist(tmp_path, _bib("a"), None))
    assert done.returncode == 0


def test_a_jsonl_rubric_is_read_the_same_way(tmp_path: Path) -> None:
    """The structured rubric is the format that is arriving; its keys and titles are compared."""
    good = '{"key": "a", "title": "The A Section"}\n'
    assert _pairing(_dist(tmp_path / "ok", _bib("a"), good, "rubric.jsonl")).returncode == 0
    bad = '{"key": "a", "title": ""}\n{"key": "b", "title": "B"}\nnot json\n'
    done = _pairing(_dist(tmp_path / "bad", _bib("a"), bad, "rubric.jsonl"))
    assert done.returncode == 1
    assert "RUBRIC ROW WITHOUT TITLE a" in done.stdout
    assert "RUBRIC ROW WITHOUT WARRANT b" in done.stdout

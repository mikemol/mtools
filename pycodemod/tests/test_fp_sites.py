# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The fingerprint site walk: a control site carries the referents of its governing expression."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.census_fp import Census, FpSite, modelled_keys
from mikemol.pycodemod.control_roster import PYTHON_BOUNDARY
from mikemol.pycodemod.fp_sites import fp_sites
from mikemol.pycodemod.storeflow import StoreVocab

if TYPE_CHECKING:
    from pathlib import Path

_VOCAB = StoreVocab(
    readers=frozenset({"execute", "fetchall"}),
    receivers=frozenset({"con"}),
    connections=frozenset({"con"}),
)
_FIXTURE = (
    "def f(rows, lim):\n"
    "    for r in rows:\n"
    "        if r['core_id'] and lim:\n"
    "            return r\n"
)
_LINE_FOR = 2
_LINE_IF = 3
_LINE_FIRST_IF = 2
_LINE_SECOND_IF = 4


def _write(tmp_path: Path, src: str, name: str = "case.py") -> str:
    target = tmp_path / name
    target.write_text(src, encoding="utf-8")
    return str(target)


def _refs(sites: list[FpSite], line: int, construct: str) -> frozenset[str]:
    return next(s.refs for s in sites if s.line == line and s.construct == construct)


def test_a_for_site_carries_its_iterable_as_a_referent(tmp_path: Path) -> None:
    """The `for` site's governing expression is its iterable."""
    sites = fp_sites([_write(tmp_path, _FIXTURE)], _VOCAB, PYTHON_BOUNDARY).sites
    assert "rows" in _refs(sites, _LINE_FOR, "for")


def test_an_if_site_carries_the_column_string_as_a_referent(tmp_path: Path) -> None:
    """An identifier-shaped string in the test is a referent."""
    sites = fp_sites([_write(tmp_path, _FIXTURE)], _VOCAB, PYTHON_BOUNDARY).sites
    assert "core_id" in _refs(sites, _LINE_IF, "if")


def test_the_if_site_also_carries_its_bound_names(tmp_path: Path) -> None:
    """The names the test reads join the referents."""
    sites = fp_sites([_write(tmp_path, _FIXTURE)], _VOCAB, PYTHON_BOUNDARY).sites
    assert {"r", "lim"} <= _refs(sites, _LINE_IF, "if")


def test_authored_an_empty_governing_expression_gives_empty_refs(tmp_path: Path) -> None:
    """AUTHORED: a `break` under no `if` has no governing node, so its refs are empty."""
    src = "def g(xs):\n    for x in xs:\n        break\n"
    sites = fp_sites([_write(tmp_path, src)], _VOCAB, PYTHON_BOUNDARY).sites
    brk = [s for s in sites if s.construct == "break"]
    assert [s.refs for s in brk] == [frozenset()]


def test_authored_a_skipped_file_is_returned_not_dropped(tmp_path: Path) -> None:
    """AUTHORED: an unparseable file lands in `skipped` while a good file still yields sites."""
    bad = _write(tmp_path, "def (:\n", "bad.py")
    good = _write(tmp_path, _FIXTURE, "good.py")
    result = fp_sites([bad, good], _VOCAB, PYTHON_BOUNDARY)
    assert [s.path for s in result.skipped] == [bad]
    assert {s.path for s in result.sites} == {good}


def test_authored_fpsite_refs_for_a_comparison_and_an_attribute(tmp_path: Path) -> None:
    """AUTHORED: `sym == "x"` gives sym and x; an attribute gives its root and its member."""
    src = (
        "def h(sym, obj):\n"
        "    if sym == 'x':\n"
        "        return 1\n"
        "    if obj.member:\n"
        "        return 2\n"
        "    return 3\n"
    )
    sites = fp_sites([_write(tmp_path, src)], _VOCAB, PYTHON_BOUNDARY).sites
    assert _refs(sites, _LINE_FOR, "if") == {"sym", "x"}
    assert _refs(sites, _LINE_SECOND_IF, "if") == {"obj", "member"}


def test_authored_a_census_from_fp_sites_lowers_its_remainder_with_a_wider_seed(
    tmp_path: Path,
) -> None:
    """AUTHORED: real control sites feed `Census`; a wider seed lowers Omega and bits."""
    sites = fp_sites([_write(tmp_path, _FIXTURE)], _VOCAB, PYTHON_BOUNDARY).sites
    narrow_seed = _write(tmp_path, 'T = "core_id"\n', "seed_a.py")
    wide_seed = _write(tmp_path, 'T = "core_id"\nU = "rows"\nV = "lim"\n', "seed_b.py")
    narrow = Census(sites, modelled_keys([narrow_seed]).keys)
    wide = Census(sites, modelled_keys([wide_seed]).keys)
    assert wide.total_remainder_omega() < narrow.total_remainder_omega()
    assert wide.total_remainder_bits() < narrow.total_remainder_bits()
    assert wide.explained_sites() >= narrow.explained_sites()
    assert all(n.rem % w.rem == 0 for n, w in zip(narrow.rows, wide.rows, strict=True))

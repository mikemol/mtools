# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `edges`: per-claim rests_on/check, and the duplicate-key refusal."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.bibparse.bibparse import BibSyntaxError
from mikemol.bibparse.edges import (
    ClaimEdges,
    DuplicateKeyError,
    claim_edges,
    collect,
    edges_of,
    split_list,
)

if TYPE_CHECKING:
    from pathlib import Path


def _bib(path: Path, text: str) -> Path:
    """Write `text` to `path`.

    Returns:
        `path`.

    """
    path.write_text(text, encoding="utf-8")
    return path


def test_split_list_splits_on_commas_and_whitespace_and_drops_empties() -> None:
    """Commas, spaces, tabs and newlines all separate; stray separators leave no empties."""
    assert split_list("a, b\tc\n d,,e ,") == ["a", "b", "c", "d", "e"]
    assert split_list(" ,\n") == []
    assert split_list("") == []


def test_edges_carry_rests_on_and_check_per_claim(tmp_path: Path) -> None:
    """The shape effective.py consumes, with absent fields defaulting to empty."""
    bib = _bib(
        tmp_path / "w.bib",
        "@misc{a,\n  rests-on = {b, c\n    d},\n  check = {concept:X},\n}\n"
        "@misc{b, claim = {no edges here}}\n",
    )
    expected: dict[str, ClaimEdges] = {
        "a": {"rests_on": ["b", "c", "d"], "check": "concept:X"},
        "b": {"rests_on": [], "check": ""},
    }
    assert edges_of([bib]) == expected


def test_a_column_zero_brace_does_not_drop_the_edges(tmp_path: Path) -> None:
    """The truncation defect, end to end: the entry keeps its rests-on and check."""
    bib = _bib(
        tmp_path / "w.bib",
        "@misc{a,\n  claim = {text {braced\n}\n  more},\n  rests-on = {b},\n  check = {c:1},\n}\n",
    )
    assert edges_of([bib]) == {"a": {"rests_on": ["b"], "check": "c:1"}}


def test_collect_merges_bibs_in_order_and_keeps_the_entries(tmp_path: Path) -> None:
    """Keys from several files compose into one flat map, first file first."""
    one = _bib(tmp_path / "one.bib", "@misc{x, claim = {1}}")
    two = _bib(tmp_path / "two.bib", "@book{y, claim = {2}}")
    merged = collect([one, two])
    assert list(merged) == ["x", "y"]
    assert merged["y"].typ == "book"
    assert merged["x"].fields == {"claim": "1"}


def test_a_key_defined_in_two_bibs_is_refused_naming_both_places(tmp_path: Path) -> None:
    """The second definition never wins silently: the refusal names the key and both lines."""
    one = _bib(tmp_path / "one.bib", "@misc{k, check = {cmd:a}}")
    two = _bib(tmp_path / "two.bib", "\n@misc{k, claim = {later}}")
    with pytest.raises(DuplicateKeyError) as caught:
        collect([one, two])
    message = str(caught.value)
    assert "'k'" in message
    assert f"{one}:1" in message
    assert f"{two}:2" in message


def test_a_key_repeated_inside_one_bib_is_refused(tmp_path: Path) -> None:
    """A repeat in a single file refuses as well; paperkit let the later one win."""
    bib = _bib(tmp_path / "w.bib", "@misc{k, a = {1}}\n@misc{k, a = {2}}")
    with pytest.raises(DuplicateKeyError, match="TWICE"):
        edges_of([bib])


def test_a_malformed_bib_raises_its_syntax_error(tmp_path: Path) -> None:
    """A broken file is not a result: the parser's error propagates."""
    bib = _bib(tmp_path / "w.bib", "@misc{k, a = {never closes")
    with pytest.raises(BibSyntaxError, match="unterminated value"):
        edges_of([bib])


def test_claim_edges_resolves_a_planted_project(tmp_path: Path) -> None:
    """From a project directory to edges: paper.toml names two bibs, both are read."""
    (tmp_path / "paper.toml").write_text(
        '[paper]\nwarrants = ["main.bib", "//lib:more.bib"]\n',
        encoding="utf-8",
    )
    (tmp_path / "lib").mkdir()
    _bib(tmp_path / "main.bib", "@misc{a, rests-on = {z}, check = {cmd:true}}")
    _bib(tmp_path / "lib" / "more.bib", "@misc{z, check = {concept:Q}}")
    assert claim_edges(tmp_path) == {
        "a": {"rests_on": ["z"], "check": "cmd:true"},
        "z": {"rests_on": [], "check": "concept:Q"},
    }


def test_claim_edges_refuses_a_duplicate_across_the_projects_bibs(tmp_path: Path) -> None:
    """The refusal reaches the project-level entry point."""
    (tmp_path / "paper.toml").write_text(
        '[paper]\nwarrants = ["a.bib", "b.bib"]\n',
        encoding="utf-8",
    )
    _bib(tmp_path / "a.bib", "@misc{k, check = {cmd:a}}")
    _bib(tmp_path / "b.bib", "@misc{k, check = {cmd:b}}")
    with pytest.raises(DuplicateKeyError, match="'k'"):
        claim_edges(tmp_path)

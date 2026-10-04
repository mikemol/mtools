# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `census`: EMPTY apart from ABSENT over a corpus, and the matcher asymmetry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygit2

from mikemol.treeio import census as census_module
from mikemol.treeio.census import Census, census, compare, control_of
from mikemol.treeio.presence import Presence
from mikemol.treeio.result import Result
from mikemol.treeio.sources import Rev, WorkingTree

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.treeio.sources import Source

_FILES = {
    "d/top.agda": b"x",
    "d/sub/mid.agda": b"x",
    "d/sub/deep/low.agda": b"x",
    "d/sub/other.txt": b"x",
}


def _tree(repo: pygit2.Repository, files: dict[str, bytes]) -> pygit2.Oid:
    """Build the tree object for a mapping of slash-separated paths to bytes.

    Returns:
        The id of the written tree.

    """
    builder = repo.TreeBuilder()
    nested: dict[str, dict[str, bytes]] = {}
    for rel, data in files.items():
        head, sep, rest = rel.partition("/")
        if sep:
            nested.setdefault(head, {})[rest] = data
        else:
            builder.insert(head, repo.create_blob(data), pygit2.enums.FileMode.BLOB)
    for name, sub in nested.items():
        builder.insert(name, _tree(repo, sub), pygit2.enums.FileMode.TREE)
    return builder.write()


def _corpus(root: Path) -> None:
    """Commit the corpus and also lay it out on disk, so both sources hold the same files."""
    repo = pygit2.init_repository(str(root), initial_head="main")
    who = pygit2.Signature("t", "t@t")
    repo.create_commit("HEAD", who, who, "t", _tree(repo, _FILES), [])
    for rel, data in _FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)


def test_a_census_separates_empty_from_nonempty_and_counts_the_total(tmp_path: Path) -> None:
    """The empty file is counted once and named; the total is the sum of the four cells."""
    (tmp_path / "has.txt").write_bytes(b"hello")
    (tmp_path / "empty.txt").write_bytes(b"")
    (tmp_path / "also.txt").write_bytes(b"x")
    got = census("*.txt", WorkingTree(tmp_path))
    assert (got.nonempty, got.empty, got.absent, got.broken) == (2, 1, 0, 0)
    assert got.empty_paths == ["empty.txt"]
    assert got.total == got.nonempty + got.empty + got.absent + got.broken
    assert got.total == len(["has.txt", "empty.txt", "also.txt"])


def test_a_census_with_no_empty_member_reports_zero_in_that_cell(tmp_path: Path) -> None:
    """The all-clear differs from the found-something above: it is shown to report zero."""
    (tmp_path / "uni.agda").write_bytes(b"x")
    got = census("uni.agda", WorkingTree(tmp_path))
    assert (got.empty, got.nonempty, got.total) == (0, 1, 1)
    assert got.empty_paths == []


def test_a_census_names_the_broken_members_with_their_cause(tmp_path: Path) -> None:
    """A directory that a glob matched is BROKEN, and the census says which and why."""
    (tmp_path / "a.txt").mkdir()
    (tmp_path / "b.txt").write_bytes(b"x")
    got = census("*.txt", WorkingTree(tmp_path))
    assert (got.broken, got.nonempty, got.total) == (1, 1, 2)
    assert [p for p, _ in got.broken_paths] == ["a.txt"]
    assert isinstance(got.broken_paths[0][1], IsADirectoryError)


def test_a_census_counts_a_path_that_vanished_as_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path listed and then gone before the read is ABSENT, counted and not named."""
    (tmp_path / "a.txt").write_bytes(b"x")

    def gone(path: str | Path, source: Source | None = None) -> Result:
        """Report every path as vanished.

        Returns:
            An ABSENT result for the path.

        """
        return Result(Presence.ABSENT, path=path, source=source)

    monkeypatch.setattr(census_module, "read", gone)
    got = census("*.txt", WorkingTree(tmp_path))
    assert (got.absent, got.nonempty, got.empty, got.total) == (1, 0, 0, 1)


def test_a_census_honours_the_suffix_filter(tmp_path: Path) -> None:
    """A suffix selects within a depth-agnostic listing; no glob can express it."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "uni.agda").write_bytes(b"x")
    (tmp_path / "sub" / "Deep.agda").write_bytes(b"x")
    (tmp_path / "note.txt").write_bytes(b"x")
    got = census("**", WorkingTree(tmp_path), ".agda")
    assert (got.nonempty, got.total) == (2, 2)


def test_a_census_reads_a_revision(tmp_path: Path) -> None:
    """The census takes any source: at a revision it counts the committed blobs."""
    _corpus(tmp_path)
    got = census("d/**", Rev("HEAD", tmp_path), ".agda")
    assert (got.nonempty, got.empty, got.total) == (3, 0, 3)


def test_the_census_is_a_frozen_record() -> None:
    """The cells are values: two censuses with the same cells are equal."""
    cells = Census(1, 0, 0, 0, 1, [], [])
    assert cells == Census(1, 0, 0, 0, 1, [], [])
    assert cells != Census(2, 0, 0, 0, 2, [], [])


def test_the_control_is_the_wildcard_free_prefix_plus_a_double_star() -> None:
    """The control is derived from the segments, so a pattern with no double star gets one."""
    assert control_of("d/**/*.agda") == "d/**"
    assert control_of("d/*.agda") == "d/**"
    assert control_of("x/[ab]/y") == "x/**"
    assert control_of("d/e/f") == "d/e/f/**"
    assert control_of("*.txt") == "./**"
    assert control_of("**") == "./**"


def test_compare_measures_each_matcher_against_the_control(tmp_path: Path) -> None:
    """The star form drops the nested members on disk and keeps every depth at a revision."""
    _corpus(tmp_path)
    got = compare("d/*.agda", "HEAD", ".agda", tmp_path)
    assert (got.pattern, got.control, got.rev) == ("d/*.agda", "d/**", "HEAD")
    assert (got.wt.n, got.wt.control_n) == (1, 3)
    assert got.wt.missed == ["d/sub/deep/low.agda", "d/sub/mid.agda"]
    assert got.wt.extra == []
    assert (got.head.n, got.head.control_n) == (3, 3)
    assert got.head.missed == []
    assert got.head.extra == []


def test_compare_on_the_agreeing_form_reports_no_asymmetry(tmp_path: Path) -> None:
    """The depth-agnostic pattern is its own control, so neither side misses or adds anything."""
    _corpus(tmp_path)
    got = compare("d/**", "HEAD", ".agda", tmp_path)
    assert got.wt.missed == got.wt.extra == got.head.missed == got.head.extra == []
    assert got.wt.n == got.head.n == got.wt.control_n


def test_compare_defaults_to_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a root both sources look where the process is standing."""
    _corpus(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert compare("d/**", "HEAD", ".agda").head.n == len(["top", "mid", "low"])

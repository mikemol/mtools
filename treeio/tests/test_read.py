# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `read`: PRESENT, ABSENT and BROKEN from a working tree and from a revision."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pygit2
import pytest

from mikemol.treeio.presence import Presence
from mikemol.treeio.read import read, read_text, relpath
from mikemol.treeio.sources import Rev, WorkingTree

if TYPE_CHECKING:
    from pathlib import Path


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


def _commit(root: Path, files: dict[str, bytes]) -> None:
    """Make `root` a git repository whose only commit holds `files`."""
    repo = pygit2.init_repository(str(root), initial_head="main")
    who = pygit2.Signature("t", "t@t")
    repo.create_commit("HEAD", who, who, "t", _tree(repo, files), [])


def test_relpath_leaves_a_relative_path_and_relativises_an_absolute_one(tmp_path: Path) -> None:
    """A tree is keyed by repository-relative paths, so an absolute one is made relative."""
    assert relpath("a/b.txt", tmp_path) == "a/b.txt"
    assert relpath(tmp_path / "a" / "b.txt", tmp_path) == "a/b.txt"
    assert relpath("/etc/passwd", tmp_path).endswith("etc/passwd")
    assert relpath("/etc/passwd", tmp_path).startswith("..")


def test_a_worktree_read_returns_raw_bytes_and_keeps_empty_apart_from_absent(
    tmp_path: Path,
) -> None:
    """An empty file is PRESENT with b'' and a missing file is ABSENT: the load-bearing pair."""
    (tmp_path / "has.txt").write_bytes(b"hello")
    (tmp_path / "empty.txt").write_bytes(b"")
    tree = WorkingTree(tmp_path)
    has = read("has.txt", tree)
    empty = read("empty.txt", tree)
    gone = read("gone.txt", tree)
    assert (has.presence, has.data) == (Presence.PRESENT, b"hello")
    assert (empty.presence, empty.data) == (Presence.PRESENT, b"")
    assert gone.presence is Presence.ABSENT
    assert isinstance(gone.error, FileNotFoundError)
    assert bool(empty)
    assert not gone
    assert has.path == "has.txt"
    assert has.source is tree


def test_a_directory_is_broken_not_absent_and_carries_its_cause(tmp_path: Path) -> None:
    """The path exists, so reporting ABSENT would tell the caller something false."""
    (tmp_path / "adir").mkdir()
    result = read("adir", WorkingTree(tmp_path))
    assert result.presence is Presence.BROKEN
    assert isinstance(result.error, IsADirectoryError)


def test_an_unreadable_file_is_broken_not_absent(tmp_path: Path) -> None:
    """A permission refusal did not read the file, so it is BROKEN with the OS error."""
    if os.getuid() == 0:
        pytest.skip("root reads past a zero mode")
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"x")
    secret.chmod(0)
    try:
        result = read("secret.txt", WorkingTree(tmp_path))
    finally:
        secret.chmod(0o644)
    assert result.presence is Presence.BROKEN
    assert isinstance(result.error, PermissionError)


def test_a_worktree_read_accepts_an_absolute_path(tmp_path: Path) -> None:
    """An absolute path is read where it points, not under the root."""
    other = tmp_path / "other"
    other.mkdir()
    (other / "x.txt").write_bytes(b"abs")
    result = read(other / "x.txt", WorkingTree(tmp_path / "root-elsewhere"))
    assert result.data == b"abs"


def test_the_default_source_is_the_working_tree_at_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no source the read happens where the process is standing."""
    (tmp_path / "here.txt").write_bytes(b"here")
    monkeypatch.chdir(tmp_path)
    result = read("here.txt")
    assert result.data == b"here"
    assert isinstance(result.source, WorkingTree)


def test_a_revision_read_returns_the_blob_bytes(tmp_path: Path) -> None:
    """A path present in the revision reads as raw bytes, including from a subdirectory."""
    _commit(tmp_path, {"a.txt": b"one", "d/b.txt": b"\xff two"})
    head = Rev("HEAD", tmp_path)
    assert read("a.txt", head).data == b"one"
    deep = read("d/b.txt", head)
    assert (deep.presence, deep.data, deep.source) == (Presence.PRESENT, b"\xff two", head)


def test_a_revision_read_accepts_an_absolute_path_under_the_root(tmp_path: Path) -> None:
    """An absolute path inside the repository is keyed relative to it."""
    _commit(tmp_path, {"a.txt": b"one"})
    assert read(tmp_path / "a.txt", Rev("HEAD", tmp_path)).data == b"one"


def test_a_missing_path_at_a_revision_is_absent(tmp_path: Path) -> None:
    """Once the revision is good, a lookup that fails means the path is not there."""
    _commit(tmp_path, {"a.txt": b"one"})
    result = read("no/such/file.xyz", Rev("HEAD", tmp_path))
    assert result.presence is Presence.ABSENT
    assert isinstance(result.error, KeyError)


def test_a_bad_revision_is_broken_and_differs_from_a_missing_path(tmp_path: Path) -> None:
    """The arm the inherited-split assumption would have got wrong: a typo is not ABSENT."""
    _commit(tmp_path, {"a.txt": b"one"})
    bad = read("a.txt", Rev("nosuchrev-zzz-9999", tmp_path))
    missing = read("zzz.txt", Rev("HEAD", tmp_path))
    assert bad.presence is Presence.BROKEN
    assert "bad revision" in str(bad.error)
    assert bad.presence != missing.presence


def test_a_directory_that_is_not_a_repository_is_broken_at_a_revision(tmp_path: Path) -> None:
    """With no repository there is no revision to read, and the cause says so."""
    result = read("x.txt", Rev("HEAD", tmp_path))
    assert result.presence is Presence.BROKEN
    assert "not a git repository" in str(result.error)


def test_a_tree_at_a_revision_is_broken_not_a_blob(tmp_path: Path) -> None:
    """A directory in the tree is not a blob, and the cause names what it is."""
    _commit(tmp_path, {"d/b.txt": b"x"})
    result = read("d", Rev("HEAD", tmp_path))
    assert result.presence is Presence.BROKEN
    assert isinstance(result.error, IsADirectoryError)
    assert str(result.error) == "d is a tree at HEAD"


def test_path_traversal_is_absent_at_a_revision_not_a_read(tmp_path: Path) -> None:
    """There is no filesystem path to escape from when reading out of a git tree."""
    _commit(tmp_path, {"a.txt": b"one"})
    head = Rev("HEAD", tmp_path)
    for spelling in ("../etc/passwd", "/etc/passwd", "d/../../etc/passwd"):
        assert read(spelling, head).presence is Presence.ABSENT


def test_require_keeps_absent_and_broken_apart_across_the_conversion(tmp_path: Path) -> None:
    """An except clause for FileNotFoundError catches a missing path and never a bad revision."""
    _commit(tmp_path, {"a.txt": b"one"})
    with pytest.raises(FileNotFoundError):
        read("zzz.txt", Rev("HEAD", tmp_path)).require()
    with pytest.raises(ValueError, match="bad revision"):
        read("a.txt", Rev("nosuchrev-zzz-9999", tmp_path)).require()


def test_read_text_decodes_present_files_and_keeps_empty_apart_from_none(
    tmp_path: Path,
) -> None:
    """An empty file reads as an empty string and a missing one as None."""
    (tmp_path / "t.txt").write_bytes("café".encode())
    (tmp_path / "empty.txt").write_bytes(b"")
    tree = WorkingTree(tmp_path)
    empty = read_text("empty.txt", tree)
    assert read_text("t.txt", tree) == "café"
    assert empty is not None
    assert len(empty) == 0
    assert read_text("gone.txt", tree) is None


def test_read_text_raises_on_broken_and_on_undecodable_bytes(tmp_path: Path) -> None:
    """BROKEN is never a silent miss, and a decode failure raises unless the caller relaxes it."""
    (tmp_path / "adir").mkdir()
    (tmp_path / "latin.bin").write_bytes(b"\xff\xfe not utf-8")
    tree = WorkingTree(tmp_path)
    with pytest.raises(IsADirectoryError):
        read_text("adir", tree)
    with pytest.raises(UnicodeDecodeError):
        read_text("latin.bin", tree)
    assert read_text("latin.bin", tree, errors="replace") == "�� not utf-8"
    assert read("latin.bin", tree).presence is Presence.PRESENT


def test_read_text_reads_a_revision_too(tmp_path: Path) -> None:
    """The text wrapper takes any source, and a bad revision raises rather than returning None."""
    _commit(tmp_path, {"a.txt": b"one"})
    assert read_text("a.txt", Rev("HEAD", tmp_path)) == "one"
    assert read_text("zzz.txt", Rev("HEAD", tmp_path)) is None
    with pytest.raises(ValueError, match="bad revision"):
        read_text("a.txt", Rev("nosuchrev-zzz-9999", tmp_path))

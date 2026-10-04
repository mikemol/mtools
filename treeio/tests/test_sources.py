# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `sources`: the working tree, and a revision resolved eagerly and separately."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygit2

from mikemol.treeio.sources import Rev, WorkingTree

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


def test_a_working_tree_is_writable_and_names_its_absolute_root(tmp_path: Path) -> None:
    """The working tree is the only writable source and its root is absolute."""
    tree = WorkingTree(tmp_path)
    assert tree.writable is True
    assert tree.root == tmp_path.absolute()
    assert WorkingTree("rel").root.is_absolute()


def test_a_working_tree_defaults_to_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a root the tree is wherever the process is standing."""
    monkeypatch.chdir(tmp_path)
    assert WorkingTree().root == tmp_path.resolve()


def test_a_working_tree_renders_its_root_and_its_plain_name(tmp_path: Path) -> None:
    """The repr carries the root for refusals; the string form is the phrase working tree."""
    assert repr(WorkingTree(tmp_path)) == f"WorkingTree({str(tmp_path)!r})"
    assert str(WorkingTree(tmp_path)) == "working tree"


def test_a_rev_is_read_only_and_defaults_to_head(tmp_path: Path) -> None:
    """History is not writable, and an unnamed revision means HEAD."""
    rev = Rev(root=tmp_path)
    assert rev.writable is False
    assert rev.rev == "HEAD"
    assert rev.root == tmp_path.absolute()


def test_a_rev_defaults_its_root_to_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a root the revision is looked up in the repository the process stands in."""
    monkeypatch.chdir(tmp_path)
    assert Rev("HEAD").root == tmp_path.resolve()


def test_a_rev_renders_its_spelling_and_its_plain_name() -> None:
    """The repr is a constructor; the string form is rev followed by the spelling."""
    assert repr(Rev("HEAD~3")) == "Rev('HEAD~3')"
    assert str(Rev("HEAD~3")) == "rev HEAD~3"


def test_a_good_revision_resolves_to_a_tree_and_no_error(tmp_path: Path) -> None:
    """The commit peels to its tree, which holds the committed blobs."""
    _commit(tmp_path, {"a.txt": b"one"})
    tree, err = Rev("HEAD", tmp_path).resolve()
    assert err is None
    assert tree is not None
    assert tree["a.txt"].id == pygit2.hash(b"one")


def test_resolution_is_cached_so_the_same_tree_comes_back(tmp_path: Path) -> None:
    """A second resolve returns the first tree object rather than opening the repository again."""
    _commit(tmp_path, {"a.txt": b"one"})
    rev = Rev("HEAD", tmp_path)
    first, _ = rev.resolve()
    second, _ = rev.resolve()
    assert first is second


def test_a_bad_revision_is_a_value_error_naming_it(tmp_path: Path) -> None:
    """A mistyped sha is BROKEN with its own message and never a missing path."""
    _commit(tmp_path, {"a.txt": b"one"})
    tree, err = Rev("nosuchrev-zzz-9999", tmp_path).resolve()
    assert tree is None
    assert isinstance(err, ValueError)
    assert "bad revision 'nosuchrev-zzz-9999'" in str(err)
    assert str(tmp_path) in str(err)


def test_a_bad_revision_error_is_cached(tmp_path: Path) -> None:
    """The failure is remembered: the second resolve hands back the same exception object."""
    _commit(tmp_path, {"a.txt": b"one"})
    rev = Rev("nosuchrev-zzz-9999", tmp_path)
    _, first = rev.resolve()
    _, second = rev.resolve()
    assert first is second


def test_a_directory_that_is_not_a_repository_is_a_runtime_error(tmp_path: Path) -> None:
    """No repository at the root is BROKEN and says so."""
    tree, err = Rev("HEAD", tmp_path).resolve()
    assert tree is None
    assert isinstance(err, RuntimeError)
    assert "not a git repository" in str(err)


def test_an_unparseable_spelling_is_a_runtime_error(tmp_path: Path) -> None:
    """A spelling pygit2 cannot parse is BROKEN with a cannot-resolve message."""
    _commit(tmp_path, {"a.txt": b"one"})
    tree, err = Rev("HEAD@{", tmp_path).resolve()
    assert tree is None
    assert isinstance(err, RuntimeError)
    assert "cannot resolve 'HEAD@{'" in str(err)


def test_a_revision_naming_a_blob_does_not_name_a_tree(tmp_path: Path) -> None:
    """A blob cannot be peeled to a tree, and the refusal says the revision names no tree."""
    _commit(tmp_path, {"a.txt": b"one"})
    tree, err = Rev("HEAD:a.txt", tmp_path).resolve()
    assert tree is None
    assert isinstance(err, ValueError)
    assert "does not name a tree" in str(err)

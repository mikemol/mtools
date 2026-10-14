# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a gate snapshot carries an in-tree link as a regular file and refuses the rest.

W1174. ⚑ NO SYMLINK IS EVER CREATED ON THE FILESYSTEM: the tracked links are written into the
index with `update-index --cacheinfo 120000`, so the operator's no-links ruling holds for the test
too. ⚑ THE REFUSED LINKS ARE THE CONTROLS: a link out of the tree, an absolute one, a dangling one,
a link to a link and a link to a directory must each stay absent, or "carry" has quietly become
"follow".
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import snaplinks, snapshot

if TYPE_CHECKING:
    from pathlib import Path

_LAUNCHER = "#!/bin/sh\necho launcher\n"
_EXECUTABLE = 0o755
_CARRIED = ("bin/alias", "bin/second")
_REFUSED = ("esc", "abs", "dangling", "chain", "dirlink")


def _git(root: Path, *args: str, stdin: str | None = None) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _link(root: Path, name: str, target: str) -> None:
    """Stage `name` as a tracked symlink to `target` without creating a link on disk."""
    sha = _git(root, "hash-object", "-w", "--stdin", stdin=target)
    _git(root, "update-index", "--add", "--cacheinfo", f"120000,{sha},{name}")


def _repo(tmp_path: Path) -> Path:
    """Build a repository whose index tracks one launcher and links of every kind to it.

    Returns:
        the repository's root.

    """
    root = tmp_path / "repo"
    (root / "bin").mkdir(parents=True)
    _git(root, "init", "-q")
    launcher = root / "bin" / "real"
    launcher.write_text(_LAUNCHER, encoding="utf-8")
    launcher.chmod(_EXECUTABLE)
    _git(root, "add", "-A")
    _link(root, "bin/alias", "real")
    _link(root, "bin/second", "./real")
    _link(root, "esc", "../sibling")
    _link(root, "abs", "/etc/hostname")
    _link(root, "dangling", "nowhere")
    _link(root, "chain", "bin/alias")
    _link(root, "dirlink", "bin")
    return root


def test_links_are_sorted_into_carried_and_refused(tmp_path: Path) -> None:
    """The two links to the launcher are carried; the five that cannot be are refused by name."""
    root = _repo(tmp_path)
    carried, refused = snaplinks.links(root, snapshot.tree_of(root, working=False))
    assert sorted(carried) == sorted(_CARRIED)
    assert all(link.target == "bin/real" for link in carried.values())
    assert sorted(refused) == sorted(_REFUSED)


def test_a_snapshot_writes_a_carried_link_as_a_regular_file_with_the_targets_bytes_and_mode(
    tmp_path: Path,
) -> None:
    """Not a link, the launcher's bytes, mode 755; every refused link is absent from the tree."""
    root = _repo(tmp_path)
    tree = snapshot.tree_of(root, working=False)
    with snapshot.Snapshot("repo", tmp_path / "space") as snap:
        snap.materialize(root, tree)
        for name in _CARRIED:
            made = snap.path / name
            assert made.is_file()
            assert not made.is_symlink()
            assert made.read_text(encoding="utf-8") == _LAUNCHER
            assert made.stat().st_mode & 0o777 == _EXECUTABLE
        for name in _REFUSED:
            assert not (snap.path / name).exists()
            assert not (snap.path / name).is_symlink()


def test_a_carried_file_that_went_missing_is_restored_on_the_next_materialize(
    tmp_path: Path,
) -> None:
    """The stamp matches but the file is gone: `_lost` must count a carried link as lost."""
    root = _repo(tmp_path)
    tree = snapshot.tree_of(root, working=False)
    with snapshot.Snapshot("repo", tmp_path / "space") as snap:
        snap.materialize(root, tree)
        (snap.path / "bin" / "alias").unlink()
        assert snap.materialize(root, tree) == ["bin/alias"]
        assert (snap.path / "bin" / "alias").is_file()


def test_a_link_added_by_a_later_tree_arrives_through_the_incremental_diff(
    tmp_path: Path,
) -> None:
    """Materialize the tree without the link, then the tree with it: the file appears, once."""
    root = _repo(tmp_path)
    _git(root, "update-index", "--force-remove", "bin/second")
    first = snapshot.tree_of(root, working=False)
    _link(root, "bin/second", "real")
    second = snapshot.tree_of(root, working=False)
    with snapshot.Snapshot("repo", tmp_path / "space") as snap:
        snap.materialize(root, first)
        assert not (snap.path / "bin" / "second").exists()
        assert "bin/second" in snap.materialize(root, second)
        assert (snap.path / "bin" / "second").read_text(encoding="utf-8") == _LAUNCHER

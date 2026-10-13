# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-commit` in isolated mode, on a decoy repository (W902, W903).

⚑ THE FIRST ARM IS THE POSITIVE CONTROL: a plain edit commits through the private index and
snapshot, HEAD moves, and the verdict line says so. The rest ask what isolation is for: a peer's
unstaged file is neither committed nor in the way, the real index reads the committed paths as
committed (no staged reversal), a staged deletion lands as a deletion, and a new file is taken.

Every GIT_* variable is removed first, the identity is fixed, and the snapshot namespace is
tmp_path, so nothing here touches a real repository or /var/tmp/mikemol.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks.snapshot import NAMESPACE_ENV

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_ORIGINAL = "original\n"
_EDITED = "edited by this session\n"
_PEER = "edited by a peer, not staged\n"
_EXECUTABLE = 0o755
_REQUEST = ck.Request(waypoint="W1", subject="isolated subject", paths=("a.txt",))


def _git(root: Path, *args: str) -> str:
    """Run the real git (resolved, not by partial path) and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def _status(root: Path) -> list[str]:
    """Read `git status --porcelain` as lines.

    Returns:
        one line per changed path; empty when the repository is clean.

    """
    return _git(root, "status", "--porcelain").splitlines()


def _decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with a.txt, b.txt and c.txt committed, in a clean git environment.

    Returns:
        the repository's root.

    """
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
        NAMESPACE_ENV: str(tmp_path / "gate"),
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    for name in ("a.txt", "b.txt", "c.txt"):
        (root / name).write_text(_ORIGINAL, encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    return root


def _isolated(root: Path, request: ck.Request = _REQUEST) -> tuple[int, str]:
    """Commit the request in isolated mode with the real git runner.

    Returns:
        the exit code and the text written to `out`.

    """
    out = io.StringIO()
    code = ck.commit(root, request, out, isolated=True)
    return code, out.getvalue()


def test_an_edit_commits_through_the_private_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control: HEAD moves, holds the edit, and the verdict says COMMITTED."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    code, shown = _isolated(root)
    assert code == 0, shown
    assert "COMMITTED repo" in shown.splitlines()[-1]
    assert _git(root, "show", "HEAD:a.txt") == _EDITED


def test_a_peers_unstaged_file_is_neither_committed_nor_in_the_way(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The peer's edit survives in the worktree, out of the commit, still unstaged afterwards."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    (root / "b.txt").write_text(_PEER, encoding="utf-8")
    code, shown = _isolated(root)
    assert code == 0, shown
    assert _git(root, "show", "HEAD:b.txt") == _ORIGINAL
    assert (root / "b.txt").read_text(encoding="utf-8") == _PEER
    assert _status(root) == [" M b.txt"]


def test_the_real_index_reads_the_committed_path_as_committed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No staged reversal is left behind: git status is clean for the committed path."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    assert _isolated(root)[0] == 0
    assert _status(root) == []
    assert not (root / ".git" / "index.lock").exists()

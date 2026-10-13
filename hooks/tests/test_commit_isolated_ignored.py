# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for isolated mode and ignored files: a named one is taken, a directory's are not.

Split out of `test_commit_isolated` (W1101): see `test_commit_isolated_hooks`. W1039's cases.
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


def _ignoring_dir(root: Path) -> None:
    """Make `vend/` ignore everything in it, as a wheels directory does (W1039)."""
    (root / "vend").mkdir()
    (root / "vend" / ".gitignore").write_text("*\n", encoding="utf-8")
    _git(root, "add", "-f", "vend/.gitignore")
    _git(root, "commit", "--quiet", "-m", "vend")


def test_an_ignored_file_named_exactly_is_committed_on_both_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W1039: a new, ignored file the caller names is theirs to add, isolated or plain."""
    root = _decoy(tmp_path, monkeypatch)
    _ignoring_dir(root)
    (root / "vend" / "new.whl").write_text(_EDITED, encoding="utf-8")
    request = ck.Request(waypoint="W1", subject="vend", paths=("vend/new.whl",))
    code, shown = _isolated(root, request)
    assert code == 0, shown
    assert _git(root, "show", "HEAD:vend/new.whl") == _EDITED
    (root / "vend" / "plain.whl").write_text(_PEER, encoding="utf-8")
    plain = ck.Request(waypoint="W1", subject="vend", paths=("vend/plain.whl",))
    assert ck.prepare(root, plain) is not None
    assert "vend/plain.whl" in _git(root, "diff", "--cached", "--name-only")


def test_an_ignored_file_under_a_named_directory_is_not_taken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory expands to what is not ignored, so a scratch file cannot ride in."""
    root = _decoy(tmp_path, monkeypatch)
    _ignoring_dir(root)
    (root / "vend" / "scratch.whl").write_text(_PEER, encoding="utf-8")
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    request = ck.Request(waypoint="W1", subject="dir", paths=("a.txt", "vend"))
    code, shown = _isolated(root, request)
    assert code == 0, shown
    held = _git(root, "ls-tree", "-r", "--name-only", "HEAD", "vend").split()
    assert held == ["vend/.gitignore"]


def test_only_a_regular_file_is_forced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A directory and a missing path go to the plain add; no link is created to test the rest."""
    root = _decoy(tmp_path, monkeypatch)
    assert ck.add_argv_list(root, ["a.txt", "gone.txt", "."]) == [
        ["add", "-f", "--", "a.txt"],
        ["add", "-A", "--", "gone.txt", "."],
    ]

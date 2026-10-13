# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for isolated mode's routing: nothing to take, the reason line, the lock state (W1101).

Split out of `test_commit_isolated` (W1101): see `test_commit_isolated_hooks`. The cases here name
what decided the path and what a request for a path that is nowhere reads as.
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


def _hook_text(root: Path, text: str) -> None:
    """Write the repository's pre-commit with the given text."""
    hook = root / ".githooks" / "pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text(text, encoding="utf-8")


def test_a_path_that_is_neither_on_disk_nor_tracked_is_not_a_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing to take reads NOT COMMITTED and HEAD does not move."""
    root = _decoy(tmp_path, monkeypatch)
    before = _git(root, "rev-parse", "HEAD")
    request = ck.Request(waypoint="W1", subject="nothing", paths=("ghost.txt",))
    code, shown = _isolated(root, request)
    assert code == ck.EXIT_NOT_COMMITTED
    assert shown.startswith("NOT COMMITTED repo")
    assert _git(root, "rev-parse", "HEAD") == before


def test_the_reason_names_what_decided_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W1015: forced, opted out, or what the repository's pre-commit says, each in its own words."""
    root = _decoy(tmp_path, monkeypatch)
    assert ck.isolation_reason(root, {ck.ISOLATED_ENV: "1"}) == f"forced by {ck.ISOLATED_ENV}=1"
    assert ck.isolation_reason(root, {ck.ISOLATED_ENV: "0"}) == f"opted out by {ck.ISOLATED_ENV}=0"
    assert ck.isolation_reason(root, {}) == (
        "the repository's pre-commit does not name MIKEMOL_REAL_ROOT"
    )
    _hook_text(root, "MIKEMOL_REAL_ROOT\n")
    assert ck.isolation_reason(root, {}) == "the repository's pre-commit names MIKEMOL_REAL_ROOT"


def test_the_lock_state_is_held_or_none_with_its_reason() -> None:
    """An empty claim reason means the claim is held above; any other is why there is none."""
    assert ck.lock_state("") == "held"
    assert ck.lock_state("the fence venv is not built") == "none (the fence venv is not built)"


def test_the_routing_line_names_the_path_its_reason_and_the_lock() -> None:
    """One line, before the verdict: which path ran, why, and the lock."""
    isolated = ck.routing_line(isolated=True, reason="why", lock="held")
    assert isolated == "mikemol-commit: path: isolated (why); lock: held"
    plain = ck.routing_line(isolated=False, reason="because", lock="none (x)")
    assert plain == "mikemol-commit: path: plain (because); lock: none (x)"

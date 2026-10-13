# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that an isolated commit leaves the real index at HEAD for what it committed (W1108).

nemik:W428 measured a stale real index after a clean isolated commit; a raw commit that then used
it staged deletions of tracked files. ⚑ THE FIRST ARM IS THE POSITIVE CONTROL: with another path
staged, the committed path reads as committed, ONLY the other path stays staged, and a plain
`git commit` afterwards lands only it. The rest drive `refresh_index` with a runner whose reset is
refused (a peer holding the index lock): it retries, then SAYS the index was not refreshed.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import isolated
from mikemol.hooks.snapshot import NAMESPACE_ENV

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    import pytest

_REQUEST = ck.Request(waypoint="W1", subject="isolated subject", paths=("a.txt",))
_LOCKED = "fatal: Unable to create '.git/index.lock': File exists."


def _git(root: Path, *args: str) -> str:
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def _decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
    for name in ("a.txt", "b.txt"):
        (root / name).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    return root


class _Refusing:
    """A runner whose `reset` is refused `refusals` times, then works; every other command works."""

    def __init__(self, refusals: int) -> None:
        self.refusals = refusals
        self.resets = 0

    def __call__(
        self, argv: Sequence[str], _env: Mapping[str, str], _cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        if argv[0] == "reset":
            self.resets += 1
            if self.resets <= self.refusals:
                return subprocess.CompletedProcess(list(argv), 128, "", _LOCKED)
        return subprocess.CompletedProcess(list(argv), 0, "", "")


def test_the_committed_path_reads_as_committed_and_only_the_other_staged_path_remains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another path staged beforehand stays staged; a plain commit after lands only that path."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text("edited\n", encoding="utf-8")
    (root / "b.txt").write_text("staged by a peer\n", encoding="utf-8")
    _git(root, "add", "b.txt")
    out = io.StringIO()
    assert ck.commit(root, _REQUEST, out, isolated=True) == 0
    assert "real index refreshed to HEAD for 1 committed path(s)" in out.getvalue()
    assert _git(root, "diff", "--cached", "--name-only").split() == ["b.txt"]
    _git(root, "commit", "--quiet", "-m", "the peer's own commit")
    assert _git(root, "show", "--name-only", "--format=", "HEAD").split() == ["b.txt"]


def test_a_refused_reset_is_retried_and_a_lock_that_clears_is_refreshed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two refusals then success: three resets, and the note says refreshed."""
    monkeypatch.setattr(isolated, "REFRESH_PAUSE_S", 0.0)
    refusals = 2
    run = _Refusing(refusals=refusals)
    note = isolated.refresh_index(tmp_path, ["a.txt"], run)
    assert note.startswith("real index refreshed")
    assert run.resets == refusals + 1


def test_a_reset_that_stays_refused_says_the_index_was_not_refreshed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Every attempt refused: the note names the command to run, and the attempts are bounded."""
    monkeypatch.setattr(isolated, "REFRESH_PAUSE_S", 0.0)
    run = _Refusing(refusals=100)
    note = isolated.refresh_index(tmp_path, ["a.txt", "n.txt"], run)
    assert note.startswith("real index NOT refreshed")
    assert "git reset -q -- a.txt n.txt" in note
    assert _LOCKED in note
    assert run.resets == isolated.REFRESH_ATTEMPTS

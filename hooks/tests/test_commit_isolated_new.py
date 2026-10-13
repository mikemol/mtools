# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the isolated gate sees a NAMED new file and never an unnamed untracked one.

amr-skills:W347 asked that `mikemol-commit` intent-add (`git add -N`) the new files it is named
before the gate, and refuse an unnamed new file, so that a gate which names its inputs from
`git ls-files` never reads content the commit does not carry. ⚑ THE ISOLATED PATH ALREADY DOES THE
WORK: the private index takes the named paths with `add`, the snapshot is materialized from that
tree alone, and the pre-commit hook runs inside the snapshot. These witness it with a hook that
refuses unless the named file is there (the positive control) and refuses if the unnamed one is.
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


_GATE = (
    "#!/bin/sh\n"
    '[ -e new.txt ] || { echo "the named new file is not in the gate tree" >&2; exit 1; }\n'
    '[ ! -e stray.txt ] || { echo "an unnamed untracked file reached the gate" >&2; exit 1; }\n'
)


def _gated(root: Path) -> None:
    """Install a pre-commit hook that checks which new files the gate's tree holds."""
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(_GATE, encoding="utf-8")
    hook.chmod(0o755)


def test_a_named_new_file_is_in_the_gate_tree_and_an_unnamed_one_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hook passes only if new.txt is there and stray.txt is not; HEAD then holds new.txt."""
    root = _decoy(tmp_path, monkeypatch)
    _gated(root)
    (root / "new.txt").write_text(_EDITED, encoding="utf-8")
    (root / "stray.txt").write_text(_PEER, encoding="utf-8")
    request = ck.Request(waypoint="W1", subject="new", paths=("new.txt",))
    code, shown = _isolated(root, request)
    assert code == 0, shown
    assert _git(root, "show", "HEAD:new.txt") == _EDITED
    assert _git(root, "ls-tree", "-r", "--name-only", "HEAD").split() == [
        "a.txt",
        "b.txt",
        "c.txt",
        "new.txt",
    ]
    assert (root / "stray.txt").read_text(encoding="utf-8") == _PEER


def test_the_same_gate_refuses_when_the_new_file_is_not_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: naming only a.txt leaves new.txt out of the gate tree, so the hook refuses."""
    root = _decoy(tmp_path, monkeypatch)
    _gated(root)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    (root / "new.txt").write_text(_PEER, encoding="utf-8")
    code, shown = _isolated(root)
    assert code != 0
    assert "the named new file is not in the gate tree" in shown

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that isolated mode finds a host tool, and when a repository's hook turns it on.

Split out of `test_commit_isolated` (W1101): that target built a real repository per case and sat at
its 60 s timeout under host load, and the operator's ruling (2026-10-10) is to shard a slow target,
never to lengthen it. Same decoy repository and helpers; the cases here are the tool-only-the-real-
root-has control and the `isolation_wanted` decisions.
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


_NEEDS_REAL_TOOL = (
    "#!/bin/sh\n"
    '[ -x "${MIKEMOL_REAL_ROOT:?not set}/.venv/bin/tool" ] || exit 1\n'
    "[ ! -e .venv ] || exit 1\n"
)


def _tool_only_the_real_root_has(root: Path) -> None:
    """Give the repository an untracked host tool and a pre-commit hook that needs it."""
    tool = root / ".venv" / "bin" / "tool"
    tool.parent.mkdir(parents=True)
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(_EXECUTABLE)
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(_NEEDS_REAL_TOOL, encoding="utf-8")
    hook.chmod(_EXECUTABLE)


def test_an_isolated_commit_finds_a_tool_only_the_real_root_has(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W941: the hook runs in a snapshot with no .venv and reads its tool from MIKEMOL_REAL_ROOT."""
    root = _decoy(tmp_path, monkeypatch)
    _tool_only_the_real_root_has(root)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    code, shown = _isolated(root)
    assert code == 0, shown
    assert _git(root, "show", "HEAD:a.txt") == _EDITED


def test_the_same_hook_refuses_a_normal_commit_which_is_the_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without isolation MIKEMOL_REAL_ROOT is unset, so the hook refuses: it does discriminate."""
    root = _decoy(tmp_path, monkeypatch)
    _tool_only_the_real_root_has(root)
    (root / "a.txt").write_text(_EDITED, encoding="utf-8")
    before = _git(root, "rev-parse", "HEAD")
    out = io.StringIO()
    code = ck.commit(root, _REQUEST, out)
    assert code != 0
    assert out.getvalue().splitlines()[-1].startswith("REFUSED repo")
    assert _git(root, "rev-parse", "HEAD") == before


def _hook_text(root: Path, text: str) -> None:
    """Write the repository's pre-commit with the given text."""
    hook = root / ".githooks" / "pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text(text, encoding="utf-8")


def test_isolation_is_on_where_the_repos_hook_reads_the_real_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W904: unset, the pre-commit's own text decides; naming MIKEMOL_REAL_ROOT opts in."""
    root = _decoy(tmp_path, monkeypatch)
    _hook_text(root, 'tools="${MIKEMOL_REAL_ROOT:-$root}"\n')
    assert ck.isolation_wanted(root, {})


def test_isolation_is_off_where_the_hook_does_not_know_the_real_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A peer repository's gate that finds its tools beside the checkout keeps today's mode."""
    root = _decoy(tmp_path, monkeypatch)
    assert not ck.isolation_wanted(root, {})
    _hook_text(root, "#!/bin/sh\nexit 0\n")
    assert not ck.isolation_wanted(root, {})


def test_the_environment_opts_out_and_forces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """=0 turns isolation off even where supported; =1 turns it on even where it is not."""
    root = _decoy(tmp_path, monkeypatch)
    _hook_text(root, "MIKEMOL_REAL_ROOT\n")
    assert not ck.isolation_wanted(root, {ck.ISOLATED_ENV: "0"})
    _hook_text(root, "#!/bin/sh\n")
    assert ck.isolation_wanted(root, {ck.ISOLATED_ENV: "1"})
    assert not ck.isolation_wanted(root, {ck.ISOLATED_ENV: "yes"})

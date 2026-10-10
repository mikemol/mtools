# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The commit claim is keyed on the repository being committed, not on the launcher (W910).

⚑ W886 wrapped `hooks/bin/mikemol-commit` in a fence claim keyed on the LAUNCHER's checkout, so a
commit to paperkit (a gate of minutes) held every mtools commit behind it. The lock now lives where
the repository is resolved, and these arms use a TARGET repository that is not where anything runs
from, a stub fence that records the claim it was asked for, and the real `main`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata

if TYPE_CHECKING:
    from pathlib import Path

_EXECUTABLE = 0o755
_TIMEOUT_S = 60
_IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")
_QUEUE = ".claude/paths-forward.json"
_FENCE = '#!/bin/sh\necho "CLAIM=$3 $4" >> "$FENCE_LOG"\nshift 4\nexec "$@"\n'


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *_IDENTITY, *args], cwd=cwd, check=True, capture_output=True, timeout=_TIMEOUT_S
    )


def _repo(parent: Path, name: str) -> Path:
    """Make a repository with one tracked queue file and an uncommitted edit to it.

    Returns:
        the repository.

    """
    repo = parent / name
    (repo / ".claude").mkdir(parents=True)
    _git(parent, "init", "-q", str(repo))
    (repo / _QUEUE).write_text("{}\n", encoding="utf-8")
    _git(repo, "add", _QUEUE)
    _git(repo, "commit", "-q", "-m", "first")
    (repo / _QUEUE).write_text('{"a": 1}\n', encoding="utf-8")
    return repo


def _fence(tmp_path: Path) -> Path:
    path = tmp_path / "fence"
    path.write_text(_FENCE, encoding="utf-8")
    path.chmod(_EXECUTABLE)
    return path


def test_the_claim_names_the_target_repositorys_git_directory(tmp_path: Path) -> None:
    """The hold is on `<target>/.git/mtools/commit`, whatever checkout the launcher lives in."""
    target = _repo(tmp_path, "paperkit")
    fence = _fence(tmp_path)
    got = commit_kata.claim_of(target, {commit_kata.FENCE_ENV: str(fence)}, ["python", "x"])
    assert isinstance(got, commit_kata.Claim)
    gitdir = (target / ".git").resolve()
    assert got.argv[:5] == [str(fence), "hold", "0", f"claim:path:{gitdir}/mtools/commit", "--"]
    assert got.env["MEMBUDGET_FILE"] == f"{gitdir}/mtools/commit.ledger"


def test_two_repositories_get_two_different_claims(tmp_path: Path) -> None:
    """A paperkit gate no longer holds an mtools commit: the claim labels differ."""
    env = {commit_kata.FENCE_ENV: str(_fence(tmp_path))}
    one = commit_kata.claim_of(_repo(tmp_path, "one"), env, ["x"])
    two = commit_kata.claim_of(_repo(tmp_path, "two"), env, ["x"])
    assert isinstance(one, commit_kata.Claim)
    assert isinstance(two, commit_kata.Claim)
    assert one.argv[3] != two.argv[3]


def test_the_load_gate_is_off_and_the_wait_bounded(tmp_path: Path) -> None:
    """A busy host must not stall a commit, and a wedged holder ends as a refusal."""
    target = _repo(tmp_path, "r")
    env = {commit_kata.FENCE_ENV: str(_fence(tmp_path))}
    got = commit_kata.claim_of(target, env, ["x"])
    assert isinstance(got, commit_kata.Claim)
    assert got.env["MEMBUDGET_MAXLOAD"] == "0"
    assert got.env["MEMBUDGET_TIMEOUT"] == commit_kata.DEFAULT_LOCK_TIMEOUT_S
    env[commit_kata.TIMEOUT_ENV] = "90"
    again = commit_kata.claim_of(target, env, ["x"])
    assert isinstance(again, commit_kata.Claim)
    assert again.env["MEMBUDGET_TIMEOUT"] == "90"


def test_the_commands_own_budget_variables_are_put_back_or_removed(tmp_path: Path) -> None:
    """Between the hold and the commit, `env` restores what the caller had and removes the rest."""
    target = _repo(tmp_path, "r")
    env = {
        commit_kata.FENCE_ENV: str(_fence(tmp_path)),
        "MEMBUDGET_FILE": "/host/b",
        "MEMBUDGET_MAXLOAD": "7",
    }
    got = commit_kata.claim_of(target, env, ["python", "x"])
    assert isinstance(got, commit_kata.Claim)
    inner = got.argv[got.argv.index("env") :]
    assert "MEMBUDGET_FILE=/host/b" in inner
    assert "MEMBUDGET_MAXLOAD=7" in inner
    assert "-u" in inner
    assert f"{commit_kata.HELD_ENV}=1" in inner
    assert inner[-2:] == ["python", "x"]


def test_a_nested_call_does_not_take_a_second_claim(tmp_path: Path) -> None:
    """With the marker set the claim is already held above: no plan, no note."""
    target = _repo(tmp_path, "r")
    assert not commit_kata.claim_of(target, {commit_kata.HELD_ENV: "1"}, ["x"])


def test_no_fence_or_no_git_checkout_gives_a_reason_not_a_claim(tmp_path: Path) -> None:
    """Both gaps are said, and neither is an exception."""
    target = _repo(tmp_path, "r")
    assert "fence venv" in str(commit_kata.claim_of(target, {}, ["x"]))
    plain = tmp_path / "plain"
    plain.mkdir()
    got = commit_kata.claim_of(plain, {commit_kata.FENCE_ENV: str(_fence(tmp_path))}, ["x"])
    assert "not a git checkout" in str(got)


def test_the_real_main_commits_under_the_target_repositorys_claim(tmp_path: Path) -> None:
    """End to end: the commit lands, and the fence saw the TARGET's claim, not the launcher's."""
    target = _repo(tmp_path, "paperkit")
    entry = tmp_path / "entry.py"
    entry.write_text(
        "from mikemol.hooks.commit_kata import main\nraise SystemExit(main())\n", encoding="utf-8"
    )
    log = tmp_path / "log"
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.pathsep.join(sys.path),
        commit_kata.FENCE_ENV: str(_fence(tmp_path)),
        "FENCE_LOG": str(log),
        "HOME": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    done = subprocess.run(
        [sys.executable, str(entry), str(target), "--waypoint", "W9", "--subject", "s", _QUEUE],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )
    assert "COMMITTED paperkit" in done.stdout, done.stderr
    gitdir = (target / ".git").resolve()
    assert f"CLAIM=claim:path:{gitdir}/mtools/commit --" in log.read_text(encoding="utf-8")

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The post-commit stub starts the ledger census detached, once, and only where the venv is (W825).

⚑ Each arm runs the REAL `.githooks/post-commit` inside a throwaway clone whose origin is a local
bare repository, so the push the stub makes first is real and harmless. The census is a fake
console script that records its argv, so what the stub started is observed rather than inferred.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

_STUB = Path(__file__).parent.parent.parent / ".githooks" / "post-commit"
_CENSUS_REL = Path("bazel-bin") / "hooks" / ".venv" / "bin" / "mikemol-pycheck"
_EXECUTABLE = 0o755
_TIMEOUT_S = 60
_WAIT_S = 20.0
_POLL_S = 0.1
_QUIET_S = 1.0
_IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")


def _git(cwd: Path, *args: str) -> str:
    """Run git in `cwd`, failing loudly.

    Returns:
        its stdout.

    """
    done = subprocess.run(
        ["git", *_IDENTITY, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        timeout=_TIMEOUT_S,
    )
    return done.stdout


def _clone(tmp_path: Path) -> Path:
    """Make a clone with one commit, whose tree the gate witness already records.

    Returns:
        the clone's top level.

    """
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    repo = tmp_path / "repo"
    _git(tmp_path, "init", "-b", "main", str(repo))
    _git(repo, "remote", "add", "origin", str(origin))
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "first")
    witness = repo / ".git" / "mtools" / "gate-verified"
    witness.parent.mkdir()
    witness.write_text(_git(repo, "rev-parse", "HEAD^{tree}"), encoding="utf-8")
    return repo


def _install(repo: Path, body: str) -> None:
    """Install a fake census console script with `body` as its shell text."""
    script = repo / _CENSUS_REL
    script.parent.mkdir(parents=True)
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(_EXECUTABLE)


def _run_stub(repo: Path) -> subprocess.CompletedProcess[str]:
    """Run the real stub in `repo`.

    Returns:
        the finished process.

    """
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(repo.parent)}
    return subprocess.run(
        [str(_STUB)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )


def _wait_for(path: Path) -> bool:
    """Wait for a detached child to write `path`.

    Returns:
        True when it appeared in time.

    """
    deadline = time.monotonic() + _WAIT_S
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(_POLL_S)
    return False


def test_the_stub_starts_the_census_with_the_repo_root(tmp_path: Path) -> None:
    """After the push, the census is started once with --refresh-ledger and the top level."""
    repo = _clone(tmp_path)
    record = tmp_path / "argv.txt"
    _install(repo, f'printf "%s\\n" "$@" > "{record}"')
    proc = _run_stub(repo)
    assert proc.returncode == 0, proc.stdout
    assert _wait_for(record), proc.stdout
    assert record.read_text(encoding="utf-8").splitlines() == ["--refresh-ledger", str(repo)]


def test_the_stub_returns_without_waiting_for_the_census(tmp_path: Path) -> None:
    """A census that outlives the hook does not hold it: the stub returns while it still runs."""
    repo = _clone(tmp_path)
    _install(repo, "sleep 30")
    started = time.monotonic()
    proc = _run_stub(repo)
    assert proc.returncode == 0
    assert time.monotonic() - started < _WAIT_S


def test_an_absent_venv_is_a_silent_skip(tmp_path: Path) -> None:
    """With no built venv the stub still pushes, exits 0, and starts nothing."""
    repo = _clone(tmp_path)
    proc = _run_stub(repo)
    assert proc.returncode == 0
    assert "pushed" in proc.stdout
    assert not (repo / ".git" / "mtools" / "ledger-refresh.log").exists()


def test_an_unverified_tree_starts_no_census(tmp_path: Path) -> None:
    """The refresh is behind the gate witness: a commit the gate never ran for starts nothing."""
    repo = _clone(tmp_path)
    record = tmp_path / "argv.txt"
    _install(repo, f'printf "ran" > "{record}"')
    (repo / ".git" / "mtools" / "gate-verified").write_text("not-this-tree\n", encoding="utf-8")
    proc = _run_stub(repo)
    assert proc.returncode == 0
    assert "THE GATE DID NOT RUN" in proc.stdout
    time.sleep(_QUIET_S)
    assert not record.exists()

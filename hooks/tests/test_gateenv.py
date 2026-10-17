# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the gate does not see the submitter's own MIKEMOL_ variables (W1448).

⚑ THE CONTROL IS THE DEFECT: a real pre-commit hook dumps the environment it was given, the test
arms `MIKEMOL_ENDPOINTS` (as a submission that wants spans does), and the hook must NOT see it,
while still seeing the isolation's `MIKEMOL_REAL_ROOT`, the ordinary `PATH` and an unrelated
variable of the caller's. The same holds through `git commit` as through `git hook run`, because
both run the repository's hook. A non-gate command keeps the whole environment.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, gateenv

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

GIT = shutil.which("git") or "git"
HOOK = "#!/bin/sh\nenv > hook-env.txt\nexit 0\n"


def _git(root: Path, *args: str) -> str:
    argv = [GIT, "-C", str(root), *args]
    done = subprocess.run(argv, capture_output=True, text=True, check=True)
    out: str = done.stdout
    return out


def _repo(tmp_path: Path) -> Path:
    # A repository whose pre-commit hook writes its environment to hook-env.txt in the cwd.
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@e.invalid")
    _git(root, "config", "user.name", "t")
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(HOOK, encoding="utf-8")
    hook.chmod(0o755)
    return root


def _seen(root: Path) -> dict[str, str]:
    lines = (root / "hook-env.txt").read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line)


def test_the_subcommand_skips_the_global_dash_c_option() -> None:
    """`git -C path commit` is a commit; a bare option list names nothing."""
    assert gateenv.subcommand(["-C", "/r", "commit", "-m", "x"]) == "commit"
    assert gateenv.subcommand(["hook", "run", "pre-commit"]) == "hook"
    assert not gateenv.subcommand(["--version"])
    assert not gateenv.subcommand([])


def test_scrubbing_keeps_the_gates_own_variables_and_everything_outside_the_namespace() -> None:
    """The list and the pass-through, in one table."""
    env = {
        "MIKEMOL_ENDPOINTS": "/e.json",
        "MIKEMOL_CALLER": "me",
        "MIKEMOL_REAL_ROOT": "/r",
        "MIKEMOL_COMMIT_ISOLATED": "1",
        "PATH": "/bin",
        "BUILDBUDDY_API_KEY": "k",
    }
    kept = ["BUILDBUDDY_API_KEY", "MIKEMOL_COMMIT_ISOLATED", "MIKEMOL_REAL_ROOT", "PATH"]
    assert sorted(gateenv.scrubbed(env)) == kept


def test_only_the_commands_that_run_a_hook_are_scrubbed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plumbing with nothing to add inherits as ever; plumbing with extras keeps everything."""
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "/e.json")
    assert gateenv.child_env(["rev-parse", "HEAD"], {}) is None
    plumbing = gateenv.child_env(["update-index", "-q"], {"GIT_DIR": "/g"})
    assert plumbing is not None
    assert plumbing["MIKEMOL_ENDPOINTS"] == "/e.json"
    gate = gateenv.child_env(["hook", "run", "pre-commit"], {})
    assert gate is not None
    assert "MIKEMOL_ENDPOINTS" not in gate


def test_the_hook_run_by_the_gate_does_not_see_an_armed_endpoints_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: `git hook run pre-commit` through the real runner."""
    root = _repo(tmp_path)
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "/e.json")
    monkeypatch.setenv("UNRELATED_CALLER_VAR", "kept")
    done = commit_kata.run_git_in(["hook", "run", "pre-commit"], {"MIKEMOL_REAL_ROOT": "/r"}, root)
    assert done.returncode == 0
    seen = _seen(root)
    assert "MIKEMOL_ENDPOINTS" not in seen
    assert seen["MIKEMOL_REAL_ROOT"] == "/r"
    assert seen["UNRELATED_CALLER_VAR"] == "kept"
    assert seen["PATH"].endswith(os.environ["PATH"])


def test_a_commit_runs_its_hook_in_the_same_scrubbed_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`git commit` is the other way the hook runs; the armed variable does not reach it either."""
    root = _repo(tmp_path)
    (root / "a.txt").write_text("x\n", encoding="utf-8")
    _git(root, "add", "a.txt")
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "/e.json")
    done = commit_kata.run_git_in(["commit", "-q", "-m", "m"], {}, root)
    assert done.returncode == 0
    assert "MIKEMOL_ENDPOINTS" not in _seen(root)

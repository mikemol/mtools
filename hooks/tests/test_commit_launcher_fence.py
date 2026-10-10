# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`hooks/bin/mikemol-commit` names the fence for the commit; it takes no claim itself (W910).

⚑ The claim moved into `commit_kata.main`, which knows which repository is being committed (W886
keyed it on the launcher's checkout, so one repo's gate held every repo's commits). What stays here
is one fact: where the fence is. The stand-in venv's `python3` prints the variable it received.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_LAUNCHER = Path(__file__).parent.parent / "bin" / "mikemol-commit"
_EXECUTABLE = 0o755
_TIMEOUT_S = 30
_PYTHON = '#!/bin/sh\necho "FENCE=${MIKEMOL_FENCE_BIN-unset}"\necho "ARGS=$#"\n'


def _checkout(tmp_path: Path, *, fence: bool) -> Path:
    """Write a fake checkout with the hooks venv, optionally with a built fence.

    Returns:
        the fake checkout.

    """
    root = tmp_path / "project"
    bindir = root / "bazel-bin" / "hooks" / ".venv" / "bin"
    bindir.mkdir(parents=True)
    python = bindir / "python3"
    python.write_text(_PYTHON, encoding="utf-8")
    python.chmod(_EXECUTABLE)
    (bindir / "mikemol-commit").write_text("# entry\n", encoding="utf-8")
    if fence:
        tool = root / "bazel-bin" / "fence" / ".venv" / "bin" / "mikemol-membudget"
        tool.parent.mkdir(parents=True)
        tool.write_text("#!/bin/sh\n", encoding="utf-8")
        tool.chmod(_EXECUTABLE)
    return root


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "MIKEMOL_ROOT": str(root)}
    return subprocess.run(
        [str(_LAUNCHER), "repo", "--waypoint", "W1"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=_TIMEOUT_S,
    )


def test_a_built_fence_is_named_to_the_commit(tmp_path: Path) -> None:
    """The commit learns where the fence is through MIKEMOL_FENCE_BIN."""
    root = _checkout(tmp_path, fence=True)
    proc = _run(root)
    fence = root / "bazel-bin" / "fence" / ".venv" / "bin" / "mikemol-membudget"
    assert f"FENCE={fence}" in proc.stdout.splitlines()


def test_an_unbuilt_fence_names_nothing(tmp_path: Path) -> None:
    """No fence venv: the variable is unset, and the commit says so itself and runs unlocked."""
    proc = _run(_checkout(tmp_path, fence=False))
    assert "FENCE=unset" in proc.stdout.splitlines()
    assert proc.returncode == 0


def test_the_launcher_takes_no_claim_of_its_own(tmp_path: Path) -> None:
    """Every argument still reaches the Python: three words plus the entry."""
    proc = _run(_checkout(tmp_path, fence=True))
    assert "ARGS=4" in proc.stdout.splitlines()

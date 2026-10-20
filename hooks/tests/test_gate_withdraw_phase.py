# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pre-commit's `phase` stops the gate at a boundary when its submission's marker exists."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from mikemol.hooks import gatephase

GATE = Path(__file__).parent.parent.parent / ".githooks" / "pre-commit"
BASH = shutil.which("bash") or "bash"
START = "phase() {"
MARKER_ENV = "MIKEMOL_COMMIT_WITHDRAW_MARKER"
WITHDRAWN = 75
SCRIPT = 'set -euo pipefail\n{function}\nphase "$1"\necho "after: rc=$?"\n'


def _function() -> str:
    """Slice `phase` out of the pre-commit, from its header to its closing brace.

    Returns:
        the function's text.

    """
    text = GATE.read_text(encoding="utf-8")
    head = text.index(START)
    return text[head : text.index("\n}\n", head) + 2]


def _run(name: str, marker: str | None) -> subprocess.CompletedProcess[str]:
    """Run `phase NAME` under bash as the gate's shell would, with the marker variable set or not.

    Returns:
        the finished process, both streams captured.

    """
    script = SCRIPT.replace("{function}", _function())
    env = {k: v for k, v in os.environ.items() if k != MARKER_ENV}
    if marker is not None:
        env[MARKER_ENV] = marker
    return subprocess.run(
        [BASH, "-c", script, "bash", name], capture_output=True, text=True, check=False, env=env
    )


def test_a_marker_stops_the_gate_at_the_boundary_and_is_removed(tmp_path: Path) -> None:
    """Exit 75 before the phase begins, the marker deleted, nothing after the call runs."""
    marker = tmp_path / "withdraw-100"
    marker.write_text("", encoding="utf-8")
    done = _run("witness_hooks", str(marker))
    assert done.returncode == WITHDRAWN
    assert "withdrawn before phase witness_hooks" in done.stderr
    assert not marker.exists()
    assert "after:" not in done.stdout
    assert gatephase.marks(done.stderr) == []


def test_no_marker_no_variable_or_another_submissions_marker_lets_the_gate_run(
    tmp_path: Path,
) -> None:
    """The mark prints as before when the file is absent, the variable is unset, or empty."""
    other = tmp_path / "withdraw-200"
    for marker in (str(other), "", None):
        done = _run("prebuild", marker)
        assert done.returncode == 0
        assert [m.name for m in gatephase.marks(done.stderr)] == ["prebuild"]
        assert "after: rc=0" in done.stdout

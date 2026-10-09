# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The inbound-asks launcher finds its venv under MTOOLS_ROOT when wired at user level (W881).

⚑ Wired once in `~/.claude/settings.json`, the hook runs in repos that hold no built venv: the
checkout comes from MTOOLS_ROOT and the repo it serves from CLAUDE_PROJECT_DIR. The fake venv's
`python3` prints its argument count, so what the exec received is observed rather than inferred.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_LAUNCHER = Path(__file__).parent.parent / "bin" / "mikemol-hook-inbound-asks"
_ENTRY = "mikemol-hook-inbound-asks"
_EXECUTABLE = 0o755
_TIMEOUT_S = 30
_STUB = '#!/bin/sh\necho "ARGC=$#"\n'


def _checkout(tmp_path: Path) -> Path:
    """Write a fake mtools checkout holding a built venv whose python3 echoes its argc.

    Returns:
        the fake checkout.

    """
    root = tmp_path / "mtools"
    bindir = root / "bazel-bin" / "hooks" / ".venv" / "bin"
    bindir.mkdir(parents=True)
    python = bindir / "python3"
    python.write_text(_STUB, encoding="utf-8")
    python.chmod(_EXECUTABLE)
    (bindir / _ENTRY).write_text("# entry\n", encoding="utf-8")
    return root


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run the real launcher with `env` plus PATH only.

    Returns:
        the finished process.

    """
    full = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **env}
    return subprocess.run(
        [str(_LAUNCHER)],
        capture_output=True,
        text=True,
        env=full,
        check=False,
        timeout=_TIMEOUT_S,
    )


def test_the_venv_comes_from_mtools_root_not_the_served_repo(tmp_path: Path) -> None:
    """A repo with no venv of its own is served from the checkout MTOOLS_ROOT names."""
    other = tmp_path / "other"
    other.mkdir()
    proc = _run({"MTOOLS_ROOT": str(_checkout(tmp_path)), "CLAUDE_PROJECT_DIR": str(other)})
    assert proc.stdout.splitlines()[0] == "ARGC=1", proc.stderr


def test_mtools_root_wins_over_the_project_directory(tmp_path: Path) -> None:
    """With both set, a project directory that holds no venv does not make the hook say so."""
    other = tmp_path / "other"
    other.mkdir()
    proc = _run({"MTOOLS_ROOT": str(_checkout(tmp_path)), "CLAUDE_PROJECT_DIR": str(other)})
    assert "venv is not built" not in proc.stderr


def test_without_mtools_root_the_project_directory_is_the_checkout(tmp_path: Path) -> None:
    """Per-repo wiring is unchanged: CLAUDE_PROJECT_DIR alone still finds the venv."""
    proc = _run({"CLAUDE_PROJECT_DIR": str(_checkout(tmp_path))})
    assert proc.stdout.splitlines()[0] == "ARGC=1", proc.stderr


def test_a_missing_mtools_venv_is_said_and_never_denied(tmp_path: Path) -> None:
    """An MTOOLS_ROOT with no built venv exits 0 with the repair on stderr."""
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = _run({"MTOOLS_ROOT": str(empty), "CLAUDE_PROJECT_DIR": str(tmp_path)})
    assert proc.returncode == 0
    assert not proc.stdout
    assert "venv is not built" in proc.stderr


def test_neither_variable_set_is_said_and_never_denied() -> None:
    """With nothing to resolve a root from, the hook says so and proceeds."""
    proc = _run({})
    assert proc.returncode == 0
    assert not proc.stdout
    assert "MTOOLS_ROOT" in proc.stderr

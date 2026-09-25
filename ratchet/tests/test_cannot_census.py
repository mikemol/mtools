# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for a census that cannot run: a named refusal, never a traceback.

⚑⚑ RUN AS A PROCESS, BECAUSE THE DEFECT IS WHAT THE PROCESS PRINTS. A missing ruff escaped
`run_ruff` as a raw `FileNotFoundError`, and Python's default handler exits 1 — the same status
as "new keys refused". Every consumer reads only nonzero, so a gate that could not look and a gate
that looked and refused were one outcome, told apart only by reading a traceback.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# ⚑ THE DECLARED STATUS, WRITTEN HERE RATHER THAN IMPORTED: an import of a constant HEAD lacks
# would fail at collection, and these arms must fail on HEAD by assertion.
_CANNOT_CENSUS = 2
_PASSED = 0
_TRACEBACK = "Traceback"
_SUPPLY_ENV = "RUFF_BIN"
_CONTROL_ENV = "CONTROL_RUFF"
_SUBDIR = "dist"
_NOT_EXECUTABLE = 0o644
_EXECUTABLE = 0o755
_CLEAN_SOURCE = '"""A clean module."""\n'


def _run(
    dist: Path, ruff_bin: str | None, *extra: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the ratchet CLI over `dist` in a child interpreter, from `cwd` when given.

    Returns:
        the completed process, with text stdout and stderr.

    """
    env = {k: v for k, v in os.environ.items() if k != _SUPPLY_ENV}
    if ruff_bin is not None:
        env[_SUPPLY_ENV] = ruff_bin
    return subprocess.run(
        [sys.executable, "-m", "mikemol.ratchet.cli", str(dist), *extra],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=cwd,
    )


def _real_ruff() -> Path:
    """Locate a real ruff: the runner's staged one (bazel), else the host venv's.

    Returns:
        an absolute path to a ruff binary.

    """
    staged = os.environ.get(_CONTROL_ENV)
    return Path(staged).absolute() if staged else Path(sys.executable).parent / "ruff"


def test_a_relative_ruff_bin_is_anchored_where_it_was_named(tmp_path: Path) -> None:
    """A relative RUFF_BIN names a path from the CALLER's directory, not from the distribution's.

    ⚑ ruff runs with `cwd=dist`; unanchored, `RUFF_BIN=../x/ruff` resolved inside the distribution
    and the census could not start. The distribution sits one level below the caller here, so the
    two readings of the same relative path name different files.
    """
    dist = tmp_path / _SUBDIR
    dist.mkdir()
    (dist / "clean.py").write_text(_CLEAN_SOURCE, encoding="utf-8")
    relative = os.path.relpath(_real_ruff(), start=tmp_path)
    proc = _run(dist, relative, "--init-absent", cwd=tmp_path)
    assert proc.returncode == _PASSED, proc.stderr
    assert "minted" in proc.stdout


def test_a_missing_ruff_refuses_by_name_without_a_traceback(tmp_path: Path) -> None:
    """A missing ruff refuses with its own status, names both supplies, and prints no traceback."""
    proc = _run(tmp_path, None)
    assert proc.returncode == _CANNOT_CENSUS, proc.stderr
    assert _TRACEBACK not in proc.stderr
    assert str(tmp_path / ".venv" / "bin" / "ruff") in proc.stderr
    assert _SUPPLY_ENV in proc.stderr


def test_a_present_ruff_gives_a_normal_census(tmp_path: Path) -> None:
    """Positive control: the ratchet venv's own ruff censuses a clean tree and mints."""
    (tmp_path / "clean.py").write_text(_CLEAN_SOURCE, encoding="utf-8")
    # The runner's staged ruff when it names one (bazel: CONTROL_RUFF, a RELATIVE path), else the
    # host venv's: the sandbox venv carries no ruff binary.
    ruff = os.environ.get(_CONTROL_ENV) or str(Path(sys.executable).parent / "ruff")
    proc = _run(tmp_path, ruff, "--init-absent")
    assert proc.returncode == _PASSED, proc.stderr
    assert "minted" in proc.stdout


def test_a_non_executable_ruff_refuses_by_name(tmp_path: Path) -> None:
    """A ruff that exists but cannot be executed refuses with the census status, not a crash."""
    ruff = tmp_path / "ruff"
    ruff.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    ruff.chmod(_NOT_EXECUTABLE)
    proc = _run(tmp_path, str(ruff))
    assert proc.returncode == _CANNOT_CENSUS, proc.stderr
    assert _TRACEBACK not in proc.stderr
    assert str(ruff) in proc.stderr


def test_an_unexpected_ruff_exit_refuses_through_the_cli(tmp_path: Path) -> None:
    """A ruff exiting 2 refuses through the CLI with the census status, not a traceback."""
    ruff = tmp_path / "ruff"
    ruff.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    ruff.chmod(_EXECUTABLE)
    proc = _run(tmp_path, str(ruff))
    assert proc.returncode == _CANNOT_CENSUS, proc.stderr
    assert _TRACEBACK not in proc.stderr

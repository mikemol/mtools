# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for directory operands: a virtual environment is pruned and counted (mtools:W559).

A venv is told by the `pyvenv.cfg` file directly inside it, never by its name. Git runs in a DECOY
repository made under tmp_path, with every GIT_* variable removed and global config off.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import cli

if TYPE_CHECKING:
    from pathlib import Path

_IMPORTER = "import target_mod\n"
_MAIN = "main_importer.py"
_THIRD_PARTY = "third_party_importer.py"
_CFG = "pyvenv.cfg"


def _plant(directory: Path, *, cfg: bool) -> None:
    directory.mkdir(parents=True)
    (directory / _THIRD_PARTY).write_text(_IMPORTER, encoding="utf-8")
    if cfg:
        (directory / _CFG).write_text("home = /usr/bin\n", encoding="utf-8")


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a decoy repository holding one importer.

    Returns:
        the repository root.

    """
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    root = tmp_path / "repo"
    root.mkdir()
    (root / _MAIN).write_text(_IMPORTER, encoding="utf-8")
    git = shutil.which("git")
    assert git is not None
    subprocess.run([git, "init", "-q"], cwd=root, check=True, capture_output=True)
    return root


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    code = cli.main(["importers", "target_mod", *argv])
    assert code == 0
    return capsys.readouterr().out


def test_a_venv_is_pruned_counted_and_its_importer_not_found(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory holding pyvenv.cfg is not walked, and the count says one."""
    _plant(repo / ".venv", cfg=True)
    out = _run(capsys, str(repo))
    assert f"{repo / _MAIN}:1" in out
    assert _THIRD_PARTY not in out
    assert "skipped 1 virtualenvs" in out


def test_a_dir_named_dot_venv_without_the_cfg_is_walked(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Detection is by the file, so a bare directory named .venv is walked and counts zero."""
    _plant(repo / ".venv", cfg=False)
    out = _run(capsys, str(repo))
    assert f"{repo / '.venv' / _THIRD_PARTY}:1" in out
    assert "skipped 0 virtualenvs" in out


def test_a_venv_with_another_name_is_pruned(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A venv named anything is pruned: the name is not the test."""
    _plant(repo / "env-of-mine" / "nested", cfg=True)
    out = _run(capsys, str(repo))
    assert _THIRD_PARTY not in out
    assert "skipped 1 virtualenvs" in out


def test_the_line_prints_zero_when_there_is_none(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory operand with no venv still prints the line, with 0."""
    out = _run(capsys, str(repo))
    assert "skipped 0 virtualenvs" in out


def test_the_count_survives_include_worktrees(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A venv is not a worktree: --include-worktrees still prunes and counts it."""
    _plant(repo / ".venv", cfg=True)
    out = _run(capsys, "--include-worktrees", str(repo))
    assert _THIRD_PARTY not in out
    assert "skipped 1 virtualenvs" in out

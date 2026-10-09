# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `tool_path.find`: the env override, the project's venv, then the env's own PATH."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

from mikemol.hooks import tool_path

if TYPE_CHECKING:
    from pathlib import Path

NAME = "mikemol-fake-tool"
VAR = "MIKEMOL_FAKE_TOOL"
MODE = stat.S_IRWXU


def _script(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / NAME
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(MODE)
    return script


def test_the_env_override_wins(tmp_path: Path) -> None:
    """⚑ A variable naming the binary beats the project's venv and the PATH."""
    named = _script(tmp_path / "named")
    _script(tmp_path / "root" / ".venv" / "bin")
    assert tool_path.find(NAME, VAR, tmp_path / "root", {VAR: str(named)}) == named


def test_the_projects_own_venv_comes_next(tmp_path: Path) -> None:
    """⚑ Without an override the project's .venv/bin answers before any PATH entry."""
    mine = _script(tmp_path / "root" / ".venv" / "bin")
    other = tmp_path / "elsewhere"
    _script(other)
    assert tool_path.find(NAME, VAR, tmp_path / "root", {"PATH": str(other)}) == mine


def test_the_path_searched_is_the_envs_not_the_processs(tmp_path: Path) -> None:
    """⚑ A tool on the env's PATH is found; an env without a PATH finds none (the W830 flake)."""
    on_env_path = _script(tmp_path / "bin")
    env = {"PATH": str(tmp_path / "bin")}
    assert tool_path.find(NAME, VAR, tmp_path / "root", env) == on_env_path
    assert tool_path.find(NAME, VAR, tmp_path / "root", {}) is None


def test_a_missing_tool_is_none_never_a_guess(tmp_path: Path) -> None:
    """⚑ A tool that is not found is None: no fallback to a different tool."""
    assert tool_path.find(NAME, VAR, tmp_path, {"PATH": str(tmp_path)}) is None

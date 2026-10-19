# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The gate hands ruff the config ruff itself would choose, not always the pyproject (W1093)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import project_root

if TYPE_CHECKING:
    from pathlib import Path


def _root(tmp_path: Path, *names: str) -> Path:
    for name in names:
        (tmp_path / name).write_text("", encoding="utf-8")
    return tmp_path


def test_a_ruff_toml_beside_a_pyproject_is_the_config(tmp_path: Path) -> None:
    """The gcalculus shape: width 100 lives in ruff.toml, the pyproject has no ruff table."""
    root = _root(tmp_path, "pyproject.toml", "ruff.toml")
    assert project_root.ruff_config_for(root) == root / "ruff.toml"


def test_a_dot_ruff_toml_beats_a_ruff_toml(tmp_path: Path) -> None:
    """Ruff's own order: `.ruff.toml` first, then `ruff.toml`, then `pyproject.toml`."""
    root = _root(tmp_path, "pyproject.toml", "ruff.toml", ".ruff.toml")
    assert project_root.ruff_config_for(root) == root / ".ruff.toml"


def test_with_no_ruff_only_file_the_pyproject_is_the_config(tmp_path: Path) -> None:
    """Every mtools dist declares its width in pyproject: nothing changes for them."""
    root = _root(tmp_path, "pyproject.toml")
    assert project_root.ruff_config_for(root) == root / "pyproject.toml"

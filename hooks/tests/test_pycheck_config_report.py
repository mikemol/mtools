# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ruff refusal names the config file that drove it and the width it set (W1596)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import pycheck

if TYPE_CHECKING:
    from pathlib import Path


def test_the_note_names_the_file_and_its_line_length(tmp_path: Path) -> None:
    """The gcalculus shape: a ruff.toml at 100 is named with that 100."""
    cfg = tmp_path / "ruff.toml"
    cfg.write_text("line-length = 100\n", encoding="utf-8")
    assert pycheck.config_note(cfg) == f"ruff config: {cfg} (line-length 100)"


def test_a_file_that_sets_no_width_reads_default(tmp_path: Path) -> None:
    """A pyproject with no ruff table gives ruff its own width, and the note says so."""
    cfg = tmp_path / "pyproject.toml"
    cfg.write_text("[project]\nname = 'x'\n", encoding="utf-8")
    assert pycheck.config_note(cfg).endswith("(line-length default)")


def test_an_unreadable_file_reads_default_and_does_not_raise(tmp_path: Path) -> None:
    """A missing config is a note, not a crash inside a refusal."""
    assert pycheck.config_note(tmp_path / "gone.toml").endswith("(line-length default)")

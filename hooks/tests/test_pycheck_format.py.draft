# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-pycheck --format`: the project's formatter, applied to one file."""

from __future__ import annotations

import io
import stat
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_format

if TYPE_CHECKING:
    from pathlib import Path

# A stand-in for `python3 -m ruff format ... -`: it reads stdin and writes it back upper-cased, so a
# changed file and an unchanged one are both one `printf` away, and no real ruff is needed.
_FAKE = "#!/bin/sh\ntr a-z A-Z\n"


def _project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    interpreter = tmp_path / ".venv" / "bin" / "python3"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(_FAKE, encoding="utf-8")
    interpreter.chmod(interpreter.stat().st_mode | stat.S_IXUSR)
    return tmp_path


def test_a_file_the_formatter_changes_is_rewritten_and_said_so(tmp_path: Path) -> None:
    """⚑ The formatter's output replaces the file, and the report names the file as formatted."""
    root = _project(tmp_path)
    target = root / "m.py"
    target.write_text("x = 1\n", encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    assert pycheck_format.format_file(target, out, err) == pycheck_format.EXIT_FORMATTED
    assert target.read_text(encoding="utf-8") == "X = 1\n"
    assert f"{target}: formatted" in out.getvalue()


def test_a_file_already_formatted_is_left_untouched(tmp_path: Path) -> None:
    """⚑ No write when the formatter changes nothing: the report says so."""
    root = _project(tmp_path)
    target = root / "m.py"
    target.write_text("X = 1\n", encoding="utf-8")
    before = target.stat().st_mtime_ns
    out, err = io.StringIO(), io.StringIO()
    assert pycheck_format.format_file(target, out, err) == pycheck_format.EXIT_FORMATTED
    assert target.stat().st_mtime_ns == before
    assert "already formatted" in out.getvalue()


def test_a_file_in_no_project_is_not_formatted_and_is_not_clean(tmp_path: Path) -> None:
    """⚑⚑ No governing project is exit 3, never a quiet success: nothing was formatted."""
    target = tmp_path / "m.py"
    target.write_text("x = 1\n", encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    assert pycheck_format.format_file(target, out, err) == pycheck_format.EXIT_NOT_RUN
    assert target.read_text(encoding="utf-8") == "x = 1\n"
    assert "not formatted" in err.getvalue()

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The real tool runs name existing trees, read files, and never read a crash as no findings."""

import sys
from pathlib import Path

import pytest

from mikemol.hooks import pycheck_ratchet_run as run


def _python(program: str) -> list[str]:
    return [sys.executable, "-c", program]


def test_only_the_trees_that_exist_are_named_in_the_fixed_order(tmp_path: Path) -> None:
    """A missing tree is skipped, and `src` comes before `tests`."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "src").mkdir()
    assert run.trees(tmp_path) == [str(tmp_path / "src"), str(tmp_path / "tests")]


def test_exit_one_is_findings_and_its_output_is_returned(tmp_path: Path) -> None:
    """Both tools exit 1 when they report, so the output is the answer."""
    assert run.run_tool("t", _python("print('x'); raise SystemExit(1)"), tmp_path) == "x\n"


def test_a_status_that_is_neither_clean_nor_findings_raises(tmp_path: Path) -> None:
    """A crash with empty output must not read as an empty finding list."""
    with pytest.raises(run.ToolFailedError, match="t exited 3"):
        run.run_tool("t", _python("raise SystemExit(3)"), tmp_path)


def test_a_missing_file_reads_as_none_and_a_present_one_as_its_text(tmp_path: Path) -> None:
    """The reader says absent rather than raising."""
    (tmp_path / "f.json").write_text("{}", encoding="utf-8")
    assert run.disk(tmp_path / "f.json") == "{}"
    assert run.disk(tmp_path / "absent.json") is None

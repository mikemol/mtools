# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The codemod leaves no wait_for_function call with a wall-clock bound (nemik:W706, W1684)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.webpage import waits

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

BOUNDED = "page.wait_for_function(READY, timeout=60000)\n"
BARE = "page.wait_for_function(READY)\n"
MULTILINE = "page.wait_for_function(\n    '() => ready',\n    arg=1,\n)\n"
OTHER = "page.wait_for_selector('#x', timeout=500)\nx = {'timeout': 5}\n"


def test_a_timeout_value_becomes_zero() -> None:
    """The bound is replaced in place."""
    assert waits.rewrite(BOUNDED) == "page.wait_for_function(READY, timeout=0)\n"


def test_a_call_without_one_gains_it() -> None:
    """A bare call gets timeout=0 after its last argument."""
    assert waits.rewrite(BARE) == "page.wait_for_function(READY, timeout=0)\n"


def test_a_multiline_call_keeps_its_arguments() -> None:
    """A call split over lines gains timeout=0 after the trailing comma."""
    out = waits.rewrite(MULTILINE)
    assert "arg=1," in out
    assert "timeout=0," in out
    assert out.count("wait_for_function") == 1


def test_nothing_else_is_touched() -> None:
    """Other calls and a plain dict with a timeout key stay as written."""
    assert waits.rewrite(OTHER) == OTHER


def test_a_second_run_changes_nothing() -> None:
    """The rewrite is idempotent over every shape."""
    source = BOUNDED + BARE + MULTILINE + OTHER
    once = waits.rewrite(source)
    assert waits.rewrite(once) == once


def test_a_dry_run_prints_the_diff_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --write the file is as it was, the diff is printed and the count says would."""
    target = tmp_path / "test_x.py"
    target.write_text(BOUNDED, encoding="utf-8")
    assert waits.main([str(target)]) == 0
    out = capsys.readouterr().out
    assert "-page.wait_for_function(READY, timeout=60000)" in out
    assert "+page.wait_for_function(READY, timeout=0)" in out
    assert "1 file(s) would change" in out
    assert target.read_text(encoding="utf-8") == BOUNDED


def test_write_rewrites_the_file_and_a_clean_file_is_not_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--write applies the rewrite; a file with nothing to change adds nothing to the count."""
    target = tmp_path / "test_x.py"
    clean = tmp_path / "test_y.py"
    target.write_text(BOUNDED, encoding="utf-8")
    clean.write_text(OTHER, encoding="utf-8")
    assert waits.main(["--write", str(target), str(clean)]) == 0
    assert "1 file(s) rewritten" in capsys.readouterr().out
    assert target.read_text(encoding="utf-8") == "page.wait_for_function(READY, timeout=0)\n"
    assert clean.read_text(encoding="utf-8") == OTHER

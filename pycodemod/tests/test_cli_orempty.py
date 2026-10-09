# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `or-empty`: the orempty planner rides the shared judge, nothing of its own."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_orempty import OrEmptyFlags, print_orempty

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

SOURCE = 'from typing import cast\n\nx = cast("Json", a or {})\n'
NO_SITE = "x = 1\n"
NAME = "tool.py"
STARTED = "judge started"


def _runner(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    # A stand-in for the project's mypy and ruff: the rewritten text is the one with fewer findings.
    if not argv[0].endswith("mypy"):
        return 0, "", ""
    probe = argv[-1]
    rewritten = "as_object(" in (cwd / probe).read_text(encoding="utf-8")
    messages = ["a"] if rewritten else ["a", "b"]
    lines = [f'{{"file": "{probe}", "message": "{m}"}}' for m in messages]
    return 1, "\n".join(lines), ""


def _exploding(_argv: Sequence[str], _cwd: Path) -> tuple[int, str, str]:
    raise RuntimeError(STARTED)


def _flags(root: Path, *, write: bool) -> OrEmptyFlags:
    helpers = ("as_object", "as_list")
    return OrEmptyFlags(str(root), write, "checks.jsonio", helpers[0], helpers[1])


def test_a_dry_run_reports_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """⚑ The default is a plan under the label or-empty: judged, said, untouched."""
    target = tmp_path / NAME
    target.write_text(SOURCE, encoding="utf-8")
    assert print_orempty([str(target)], _flags(tmp_path, write=False), _runner) == 0
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "or-empty would-write" in capsys.readouterr().out


def test_write_lands_the_rewrite_the_judge_accepts(tmp_path: Path) -> None:
    """⚑ `--write` applies the candidate: the cast is a helper call and the import is there."""
    target = tmp_path / NAME
    target.write_text(SOURCE, encoding="utf-8")
    assert print_orempty([str(target)], _flags(tmp_path, write=True), _runner) == 0
    text = target.read_text(encoding="utf-8")
    assert "x = as_object(a)" in text
    assert "from checks.jsonio import as_object" in text


def test_a_file_with_no_site_is_not_judged(tmp_path: Path) -> None:
    """⚑ Nothing to rewrite means no tool is started."""
    target = tmp_path / NAME
    target.write_text(NO_SITE, encoding="utf-8")
    assert print_orempty([str(target)], _flags(tmp_path, write=True), _exploding) == 0

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `codon-prep-tree`: both verbs, the bar, the tests, and a restore on any failure.

⚑ THE CONTROLS ARE THE TWO WAYS A PROJECT CAN FAIL AFTER BOTH VERBS ACCEPTED IT: the repository's
bar refuses a changed file, or the project's tests fail. Each restores every file the mode wrote and
is exit 2, so a half-prepared project never survives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_codonprep import print_codon_prep_tree

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    import pytest

    type Runner = Callable[[Sequence[str], Path], tuple[int, str, str]]

SOURCE = (
    "from __future__ import annotations\n\n"
    "from typing import TYPE_CHECKING\n\n"
    "if TYPE_CHECKING:\n    from a import B\n\n"
    "def f(x: B) -> int:\n    return 1\n"
)
NAME = "mod.py"
_TWO = 2
_GUARD_IMPORT = "from typing import TYPE_CHECKING\n"


def _runner(*, bar_exit: int = 0, tests_exit: int = 0) -> Runner:
    # A stand-in for ruff (its fix drops the guard import), the repository bar and the test run.
    def run(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        if "--fix" in argv:
            probe = cwd / argv[-1]
            probe.write_text(
                probe.read_text(encoding="utf-8").replace(_GUARD_IMPORT, ""), encoding="utf-8"
            )
        if "--check-file" in argv:
            return bar_exit, "", "line 1: a finding" if bar_exit else ""
        if argv[1:2] == ["-m"]:
            return tests_exit, "", "1 failed" if tests_exit else ""
        return 0, "", ""

    return run


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    (root / "src" / NAME).write_text(SOURCE, encoding="utf-8")
    return root


def test_both_verbs_land_and_nothing_is_left_to_quote(tmp_path: Path) -> None:
    """The guard and the future import are gone, the import is real, the annotation is bare."""
    root = _project(tmp_path)
    assert print_codon_prep_tree([str(root)], write=True, run=_runner()) == 0
    written = (root / "src" / NAME).read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in written
    assert "__future__" not in written
    assert "from a import B" in written
    assert "def f(x: B)" in written


def test_a_file_the_bar_refuses_restores_the_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both verbs accepted it, the bar did not: exit 2, the source as it was."""
    root = _project(tmp_path)
    assert print_codon_prep_tree([str(root)], write=True, run=_runner(bar_exit=1)) == _TWO
    assert (root / "src" / NAME).read_text(encoding="utf-8") == SOURCE
    assert "fails the bar" in capsys.readouterr().out


def test_failing_project_tests_restore_the_project_too(tmp_path: Path) -> None:
    """The bar passed and the tests did not: exit 2, the source as it was."""
    root = _project(tmp_path)
    assert print_codon_prep_tree([str(root)], write=True, run=_runner(tests_exit=1)) == _TWO
    assert (root / "src" / NAME).read_text(encoding="utf-8") == SOURCE


def test_a_dry_run_changes_nothing_and_a_project_without_a_venv_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The dry run reports and writes nothing; a root with no python is named and skipped."""
    root = _project(tmp_path)
    bare = tmp_path / "bare"
    bare.mkdir()
    assert print_codon_prep_tree([str(root), str(bare)], write=False, run=_runner()) == 0
    assert (root / "src" / NAME).read_text(encoding="utf-8") == SOURCE
    assert f"skipped {bare}" in capsys.readouterr().out

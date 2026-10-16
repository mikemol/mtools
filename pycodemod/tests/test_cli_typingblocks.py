# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `type-checking-imports`: written only when the guard count falls, tests pass.

⚑ THE CONTROL IS THE SECOND JUDGE: the hoist is clean to ruff and drops the guard count, and a
selftest that exits nonzero (an import cycle at run time) still refuses the file and leaves it as
it was. The stand-in ruff drops the now-unused `TYPE_CHECKING` import, as the real fix does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_typedargs import TypedArgsFlags
from mikemol.pycodemod.cli_typingblocks import print_typing_blocks, print_typing_blocks_tree

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    import pytest

    type Runner = Callable[[Sequence[str], Path], tuple[int, str, str]]

SOURCE = "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from a import B\n\nx = 1\n"
NAME = "mod.py"
_SELFTEST = "selftest-cmd"
_TWO = 2
_GUARD_IMPORT = "from typing import TYPE_CHECKING\n"


def _runner(selftest_exit: int = 0, tests_exit: int = 0) -> Runner:
    # A stand-in for the project's ruff and test run; its fix removes the guard import.
    def run(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        if "--fix" in argv:
            probe = cwd / argv[-1]
            probe.write_text(
                probe.read_text(encoding="utf-8").replace(_GUARD_IMPORT, ""), encoding="utf-8"
            )
        if argv[0] == _SELFTEST:
            return selftest_exit, "", ""
        if argv[1:2] == ["-m"]:
            return tests_exit, "", "1 failed" if tests_exit else ""
        return 0, "", ""

    return run


def _flags(root: Path, *, write: bool, selftest: str = "") -> TypedArgsFlags:
    return TypedArgsFlags(root=str(root), write=write, selftest=selftest)


def test_a_hoist_that_drops_the_guard_count_is_written_when_the_tests_pass(tmp_path: Path) -> None:
    """The block and its import go, `from a import B` stays, and the selftest ran clean."""
    target = tmp_path / NAME
    target.write_text(SOURCE, encoding="utf-8")
    flags = _flags(tmp_path, write=True, selftest=_SELFTEST)
    assert print_typing_blocks([str(target)], flags, _runner()) == 0
    written = target.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in written
    assert "from a import B" in written


def test_a_failing_selftest_refuses_the_file_and_leaves_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An import cycle shows as the project's tests failing: exit 1, the file as it was."""
    target = tmp_path / NAME
    target.write_text(SOURCE, encoding="utf-8")
    flags = _flags(tmp_path, write=True, selftest=_SELFTEST)
    assert print_typing_blocks([str(target)], flags, _runner(selftest_exit=1)) == 1
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "selftest failed" in capsys.readouterr().out


def test_failing_dist_tests_after_a_write_restore_every_file_and_are_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A cycle shows only when the dist's tests run: they run once, and their failure undoes it."""
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    target = root / "src" / NAME
    target.write_text(SOURCE, encoding="utf-8")
    assert print_typing_blocks_tree([str(root)], write=True, run=_runner(tests_exit=1)) == _TWO
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "every file restored" in capsys.readouterr().out


def test_the_tree_driver_runs_each_project_with_its_own_tests_and_skips_one_without(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A project with src and a python is judged with its own pytest; one without is skipped."""
    good = tmp_path / "good"
    (good / "src").mkdir(parents=True)
    (good / ".venv" / "bin").mkdir(parents=True)
    (good / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    (good / "src" / NAME).write_text(SOURCE, encoding="utf-8")
    bare = tmp_path / "bare"
    bare.mkdir()
    assert print_typing_blocks_tree([str(good), str(bare)], write=False, run=_runner()) == 0
    out = capsys.readouterr().out
    assert f"would-write {good / 'src' / NAME}" in out
    assert f"skipped {bare}" in out

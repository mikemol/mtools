# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `typed-args`: a file is written only when the project's judge says it improved."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod.cli_typedargs import PROBE_PREFIX, TypedArgsFlags, print_typedargs

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    type Runner = Callable[[Sequence[str], Path], tuple[int, str, str]]

SOURCE = (
    "from __future__ import annotations\n\nimport argparse\n\n\n"
    "def main() -> int:\n"
    "    parser = argparse.ArgumentParser()\n"
    '    parser.add_argument("--n", type=int)\n'
    "    args = parser.parse_args()\n"
    "    return args.n\n"
)
NO_PARSER = "def main() -> int:\n    return 1\n"
UNPARSEABLE = "def (:\n"
TWO = 2
NAME = "tool.py"
STARTED = "judge started"


def _runner(before: list[str], after: list[str], mypy_exit: int = 0) -> Runner:
    # A stand-in for the project's mypy and ruff: the candidate is the text that names a Namespace.
    def run(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        if not argv[0].endswith("mypy"):
            return 0, "", ""
        probe = argv[-1]
        typed = "argparse.Namespace" in (cwd / probe).read_text(encoding="utf-8")
        lines = [f'{{"file": "{probe}", "message": "{m}"}}' for m in (after if typed else before)]
        return mypy_exit, "\n".join(lines), ""

    return run


def _exploding(_argv: Sequence[str], _cwd: Path) -> tuple[int, str, str]:
    raise RuntimeError(STARTED)


def _project(tmp_path: Path, text: str) -> Path:
    target = tmp_path / NAME
    target.write_text(text, encoding="utf-8")
    return target


def _flags(root: Path, *, write: bool) -> TypedArgsFlags:
    return TypedArgsFlags(root=str(root), write=write)


def _leftovers(tmp_path: Path) -> list[Path]:
    return sorted(tmp_path.glob(f"{PROBE_PREFIX}*"))


def test_a_dry_run_says_what_it_would_write_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """⚑ The default is a plan: the judge ran, the verdict printed, the file untouched."""
    target = _project(tmp_path, SOURCE)
    run = _runner(["a", "b"], ["a"])
    assert print_typedargs([str(target)], _flags(tmp_path, write=False), run) == 0
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "would-write" in capsys.readouterr().out
    assert _leftovers(tmp_path) == []


def test_write_applies_a_candidate_the_judge_accepts(tmp_path: Path) -> None:
    """⚑ `--write` lands the formatted candidate when its findings are a strict subset."""
    target = _project(tmp_path, SOURCE)
    run = _runner(["a", "b"], ["a"])
    assert print_typedargs([str(target)], _flags(tmp_path, write=True), run) == 0
    assert "namespace=MainArgs()" in target.read_text(encoding="utf-8")
    assert _leftovers(tmp_path) == []


def test_a_new_message_is_refused_even_when_the_count_drops(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """⚑ A set, not a count: two findings traded for one NEW one is a regression, named."""
    target = _project(tmp_path, SOURCE)
    run = _runner(["a", "b"], ["fresh"])
    assert print_typedargs([str(target)], _flags(tmp_path, write=True), run) == 1
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "fresh" in capsys.readouterr().out


def test_no_fewer_findings_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """⚑ Equal is not better: a candidate that fixes nothing is not written."""
    target = _project(tmp_path, SOURCE)
    run = _runner(["a"], ["a"])
    assert print_typedargs([str(target)], _flags(tmp_path, write=True), run) == 1
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "no fewer findings" in capsys.readouterr().out


def test_a_tool_that_cannot_run_is_exit_two_never_a_pass(tmp_path: Path) -> None:
    """⚑ mypy exiting 2 is not a clean bill: nothing is written and the exit says so."""
    target = _project(tmp_path, SOURCE)
    run = _runner([], [], mypy_exit=TWO)
    assert print_typedargs([str(target)], _flags(tmp_path, write=True), run) == TWO
    assert target.read_text(encoding="utf-8") == SOURCE
    assert _leftovers(tmp_path) == []


def test_the_probe_is_removed_when_a_tool_raises(tmp_path: Path) -> None:
    """⚑ The probe sits in a shared tree for seconds and is gone on EVERY exit."""
    target = _project(tmp_path, SOURCE)
    with pytest.raises(RuntimeError, match=STARTED):
        print_typedargs([str(target)], _flags(tmp_path, write=True), _exploding)
    assert _leftovers(tmp_path) == []


def test_a_file_outside_the_root_is_exit_two(tmp_path: Path) -> None:
    """⚑ The judge is the root's own; a file it does not contain cannot be judged by it."""
    inside = tmp_path / "project"
    inside.mkdir()
    target = _project(tmp_path, SOURCE)
    assert print_typedargs([str(target)], _flags(inside, write=True), _exploding) == TWO


def test_a_file_without_a_parser_is_not_judged(tmp_path: Path) -> None:
    """⚑ Nothing to plan means no tool is started and the file counts as done."""
    target = _project(tmp_path, NO_PARSER)
    assert print_typedargs([str(target)], _flags(tmp_path, write=True), _exploding) == 0


def test_a_refusal_goes_to_the_worklist(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """⚑ What the planner cannot prove is printed with its reason and exits 1."""
    target = _project(tmp_path, UNPARSEABLE)
    assert print_typedargs([str(target)], _flags(tmp_path, write=True), _exploding) == 1
    assert "does not parse" in capsys.readouterr().out

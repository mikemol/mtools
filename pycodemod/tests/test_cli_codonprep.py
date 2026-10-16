# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `codon-prep-tree`: both verbs, the bar, the tests, and a restore on any failure.

⚑ THE CONTROLS ARE THE TWO WAYS A PROJECT CAN FAIL AFTER BOTH VERBS ACCEPTED IT: the repository's
bar refuses a changed file, or the project's tests fail. Each restores every file the mode wrote and
is exit 2, so a half-prepared project never survives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_codonprep import Refusal, print_codon_prep_tree

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


def test_keep_leaves_the_rewrite_in_place_when_the_bar_refuses_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The diagnosis route: exit 2 as before, but the written source stays for reproduction."""
    root = _project(tmp_path)
    assert (
        print_codon_prep_tree([str(root)], write=True, run=_runner(bar_exit=1), keep=True) == _TWO
    )
    assert (root / "src" / NAME).read_text(encoding="utf-8") != SOURCE
    assert "LEFT IN PLACE" in capsys.readouterr().out


def test_failing_project_tests_restore_the_project_too(tmp_path: Path) -> None:
    """The bar passed and the tests did not: exit 2, the source as it was."""
    root = _project(tmp_path)
    assert print_codon_prep_tree([str(root)], write=True, run=_runner(tests_exit=1)) == _TWO
    assert (root / "src" / NAME).read_text(encoding="utf-8") == SOURCE


def test_a_relative_root_reaches_the_bar_by_an_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: the bar's path is the same whether the root is given relative or absolute."""
    _project(tmp_path)
    monkeypatch.chdir(tmp_path)
    seen: list[str] = []
    inner = _runner()

    def run(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        if "--check-file" in argv:
            seen.append(argv[0])
        return inner(argv, cwd)

    assert print_codon_prep_tree(["proj"], write=True, run=run) == 0
    assert seen
    assert all(path.startswith("/") for path in seen)


def test_a_declared_mutant_the_rewrite_made_stale_restores_the_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pattern that matched before and matches nothing after: exit 2, the source as it was."""
    root = _project(tmp_path)
    (root / "mutants.regex").write_text(
        f"src/{NAME}|keeps-the-future-import|from __future__ import annotations|x|def=f\n",
        encoding="utf-8",
    )
    assert print_codon_prep_tree([str(root)], write=True, run=_runner()) == _TWO
    assert (root / "src" / NAME).read_text(encoding="utf-8") == SOURCE
    assert "keeps-the-future-import" in capsys.readouterr().out


def test_a_declaration_stale_before_the_run_is_not_charged_to_it(tmp_path: Path) -> None:
    """The control: a pattern that never matched is the dist's own debt, and the run proceeds."""
    root = _project(tmp_path)
    (root / "mutants.regex").write_text(
        f"src/{NAME}|never-matched|no such text|x|def=f\n", encoding="utf-8"
    )
    assert print_codon_prep_tree([str(root)], write=True, run=_runner()) == 0


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


_BOOL_RULE = "boolean-type-hint-positional-argument"
_PYPROJECT = '[tool.ruff.lint]\nselect = ["ALL"]\nignore = ["a"]\n'


def _rule_bar(rule: str) -> Runner:
    # A stand-in whose bar refuses a file for `rule` until the dist's pyproject lists that rule.
    inner = _runner()

    def run(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        if "--check-file" in argv:
            listed = f'"{rule}"' in (cwd / "pyproject.toml").read_text(encoding="utf-8")
            return (0, "", "") if listed else (4, f"--- ruff ---\n{rule}: a boolean\n", "")
        return inner(argv, cwd)

    return run


def test_a_refusal_that_is_only_a_rule_the_rewrite_contradicts_is_switched_off_not_fatal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The bar refuses on the boolean rule; the dist's pyproject gains it and the project stays."""
    root = _project(tmp_path)
    (root / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
    assert print_codon_prep_tree([str(root)], write=True, run=_rule_bar(_BOOL_RULE)) == 0
    assert f'"{_BOOL_RULE}"' in (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in (root / "src" / NAME).read_text(encoding="utf-8")
    assert "ruff rules switched off" in capsys.readouterr().out


def test_a_dist_with_a_per_file_table_gets_the_rule_for_the_file_not_the_global_list(
    tmp_path: Path,
) -> None:
    """The route for a dist that pins its global ignore list: only the offending file is exempt."""
    root = _project(tmp_path)
    pyproject = _PYPROJECT + '\n[tool.ruff.lint.per-file-ignores]\n"tests/*" = ["assert"]\n'
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    assert print_codon_prep_tree([str(root)], write=True, run=_rule_bar(_BOOL_RULE)) == 0
    written = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'ignore = ["a"]' in written
    assert f'"src/{NAME}" = ["{_BOOL_RULE}"]' in written


def test_ruffs_help_lines_are_not_read_as_rules() -> None:
    """The control: `help: ...` reads like `rule: message` and must not make a refusal unfixable."""
    output = f"--- ruff ---\n{_BOOL_RULE}: a boolean\n   --> f.py:1:1\nhelp: make it keyword-only\n"
    refusal = Refusal("f.py", 4, output)
    assert refusal.rules == {_BOOL_RULE}
    assert refusal.self_fixable


def test_a_refusal_for_any_other_rule_restores_the_project_and_the_pyproject(
    tmp_path: Path,
) -> None:
    """A rule outside the self-fixable set stays refused: files and pyproject come back."""
    root = _project(tmp_path)
    (root / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
    other = _rule_bar("complex-structure")
    assert print_codon_prep_tree([str(root)], write=True, run=other) == _TWO
    assert (root / "src" / NAME).read_text(encoding="utf-8") == SOURCE
    assert (root / "pyproject.toml").read_text(encoding="utf-8") == _PYPROJECT

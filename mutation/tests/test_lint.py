# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A distribution's declared defects are checked without a suite, by the grid's own parser."""

from pathlib import Path

import pytest

from mikemol.mutation import lint

_SOURCE = "def f():\n    return 1\n"
_SOUND = "src/mod.py|returns-two|return 1|return 2|def=f\n"
_USAGE = 2
_THREE = 3


def _dist(tmp_path: Path, declarations: str) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(_SOURCE, encoding="utf-8")
    (tmp_path / "mutants.regex").write_text(declarations, encoding="utf-8")
    return tmp_path


def test_a_declaration_that_plants_has_no_problem(tmp_path: Path) -> None:
    """The positive control: a sound line, and a dist with no file at all, are both clean."""
    assert lint.problems(_dist(tmp_path, _SOUND)) == []
    assert lint.problems(tmp_path / "elsewhere") == []


def test_a_bare_percent_is_named_by_the_parser_not_left_to_the_gate(tmp_path: Path) -> None:
    """The 2026-10-18 failure: a % in a pattern that is not %7C or %25 refuses the whole file."""
    found = lint.problems(_dist(tmp_path, "src/mod.py|bad|x % y|z|def=f\n"))
    assert len(found) == 1
    assert "bad escape" in found[0]
    assert "line 1" in found[0]


def test_a_module_that_is_not_a_file_a_stale_pattern_and_a_broken_rewrite_are_each_named(
    tmp_path: Path,
) -> None:
    """Each of the three the grid would report as errored or unapplied has its own line."""
    both = (
        "src/ghost.py|no-module|return 1|return 2|\n"
        "src/mod.py|stale|nothing-here|x|\n"
        "src/mod.py|breaks|return|return (|\n"
    )
    found = lint.problems(_dist(tmp_path, both))
    assert any("no-module: src/ghost.py is not a file" in line for line in found)
    assert any("stale: the pattern matches nothing in its scope" in line for line in found)
    assert any(line.startswith("src/mod.py::breaks:") for line in found)
    assert len(found) == _THREE


def test_main_exits_zero_clean_one_on_a_problem_and_two_on_misuse(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The exit code is the verdict, the lines go to stderr, and misuse is not a verdict."""
    assert lint.main([str(_dist(tmp_path, _SOUND))]) == 0
    assert not capsys.readouterr().err
    (tmp_path / "mutants.regex").write_text("src/mod.py|stale|nothing-here|x|\n", encoding="utf-8")
    assert lint.main([str(tmp_path)]) == 1
    assert "mutation-lint: src/mod.py::stale" in capsys.readouterr().err
    assert lint.main([]) == _USAGE

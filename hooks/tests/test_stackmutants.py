# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses of the submit-time mutant lint: which dists it asks about, and what it refuses (W1704).

⚑ THE CONTROLS ARE THE REFUSALS: a missing mutation venv and a lint that fails each refuse, a lint
that passes leaves nothing, and a path at the root names no dist.
"""

from __future__ import annotations

import stat
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import stackmutants

if TYPE_CHECKING:
    from pathlib import Path


def _venv(root: Path, script: str) -> None:
    # A stand-in for the mutation venv's interpreter: a script that ignores its arguments.
    python = stackmutants.mutation_python(root)
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text(f"#!{sys.executable}\n{script}\n", encoding="utf-8")
    python.chmod(python.stat().st_mode | stat.S_IXUSR)


def test_the_dists_are_the_top_directories_once_each_in_first_seen_order() -> None:
    """A stack names a dist by what it touches, not only by carrying its mutants.regex."""
    paths = ["waldo/src/a.py", "hooks/b.py", "waldo/tests/t.py", "README.md", "waldo/mutants.regex"]
    assert stackmutants.dists_of(paths) == ["waldo", "hooks"]
    assert stackmutants.dists_of(["README.md"]) == []


def test_no_lint_has_no_problems(tmp_path: Path) -> None:
    """The default seam is silent, so a caller that does not wire the lint is unchanged."""
    assert stackmutants.no_lint(tmp_path, ["x"]) == []


def test_a_missing_mutation_venv_refuses_and_says_how_to_build_it(tmp_path: Path) -> None:
    """A check that cannot run is not a pass."""
    problems = stackmutants.real_lint(tmp_path)(tmp_path, ["waldo"])
    assert len(problems) == 1
    assert "is missing: build it" in problems[0]


def test_a_failing_lint_is_named_per_dist_and_a_passing_one_is_silent(tmp_path: Path) -> None:
    """Each problem line is prefixed with its dist; exit 0 contributes nothing."""
    _venv(tmp_path, "import sys\nsys.stderr.write('W1: x is not a file\\n')\nsys.exit(1)")
    lint = stackmutants.real_lint(tmp_path)
    assert lint(tmp_path, ["waldo", "hooks"]) == [
        "waldo: W1: x is not a file",
        "hooks: W1: x is not a file",
    ]
    _venv(tmp_path, "import sys\nsys.stderr.write('noise\\n')\nsys.exit(0)")
    assert lint(tmp_path, ["waldo"]) == []


def test_a_failing_lint_with_no_output_still_refuses(tmp_path: Path) -> None:
    """Exit non-zero without a word is a refusal naming the exit, never a pass."""
    _venv(tmp_path, "import sys\nsys.exit(3)")
    assert stackmutants.real_lint(tmp_path)(tmp_path, ["waldo"]) == [
        "waldo: mutation lint exited 3 with no output"
    ]

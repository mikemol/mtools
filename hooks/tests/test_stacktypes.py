# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses of the submit-time type check: which dists it checks and what it refuses (W1704).

⚑ THE CONTROLS ARE THE REFUSALS AND THE SKIPS: a declaring dist with no venv, a failing mypy and a
mypy that dies silently each refuse, a passing one is silent, and a dist with no `[tool.mypy]`
table is never asked for a venv (the lesson of W1866).
"""

from __future__ import annotations

import stat
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import stackmutants, stacktypes

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _declare(snapshot: Path, dist: str, text: str = "[tool.mypy]\nstrict = true\n") -> None:
    (snapshot / dist).mkdir(parents=True, exist_ok=True)
    (snapshot / dist / "pyproject.toml").write_text(text, encoding="utf-8")


def _mypy(root: Path, dist: str, script: str) -> Path:
    # A stand-in for the dist's mypy: a script that records its argv and working directory.
    path = root / dist / ".venv" / "bin" / "mypy"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n{script}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_only_a_dist_with_a_mypy_table_is_checked(tmp_path: Path) -> None:
    """A pyproject without the table, and a dist without a pyproject, are not asked about mypy."""
    _declare(tmp_path, "typed")
    _declare(tmp_path, "plain", "[project]\nname = 'plain'\n")
    assert stacktypes.typed_dists(tmp_path, ["plain", "typed", "absent"]) == ["typed"]


def test_a_repo_with_no_typed_dist_needs_no_mypy(tmp_path: Path) -> None:
    """Estate's layout: nothing declares the table, so nothing is refused for a missing venv."""
    _declare(tmp_path, "plain", "[project]\nname = 'plain'\n")
    assert stacktypes.real_types(tmp_path)(tmp_path, ["plain", "src", "tests"]) == []


def test_a_declaring_dist_with_no_mypy_refuses_and_says_how_to_build_it(tmp_path: Path) -> None:
    """A check that cannot run is not a pass."""
    _declare(tmp_path, "typed")
    problems = stacktypes.real_types(tmp_path)(tmp_path, ["typed"])
    assert len(problems) == 1
    assert "is missing: build it" in problems[0]


def test_mypy_lines_are_named_per_dist_and_a_clean_run_is_silent(tmp_path: Path) -> None:
    """The errors come back prefixed by their dist; exit 0 contributes nothing."""
    snapshot = tmp_path / "ns" / "repo" / "tree"
    root = tmp_path / "real"
    _declare(snapshot, "typed")
    _mypy(root, "typed", "import sys\nprint('src/a.py:1: error: bad')\nsys.exit(1)")
    lint = stacktypes.real_types(root)
    assert lint(snapshot, ["typed"]) == ["typed: src/a.py:1: error: bad"]
    _mypy(root, "typed", "print('Success: no issues found')")
    assert lint(snapshot, ["typed"]) == []


def test_mypy_runs_in_the_snapshot_dist_with_its_cache_beside_the_tree(tmp_path: Path) -> None:
    """The working directory is the tip's dist and the cache is outside the snapshot tree."""
    snapshot = tmp_path / "ns" / "repo" / "tree"
    root = tmp_path / "real"
    _declare(snapshot, "typed")
    script = "import os, sys\nprint(os.getcwd(), *sys.argv[1:])\nsys.exit(1)"
    _mypy(root, "typed", script)
    (line,) = stacktypes.real_types(root)(snapshot, ["typed"])
    cache = snapshot.parent / "mypy-cache" / "typed"
    assert line == f"typed: {snapshot / 'typed'} --cache-dir={cache}"


def test_a_mypy_that_dies_without_output_still_refuses(tmp_path: Path) -> None:
    """Exit non-zero without a word is a refusal naming the exit, never a pass."""
    snapshot = tmp_path / "ns" / "repo" / "tree"
    root = tmp_path / "real"
    _declare(snapshot, "typed")
    _mypy(root, "typed", "import sys\nsys.exit(2)")
    problems = stacktypes.real_types(root)(snapshot, ["typed"])
    assert problems == ["typed: mypy exited 2 with no output"]


def test_chain_keeps_every_lints_problems_in_order(tmp_path: Path) -> None:
    """One lint failing does not hide the next: both sets of problems come back, in order."""

    def first(_snapshot: Path, _dists: Sequence[str]) -> list[str]:
        return ["a"]

    def second(_snapshot: Path, dists: Sequence[str]) -> list[str]:
        return [f"b:{','.join(dists)}"]

    assert stackmutants.chain(first, second)(tmp_path, ["x", "y"]) == ["a", "b:x,y"]
    assert stackmutants.chain()(tmp_path, ["x"]) == []

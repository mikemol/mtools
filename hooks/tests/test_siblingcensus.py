# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A reach is a path that resolves into another checkout; one that stays in the repo is not."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, siblingcensus, siblingcensus_cli

if TYPE_CHECKING:
    import pytest

ROOT = Path("/h/github/mtools")


def _targets(files: dict[str, str]) -> list[tuple[str, int, str]]:
    return [(r.file, r.line, r.target) for r in siblingcensus.reaches(ROOT, files)]


def _names(files: dict[str, str]) -> list[str]:
    return [r.target for r in siblingcensus.reaches(ROOT, files)]


def test_a_dotdot_that_stays_inside_the_repo_is_not_a_reach() -> None:
    """A distribution beside another under the one checkout is no sibling checkout."""
    files = {"pycodemod/pyproject.toml": 'mikemol-pathwalk = { path = "../pathwalk" }\n'}
    assert _targets(files) == []


def test_a_dotdot_that_lands_beside_the_repo_names_the_other_checkout() -> None:
    """From the repo root one step up is the github root, and the next word is another repo."""
    files = {
        "README.md": "see ../paperkit/docs\n",
        "a/b/c.py": "# ../../../life/x\n# ../../up\n",
    }
    assert _targets(files) == [("README.md", 1, "paperkit"), ("a/b/c.py", 1, "life")]


def test_the_home_forms_name_another_repo_unless_it_is_this_one() -> None:
    """Tilde, HOME and absolute spellings count for another repo and not for the repo itself."""
    text = (
        "a ~/github/nemik/x\n"
        "b $HOME/github/life\n"
        "c /home/mikemol/github/paperkit/y\n"
        "d ~/github/mtools/z\n"
    )
    assert _names({"notes.md": text}) == ["nemik", "life", "paperkit"]


def test_each_reach_carries_its_file_and_line_number() -> None:
    """Two lines in two files come back in file and line order."""
    files = {"b.py": "x\n~/github/nemik\n", "a.py": "~/github/life\n"}
    assert _targets(files) == [("a.py", 1, "life"), ("b.py", 2, "nemik")]


def test_the_command_counts_tracked_files_only_and_says_how_many_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An untracked file with a reach is not counted: the line reads N reach(es) in M file(s)."""
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    commit_kata.run_git_in(["init", "-q"], {}, repo)
    (repo / "kept.md").write_text("~/github/nemik\n~/github/life\n", encoding="utf-8")
    (repo / "loose.md").write_text("~/github/paperkit\n", encoding="utf-8")
    commit_kata.run_git_in(["add", "kept.md"], {}, repo)
    assert siblingcensus_cli.main([str(repo)]) == 0
    assert capsys.readouterr().out == "repo: 2 reach(es) in 1 file(s)\n"
    assert siblingcensus_cli.main([]) == siblingcensus_cli.EXIT_USAGE

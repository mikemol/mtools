# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-pycheck --changed`: changed files named from git, one exit for all."""

from __future__ import annotations

import io
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_census, pycheck_cli

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

GIT = shutil.which("git") or "git"


def _git(root: Path, *args: str) -> None:
    """Run one git command in `root`, failing the test if git refuses."""
    subprocess.run(
        [GIT, "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        check=True,
    )


def _repo(root: Path) -> None:
    """Build a repository with one committed file of each kind a status can name."""
    _git(root, "init", "-q")
    for name in ("a.py", "c.py", "e.py", "f.txt"):
        (root / name).write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")


def _verdict(code: int) -> Callable[[Path], int]:
    """Make a per-file checker that answers `code` for every file.

    Returns:
        the checker.

    """

    def check_one(path: Path) -> int:
        del path
        return code

    return check_one


def test_changed_python_names_modified_added_and_renamed_files_not_deleted_ones(
    tmp_path: Path,
) -> None:
    """Modified, untracked and renamed `.py` files are named; a deletion and a text file not."""
    _repo(tmp_path)
    (tmp_path / "a.py").write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 1\n", encoding="utf-8")
    (tmp_path / "f.txt").write_text("changed\n", encoding="utf-8")
    _git(tmp_path, "mv", "c.py", "d.py")
    _git(tmp_path, "rm", "-q", "e.py")
    assert pycheck_census.changed_python(tmp_path) == ["a.py", "b.py", "d.py"]


def test_a_clean_tree_has_no_changed_files_and_a_non_repository_is_none(tmp_path: Path) -> None:
    """Nothing changed is an empty list; git refusing is None, never the same thing."""
    assert pycheck_census.changed_python(tmp_path) is None
    _repo(tmp_path)
    assert pycheck_census.changed_python(tmp_path) == []


def test_a_refusal_outranks_not_checked_which_outranks_a_clean_run(tmp_path: Path) -> None:
    """The exit never softens: one refused file refuses the run; one unjudged never reads clean."""
    out, err = io.StringIO(), io.StringIO()
    names = ["a.py", "b.py"]
    changed = pycheck_cli.check_changed
    admitted = pycheck_cli.EXIT_ADMITTED
    refused = pycheck_cli.EXIT_REFUSED
    unjudged = pycheck_cli.EXIT_NOT_CHECKED
    assert changed(tmp_path, lambda _r: names, _verdict(admitted), out, err) == admitted
    assert changed(tmp_path, lambda _r: names, _verdict(refused), out, err) == refused
    assert changed(tmp_path, lambda _r: names, _verdict(unjudged), out, err) == unjudged


def test_no_changed_files_is_stated_and_git_failing_is_not_checked(tmp_path: Path) -> None:
    """An empty change set says so and exits zero; an unreadable one exits three on stderr."""
    out, err = io.StringIO(), io.StringIO()
    admitted = _verdict(pycheck_cli.EXIT_ADMITTED)
    assert pycheck_cli.check_changed(tmp_path, lambda _r: [], admitted, out, err) == 0
    assert "no changed Python files" in out.getvalue()
    code = pycheck_cli.check_changed(tmp_path, lambda _r: None, admitted, out, err)
    assert code == pycheck_cli.EXIT_NOT_CHECKED
    assert "not checked" in err.getvalue()

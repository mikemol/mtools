# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for W553: a linked worktree borrows its main tree's checkers, and only those.

Every repository here is a DECOY under decoy, and every GIT_* variable is removed first so
nothing inherited can point a probe at a real repository. The `.venv/bin/python3` planted is a tiny
shell script that records its working directory and argv, then exits clean.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import pycheck, worktree_venv

if TYPE_CHECKING:
    from pathlib import Path

_DIST = "dist"
_SOURCE = '"""Doc."""\n'


@pytest.fixture()
def decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Remove every GIT_* variable, switch git config off, and hand back tmp_path.

    Returns:
        the directory decoy repositories are built in.

    """
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return tmp_path


def _git(repo: Path, *args: str) -> None:
    """Run one git command in `repo`."""
    git = shutil.which("git")
    assert git is not None
    subprocess.run(
        [git, "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
    )


def _main(decoy: Path) -> Path:
    """Build a decoy repository with one committed distribution `dist/`.

    Returns:
        the main tree's root.

    """
    repo = decoy / "main"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    (repo / _DIST / "src").mkdir(parents=True)
    (repo / _DIST / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    return repo


def _worktree(decoy: Path, main: Path) -> Path:
    """Add a linked worktree of `main`.

    Returns:
        the worktree's root.

    """
    wt = decoy / "wt"
    _git(main, "worktree", "add", "--quiet", str(wt), "-b", "side")
    return wt


def _fake_venv(dist: Path, log: Path) -> Path:
    """Plant a fake interpreter under `dist/.venv/bin` that logs its cwd and argv.

    Returns:
        the fake interpreter's path.

    """
    py = dist / ".venv" / "bin" / "python3"
    py.parent.mkdir(parents=True)
    script = f'#!/bin/sh\nprintf "%s|%s\\n" "$PWD" "$*" >> "{log}"\nexit 0\n'
    py.write_text(script, encoding="utf-8")
    py.chmod(0o755)
    return py


def test_worktree_without_a_venv_borrows_the_main_trees(decoy: Path) -> None:
    """A linked worktree with no venv resolves the main tree's interpreter for that dist."""
    main = _main(decoy)
    wt = _worktree(decoy, main)
    planted = _fake_venv(main / _DIST, decoy / "log")
    assert worktree_venv.main_tree_venv_python(wt / _DIST) == planted


def test_borrowed_tools_still_read_the_worktrees_file_and_config(decoy: Path) -> None:
    """Both checkers run FROM the worktree dist, under its pyproject, on a file staged there."""
    main = _main(decoy)
    wt = _worktree(decoy, main)
    log = decoy / "log"
    _fake_venv(main / _DIST, log)
    target = wt / _DIST / "src" / "mod.py"
    assert pycheck.analyze(_SOURCE, str(target)) == (True, "")
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(["ruff", "ruff-format", "mypy"])
    for line in lines:
        cwd, argv = line.split("|", 1)
        assert cwd == str((wt / _DIST).resolve())
        assert str(main) not in argv.replace(str(wt), "")
        assert str(wt / _DIST / "pyproject.toml") in argv
    assert str(target) in lines[0]
    assert str(wt / _DIST) in lines[-1]


def test_neither_tree_having_a_venv_keeps_the_refusal(decoy: Path) -> None:
    """With no venv in the worktree or the main tree the existing refusal text stands."""
    main = _main(decoy)
    wt = _worktree(decoy, main)
    assert worktree_venv.main_tree_venv_python(wt / _DIST) is None
    verdict, why = pycheck.analyze(_SOURCE, str(wt / _DIST / "src" / "mod.py"))
    assert verdict is None
    assert "has no .venv/bin/python3 to run ruff and mypy from" in why


def test_a_worktrees_own_venv_wins(decoy: Path) -> None:
    """When the worktree has its own venv, it runs the checkers and the main tree's does not."""
    main = _main(decoy)
    wt = _worktree(decoy, main)
    main_log = decoy / "main.log"
    own_log = decoy / "own.log"
    _fake_venv(main / _DIST, main_log)
    _fake_venv(wt / _DIST, own_log)
    assert pycheck.analyze(_SOURCE, str(wt / _DIST / "src" / "mod.py")) == (True, "")
    assert own_log.exists()
    assert not main_log.exists()


def test_a_non_worktree_repository_behaves_as_before(decoy: Path) -> None:
    """In the main tree itself there is nothing to borrow: its own venv or the refusal."""
    main = _main(decoy)
    target = str(main / _DIST / "src" / "mod.py")
    assert worktree_venv.main_tree_venv_python(main / _DIST) is None
    verdict, why = pycheck.analyze(_SOURCE, target)
    assert verdict is None
    assert "has no .venv/bin/python3" in why
    log = decoy / "log"
    _fake_venv(main / _DIST, log)
    assert pycheck.analyze(_SOURCE, target) == (True, "")
    assert log.exists()


def test_a_directory_outside_any_repository_resolves_nothing(decoy: Path) -> None:
    """A plain directory, or a missing one, is not a worktree and yields None."""
    plain = decoy / "plain"
    plain.mkdir()
    assert worktree_venv.main_tree_venv_python(plain) is None
    assert worktree_venv.main_tree_venv_python(decoy / "absent") is None

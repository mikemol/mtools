# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The census names the Python files it does not measure, so zero never means unread (W1561).

⚑ REAL GIT ON A TEMP REPOSITORY, NO FAKE: the controls are the files the census cannot see, an
untracked source and a stub, beside one it can, and an ignored file that is nobody's business.
"""

from __future__ import annotations

import io
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import pycheck_census, pycheck_cli

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.hooks.verdict import Verdict

GIT = shutil.which("git") or "git"
IDENTITY = ["-c", "user.email=t@e.invalid", "-c", "user.name=t"]


def _git(root: Path, *args: str) -> None:
    subprocess.run([GIT, "-C", str(root), *IDENTITY, *args], capture_output=True, check=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    for name in ("a.py", "c.pyi", "data.txt"):
        (root / name).write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    for name in ("b.py", "ignored.py", "d.pyi"):
        (root / name).write_text("y = 2\n", encoding="utf-8")
    return root


def _clean(_path: str, _text: str) -> Verdict:
    return True, ""


def test_an_untracked_source_and_the_stubs_are_named_and_an_ignored_file_is_not(
    tmp_path: Path,
) -> None:
    """Tracked a.py is measured; b.py is untracked, both stubs are stubs; ignored.py is ignored."""
    root = _repo(tmp_path)
    assert pycheck_census.unmeasured(root) == ["b.py", "c.pyi", "d.pyi"]


def test_outside_a_repository_nothing_is_named(tmp_path: Path) -> None:
    """With no git to ask, the answer is empty and nothing raises."""
    assert pycheck_census.unmeasured(tmp_path) == []


def test_measure_says_what_it_did_not_look_at(tmp_path: Path) -> None:
    """The omission is on stderr beside the ledger, so a zero cannot read as clean."""
    root = _repo(tmp_path)
    err = io.StringIO()
    debt = pycheck_cli.measure(root, pycheck_census.tracked_python, _clean, err)
    assert debt == {}
    assert "3 untracked or stub files not in the census: b.py, c.pyi, d.pyi" in err.getvalue()


def test_a_tree_with_nothing_unmeasured_says_nothing(tmp_path: Path) -> None:
    """A clean tree adds no line: only the omission is reported."""
    root = tmp_path / "tidy"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", "-A")
    err = io.StringIO()
    pycheck_cli.measure(root, pycheck_census.tracked_python, _clean, err)
    assert "not in the census" not in err.getvalue()

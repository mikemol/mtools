# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for fix_owes_callers: callers of a changed def in files the change did not touch.

Every case runs git in a DECOY repository made under tmp_path, and every GIT_* variable is
removed first: a commit hook exports GIT_DIR and GIT_INDEX_FILE, which would point git at the
real repository.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import owes

if TYPE_CHECKING:
    from pathlib import Path

_FILES = {
    "store.py": "def load(x):\n    return x, x\n",
    "caller_a.py": "from store import load\na, b = load(1)\n",
    "caller_b.py": "from store import load\nc, d = load(2)\n",
    "handoff.py": "from store import load\nfns = sorted([1], key=load)\n",
}


def _git(root: Path, *args: str) -> None:
    git = shutil.which("git")
    assert git is not None
    subprocess.run(
        [git, "-c", "user.name=decoy", "-c", "user.email=decoy@invalid", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a fresh repository in tmp_path holding one def and three users, committed once.

    Returns:
        the repository root.

    """
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    for name, text in _FILES.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _paths(root: Path) -> list[str]:
    return [str(root / n) for n in sorted(_FILES)]


def _names(result: owes.Owes) -> list[tuple[str, int, str]]:
    return [(s.path.rsplit("/", 1)[-1], s.line, s.kind) for s in result.owed]


def _widen(root: Path) -> None:
    (root / "store.py").write_text("def load(x):\n    return x, x, x, x\n", encoding="utf-8")


def test_an_uncommitted_widening_owes_every_untouched_caller(decoy: Path) -> None:
    """Only the def file edited, WORKING: both callers and the key= handoff are owed.

    The import line is owed too: a name imported is a name used, and a rename breaks it.
    """
    _widen(decoy)
    got = owes.fix_owes_callers("load", owes.WORKING, _paths(decoy), str(decoy))
    assert _names(got) == [
        ("caller_a.py", 2, "call"),
        ("caller_a.py", 1, "ref"),
        ("caller_b.py", 2, "call"),
        ("caller_b.py", 1, "ref"),
        ("handoff.py", 1, "ref"),
        ("handoff.py", 2, "ref"),
    ]
    assert (got.defs, got.defs_changed, got.covered) == (1, 1, 0)


def test_a_caller_the_change_also_touched_is_covered_not_owed(decoy: Path) -> None:
    """The def and caller_a both edited: caller_a is counted as covered, never listed."""
    _widen(decoy)
    (decoy / "caller_a.py").write_text(
        "from store import load\na, b, c, d = load(1)\n", encoding="utf-8"
    )
    got = owes.fix_owes_callers("load", owes.WORKING, _paths(decoy), str(decoy))
    assert sorted({n for n, _l, _k in _names(got)}) == ["caller_b.py", "handoff.py"]
    assert got.covered == len(["import", "call"])


def test_a_committed_range_is_read_from_git(decoy: Path) -> None:
    """The widening committed, then asked for as HEAD~1: the same callers are owed."""
    _widen(decoy)
    _git(decoy, "commit", "-q", "-am", "widen")
    got = owes.fix_owes_callers("load", "HEAD~1", _paths(decoy), str(decoy))
    assert sorted({n for n, _l, _k in _names(got)}) == ["caller_a.py", "caller_b.py", "handoff.py"]
    assert got.change.desc == "git diff --name-only HEAD~1"


def test_a_change_without_the_def_has_no_referent(decoy: Path) -> None:
    """Only caller_a edited: no def of the name is in the change, and defs_changed says so."""
    (decoy / "caller_a.py").write_text("from store import load\nload(9)\n", encoding="utf-8")
    got = owes.fix_owes_callers("load", owes.WORKING, _paths(decoy), str(decoy))
    assert (got.defs, got.defs_changed) == (1, 0)


def test_a_bad_revision_raises_with_gits_words_not_an_empty_change(decoy: Path) -> None:
    """An unknown revision is git's refusal, raised; it never reads as a change that is clean."""
    with pytest.raises(owes.GitRefusedError, match="no-such-rev"):
        owes.changed_files("no-such-rev", str(decoy))


def test_a_revision_shaped_like_an_option_is_refused(decoy: Path) -> None:
    """A revision starting with a dash never reaches git, where it would be read as an option."""
    with pytest.raises(owes.GitRefusedError, match="as an option"):
        owes.changed_files("--output=x", str(decoy))
    assert not (decoy / "x").exists()


def test_a_clean_tree_is_an_empty_change_not_a_refusal(decoy: Path) -> None:
    """Nothing edited, WORKING: the change is empty, and no refusal is raised."""
    got = owes.changed_files(owes.WORKING, str(decoy))
    assert got.files == frozenset()

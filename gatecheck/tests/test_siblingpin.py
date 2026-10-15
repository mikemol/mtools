# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a sibling checkout is judged by its own HEAD and tree, and only those.

W1018. ⚑ THE REAL GIT IS THE CONTROL for the one thing a fake cannot show: with `GIT_DIR`,
`GIT_WORK_TREE` and `GIT_INDEX_FILE` pointing at ANOTHER repository (as inside the isolated hook),
the answer is still about the sibling. ⚑ THE REFUSALS: a relative root, a malformed sha, a
directory that is no checkout, a different HEAD and a dirty tree each fail with their own reason.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.gatecheck import siblingpin

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

_USAGE = 2
_GIT = shutil.which("git") or "git"
_FAKE_ROOT = Path("/x")


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        [_GIT, "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _repo(path: Path) -> str:
    path.mkdir()
    _git(path, "init", "--quiet", "-b", "main")
    (path / "a.txt").write_text("a\n", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "--quiet", "-m", "one")
    return _git(path, "rev-parse", "HEAD")


def _fake(head: str = "abc1234def", changes: str = "") -> siblingpin.Runner:
    def run(argv: Sequence[str], _root: Path) -> tuple[int, str]:
        return (0, head) if argv[0] == "rev-parse" else (0, changes)

    return run


def test_the_three_git_variables_are_removed_and_the_rest_kept() -> None:
    """GIT_DIR, GIT_WORK_TREE and GIT_INDEX_FILE go; PATH and a lookalike stay."""
    base = {
        "GIT_DIR": "/x",
        "GIT_WORK_TREE": "/y",
        "GIT_INDEX_FILE": "/z",
        "GIT_AUTHOR_NAME": "n",
        "PATH": "/bin",
    }
    assert siblingpin.clean_env(base) == {"GIT_AUTHOR_NAME": "n", "PATH": "/bin"}


def test_a_sibling_at_the_sha_and_clean_is_ok(tmp_path: Path) -> None:
    """The real git agrees: HEAD matches (full and abbreviated) and nothing is modified."""
    sibling = tmp_path / "sibling"
    sha = _repo(sibling)
    full = siblingpin.check(sibling, sha)
    assert (full.ok, full.clean, full.head, full.reason) == (True, True, sha, "")
    assert siblingpin.check(sibling, sha[:8]).ok


def test_a_different_head_and_a_dirty_tree_each_fail_with_their_own_reason(tmp_path: Path) -> None:
    """Another sha is 'not the recorded sha'; an edited tracked file is 'uncommitted changes'."""
    sibling = tmp_path / "sibling"
    sha = _repo(sibling)
    assert siblingpin.check(sibling, "0" * 40).reason == "HEAD is not the recorded sha"
    (sibling / "a.txt").write_text("edited\n", encoding="utf-8")
    dirty = siblingpin.check(sibling, sha)
    assert (dirty.ok, dirty.clean, dirty.reason) == (False, False, "uncommitted changes")


def test_the_committing_repositorys_git_variables_do_not_answer_for_the_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: GIT_DIR names another repo, yet the verdict is about the sibling's own HEAD."""
    sibling, other = tmp_path / "sibling", tmp_path / "other"
    sha = _repo(sibling)
    other.mkdir()
    _git(other, "init", "--quiet", "-b", "main")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / ".git" / "index"))
    assert siblingpin.check(sibling, sha).ok


def test_a_relative_root_a_bad_sha_and_a_non_checkout_are_refused(tmp_path: Path) -> None:
    """Each is refused before or by git, with a reason that names it."""
    assert "absolute" in siblingpin.check(Path("relative/dir"), "abc1234").reason
    assert "7 to 40" in siblingpin.check(tmp_path, "XYZ").reason
    assert "not a checkout" in siblingpin.check(tmp_path / "no", "abc1234").reason


def test_a_failing_status_is_a_refusal_not_a_pass() -> None:
    """The runner answers HEAD but fails `status`: the verdict is not ok and says why."""

    def run(argv: Sequence[str], _root: Path) -> tuple[int, str]:
        return (0, "abc1234def") if argv[0] == "rev-parse" else (128, "boom")

    verdict = siblingpin.check(_FAKE_ROOT, "abc1234", run)
    assert (verdict.ok, verdict.reason) == (False, "git status failed: boom")
    assert siblingpin.check(_FAKE_ROOT, "abc1234", _fake()).ok


def test_the_command_prints_one_json_line_and_exits_by_the_verdict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 0 and ok true at the sha; exit 1 and ok false elsewhere; 2 for the wrong arguments."""
    sibling = tmp_path / "sibling"
    sha = _repo(sibling)
    assert siblingpin.main([str(sibling), sha]) == 0
    assert cast("dict[str, object]", json.loads(capsys.readouterr().out))["ok"] is True
    assert siblingpin.main([str(sibling), "0" * 40]) == 1
    assert cast("dict[str, object]", json.loads(capsys.readouterr().out))["ok"] is False
    assert siblingpin.main([str(sibling)]) == _USAGE

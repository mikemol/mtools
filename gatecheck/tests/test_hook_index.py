# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `hook_index`: a refusal names the divergent paths, before any build cost.

Every git case runs in a DECOY repository made under tmp_path, with every GIT_* variable removed
and global/system git config off: a commit hook exports GIT_DIR and GIT_INDEX_FILE, which would
point git at the real repository.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.gatecheck import hook_index

if TYPE_CHECKING:
    from pathlib import Path


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
    """Build a repository in tmp_path with one committed file, and make it the cwd.

    Returns:
        the repository root.

    """
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.delenv("PK_HOOK_ALLOW_DIRTY", raising=False)
    (tmp_path / "base.py").write_text("X = 1\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _fake(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_git_status_reads_the_live_porcelain_of_the_cwd(decoy: Path) -> None:
    """The default seam runs `git status --porcelain=v1 -z` where the process stands."""
    assert not hook_index.git_status().stdout
    (decoy / "new.py").write_text("Y = 2\n", encoding="utf-8")
    proc = hook_index.git_status()
    assert proc.returncode == 0
    assert proc.stdout == "?? new.py\0"


def test_a_clean_tree_is_equivalent_and_passes(
    decoy: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing diverges: exit 0 and the hook's verdict is declared the commit's."""
    assert decoy.is_dir()
    assert hook_index.main() == 0
    captured = capsys.readouterr()
    assert "worktree ≡ index" in captured.out
    assert not captured.err


def test_an_untracked_and_an_unstaged_path_are_refused_by_name(
    decoy: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both dirt kinds make exit 1, each path is named, and both remedies are stated."""
    (decoy / "untracked.py").write_text("Z = 3\n", encoding="utf-8")
    (decoy / "base.py").write_text("X = 2\n", encoding="utf-8")
    assert hook_index.main() == 1
    err = capsys.readouterr().err
    assert "hook-index: REFUSED" in err
    assert "  base.py\n" in err
    assert "  untracked.py\n" in err
    assert "git add <path>" in err
    assert "PK_HOOK_ALLOW_DIRTY=1" in err


def test_a_staged_change_is_not_a_divergence(
    decoy: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A change staged in full leaves worktree == index, so the hook passes."""
    (decoy / "base.py").write_text("X = 2\n", encoding="utf-8")
    _git(decoy, "add", "base.py")
    assert hook_index.main() == 0
    assert "worktree ≡ index" in capsys.readouterr().out


def test_allow_dirty_downgrades_the_refusal_to_an_advisory(
    decoy: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`PK_HOOK_ALLOW_DIRTY=1`: exit 0, still names the paths, no remedy line."""
    (decoy / "untracked.py").write_text("Z = 3\n", encoding="utf-8")
    monkeypatch.setenv("PK_HOOK_ALLOW_DIRTY", "1")
    assert hook_index.main() == 0
    err = capsys.readouterr().err
    assert "hook-index: ADVISORY" in err
    assert "  untracked.py\n" in err
    assert "git add" not in err


def test_only_the_value_one_selects_the_advisory(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Any other value of the variable is still a refusal."""
    monkeypatch.setenv("PK_HOOK_ALLOW_DIRTY", "yes")
    assert hook_index.main(status=lambda: _fake(0, "?? x.py\0")) == 1
    assert "hook-index: REFUSED" in capsys.readouterr().err


def test_a_failing_git_status_is_reported_and_refuses(capsys: pytest.CaptureFixture[str]) -> None:
    """A non-zero `git status` exits 1 and quotes git's own stderr."""
    assert hook_index.main(status=lambda: _fake(128, stderr="fatal: not a repo\n")) == 1
    assert "git status failed — fatal: not a repo" in capsys.readouterr().err


def _always_clean(_porcelain: str, _allow: tuple[str, ...] = ()) -> list[str]:
    return []


def test_an_unsound_parser_refuses_before_reading_git(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A parser that cannot refuse the synthetic dirty line is theater: exit 1, git untouched."""
    monkeypatch.setattr(hook_index, "divergent", _always_clean)
    asked: list[str] = []

    def spy() -> subprocess.CompletedProcess[str]:
        asked.append("git")
        return _fake(0)

    assert hook_index.main(status=spy) == 1
    assert "SELF-PROOF FAIL" in capsys.readouterr().err
    assert not asked


_REFUSED = 2


def test_an_argument_is_refused_by_name_before_git_is_read(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Any argument exits 2 naming it, and git is never asked: a dropped flag reads as a pass.

    ⚑ el-openglo:W99 measured the installed hook commands ignoring argv, so `--help` exited 0 with
    no output. paperkit's `hook_index` ignored it too; this one refuses.
    """

    def spy() -> subprocess.CompletedProcess[str]:
        msg = "git was read before the argument was refused"
        raise AssertionError(msg)

    assert hook_index.main(["--help"], status=spy) == _REFUSED
    assert "'--help'" in capsys.readouterr().err


def test_the_console_entry_hands_main_the_real_argv(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`cli` passes `sys.argv[1:]` to `main`, so a flag on the command line is refused."""
    monkeypatch.setattr("sys.argv", ["mikemol-hook-index", "--allow-dirty"])
    assert hook_index.cli() == _REFUSED
    assert "'--allow-dirty'" in capsys.readouterr().err

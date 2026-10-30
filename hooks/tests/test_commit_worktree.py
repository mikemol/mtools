# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit` refuses a stack from a linked worktree and marks the main repository (W2103).

⚑ THE LEDGER IS `<git dir>/mtools`: a worktree's is `<main>/.git/worktrees/<name>/mtools`, the
shape github-8f measured when a worktree submit took a second queue and lease.
"""

from pathlib import Path

import pytest

from mikemol.hooks import commit_kata, worktree_submit


def test_a_worktree_ledger_is_refused_on_stderr_and_marked_in_the_main_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal names W2103 and the main log gets one `refused` line."""
    main = tmp_path / "repo" / ".git"
    worktree = main / "worktrees" / "toy-W2"
    assert commit_kata.worktree_refused(tmp_path / "toy-W2", worktree / "mtools")
    assert "W2103" in capsys.readouterr().err
    log = (main / "mtools" / worktree_submit.LOG_NAME).read_text(encoding="utf-8")
    assert log.endswith(f" refused toy-W2 {worktree}\n")


def test_a_stack_from_a_worktree_is_refused_before_its_file_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stack path returns the usage exit for a worktree even when the stack file is absent."""
    main = tmp_path / "repo" / ".git"
    ledger = main / "worktrees" / "toy-W2" / "mtools"

    def named(root: Path) -> Path:
        return ledger / root.name.replace(root.name, "")

    monkeypatch.setattr(commit_kata, "ledger_of", named)
    stacked = (tmp_path / "toy-W2", tmp_path / "missing.json")
    assert commit_kata.unreadable_stack(stacked) == commit_kata.EXIT_USAGE
    assert (main / "mtools" / worktree_submit.LOG_NAME).exists()


def test_a_main_checkout_and_an_unnamed_git_dir_are_not_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A main checkout's ledger, or none at all, passes and writes nothing."""
    main = tmp_path / "repo" / ".git"
    assert not commit_kata.worktree_refused(tmp_path / "repo", main / "mtools")
    assert not commit_kata.worktree_refused(tmp_path / "repo", None)
    assert not capsys.readouterr().err
    assert not (main / "mtools").exists()

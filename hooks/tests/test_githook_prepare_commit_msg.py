# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the shared git prepare-commit-msg, run against a DECOY repository in tmp_path.

The shell hook (substrate's `.githooks/prepare-commit-msg`) is the specification. ⚑ Every GIT_*
variable is removed first, so nothing inherited can point a probe at a real repository, and
GIT_CEILING_DIRECTORIES stops a non-repository probe from discovering one above tmp_path. Git's
argv (`<message-file> <source>`) is the contract, so the tests pass it to `main` directly.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks.githook_prepare_commit_msg import (
    MARKER,
    REPORT_NAME,
    GitUnavailableError,
    HookError,
    folded,
    main,
    prepare,
    report_path,
    run_git,
)

if TYPE_CHECKING:
    from pathlib import Path

_REPORT = "[1/3] Building //a\n\ngate: ok\n   \n[22/30] Linking b\n  detail line\n"
_FOLDED = f"\n{MARKER}:\n    gate: ok\n      detail line\n"


def _g(*args: str) -> str:
    """Run the real git (resolved, not by partial path) and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    return subprocess.run([git, *args], check=True, capture_output=True, text=True).stdout


def _clean_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove inherited GIT_* variables and fence repository discovery at tmp_path."""
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))


def _decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build an empty decoy repository and work inside it.

    Returns:
        the repository's root.

    """
    _clean_env(tmp_path, monkeypatch)
    repo = tmp_path / "decoy"
    repo.mkdir()
    monkeypatch.chdir(repo)
    _g("init", "--quiet")
    return repo


def _with_report(repo: Path, text: str = _REPORT) -> Path:
    """Write the pre-commit report into the decoy's git dir.

    Returns:
        the report's path.

    """
    report = repo / ".git" / REPORT_NAME
    report.write_text(text, encoding="utf-8")
    return report


def _msg(repo: Path, text: str = "subject\n") -> Path:
    """Write a commit message file.

    Returns:
        the message file's path.

    """
    path = repo / "COMMIT_EDITMSG"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("source", ["message", "template", "commit", ""])
def test_a_source_that_is_not_merge_or_squash_gets_the_report_folded_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """For message, template, commit and no source, the filtered report is appended, consumed."""
    repo = _decoy(tmp_path, monkeypatch)
    report = _with_report(repo)
    message = _msg(repo)
    assert main([str(message), source] if source else [str(message)]) == 0
    assert message.read_text(encoding="utf-8") == "subject\n" + _FOLDED
    assert not report.exists()


@pytest.mark.parametrize("source", ["merge", "squash"])
def test_a_merge_or_squash_message_is_left_alone_and_the_report_consumed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """Auto-generated merge and squash messages are not cluttered; the report is deleted."""
    repo = _decoy(tmp_path, monkeypatch)
    report = _with_report(repo)
    message = _msg(repo)
    assert main([str(message), source]) == 0
    assert message.read_text(encoding="utf-8") == "subject\n"
    assert not report.exists()


def test_no_report_is_a_quiet_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A commit that wrote no report (e.g. --no-verify) leaves the message and stderr untouched."""
    repo = _decoy(tmp_path, monkeypatch)
    message = _msg(repo)
    assert main([str(message), "message"]) == 0
    assert message.read_text(encoding="utf-8") == "subject\n"
    assert not capsys.readouterr().err


def test_a_message_already_carrying_the_marker_is_not_folded_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A manual --amend keeps its marker block: nothing is appended and the report is consumed."""
    repo = _decoy(tmp_path, monkeypatch)
    report = _with_report(repo)
    once = f"subject\n\n{MARKER}:\n    old\n"
    message = _msg(repo, once)
    assert main([str(message), "commit"]) == 0
    assert message.read_text(encoding="utf-8") == once
    assert not report.exists()


def test_a_second_run_does_not_append_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The report is one-shot: after one fold, a rerun finds none and changes nothing."""
    repo = _decoy(tmp_path, monkeypatch)
    _with_report(repo)
    message = _msg(repo)
    assert main([str(message), "message"]) == 0
    once = message.read_text(encoding="utf-8")
    assert main([str(message), "message"]) == 0
    assert message.read_text(encoding="utf-8") == once
    assert once.count(MARKER) == 1


def test_a_missing_message_file_is_reported_and_the_report_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shell `>>` swallowed this and still deleted the report; here: stderr, exit 1, kept."""
    repo = _decoy(tmp_path, monkeypatch)
    report = _with_report(repo)
    assert main([str(repo / "no-such-dir" / "MSG"), "message"]) == 1
    assert "cannot read the message" in capsys.readouterr().err
    assert report.exists()


def test_an_unwritable_message_file_is_reported_and_the_report_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A read-only message file: the append fails loudly, and the report is not lost."""
    repo = _decoy(tmp_path, monkeypatch)
    report = _with_report(repo)
    message = _msg(repo)
    message.chmod(0o444)
    assert main([str(message), "message"]) == 1
    assert "cannot append to" in capsys.readouterr().err
    assert report.exists()
    assert message.read_text(encoding="utf-8") == "subject\n"


def test_no_message_argument_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shell version exited 0 on an empty argument; here it is reported with exit 1."""
    _decoy(tmp_path, monkeypatch)
    assert main([]) == 1
    assert "usage" in capsys.readouterr().err
    assert main([""]) == 1


def test_main_reads_git_argv_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no argv given, main reads sys.argv[1:], which is how git calls the console script."""
    repo = _decoy(tmp_path, monkeypatch)
    _with_report(repo)
    message = _msg(repo)
    monkeypatch.setattr("sys.argv", ["hook", str(message), "message"])
    assert main() == 0
    assert MARKER in message.read_text(encoding="utf-8")
    assert not capsys.readouterr().err


def test_outside_a_repository_is_reported_not_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shell version built the path `/precommit-report.txt` and exited 0; here: exit 1."""
    _clean_env(tmp_path, monkeypatch)
    bare = tmp_path / "not-a-repo"
    bare.mkdir()
    monkeypatch.chdir(bare)
    message = bare / "MSG"
    message.write_text("subject\n", encoding="utf-8")
    assert main([str(message), "message"]) == 1
    assert "cannot name the git dir" in capsys.readouterr().err
    assert message.read_text(encoding="utf-8") == "subject\n"


def test_no_git_on_path_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without git on PATH, main exits 1 and says why, rather than skipping silently."""
    repo = _decoy(tmp_path, monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert main([str(_msg(repo)), "message"]) == 1
    assert "no git on PATH" in capsys.readouterr().err


def test_run_git_returns_a_result_and_raises_without_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The run_git helper returns the result whatever its status, and raises without git."""
    _decoy(tmp_path, monkeypatch)
    assert run_git("rev-parse", "--git-dir").returncode == 0
    assert run_git("no-such-subcommand").returncode != 0
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(GitUnavailableError):
        run_git("rev-parse", "--git-dir")


def test_report_path_is_in_the_absolute_git_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The report_path helper names the report under the git dir, and raises outside a repo."""
    repo = _decoy(tmp_path, monkeypatch)
    assert report_path() == (repo / ".git").resolve() / REPORT_NAME
    bare = tmp_path / "not-a-repo"
    bare.mkdir()
    monkeypatch.chdir(bare)
    with pytest.raises(HookError):
        report_path()


def test_folded_drops_progress_and_blank_lines_and_indents() -> None:
    """The block is a blank line, the marker, then the kept report lines indented four spaces."""
    assert folded(_REPORT) == _FOLDED
    assert folded("") == f"\n{MARKER}:\n"


def test_prepare_folds_the_report_into_the_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The prepare function is the hook minus argv: it appends the block, consumes the report."""
    repo = _decoy(tmp_path, monkeypatch)
    report = _with_report(repo)
    message = _msg(repo)
    prepare(message, "message")
    assert message.read_text(encoding="utf-8") == "subject\n" + _FOLDED
    assert not report.exists()


def test_prepare_raises_for_a_report_that_cannot_be_consumed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report in a read-only git dir cannot be deleted: the failure is raised, not swallowed."""
    repo = _decoy(tmp_path, monkeypatch)
    _with_report(repo)
    message = _msg(repo)
    git_dir = repo / ".git"
    git_dir.chmod(0o555)
    try:
        with pytest.raises(HookError, match="cannot delete"):
            prepare(message, "merge")
    finally:
        git_dir.chmod(0o755)

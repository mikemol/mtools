# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the shared git post-commit, run against a DECOY repository in tmp_path.

The shell hook (substrate's `.githooks/post-commit`) is the specification. ⚑ Every GIT_* variable
is removed first, so nothing inherited can point a probe at a real repository, and
GIT_CEILING_DIRECTORIES stops a non-repository probe from discovering one above tmp_path.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks.githook_post_commit import (
    GUARD,
    HEADER,
    MARKER,
    GitUnavailableError,
    advisory,
    folded,
    in_flight,
    main,
    run_git,
)

if TYPE_CHECKING:
    from pathlib import Path


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
    monkeypatch.delenv(GUARD, raising=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))


def _decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a decoy repository holding one commit, and work inside it.

    Returns:
        the repository's root.

    """
    _clean_env(tmp_path, monkeypatch)
    repo = tmp_path / "decoy"
    repo.mkdir()
    monkeypatch.chdir(repo)
    _g("init", "--quiet")
    _g("config", "user.name", "Decoy")
    _g("config", "user.email", "decoy@example.invalid")
    _g("commit", "--quiet", "--allow-empty", "-m", "first")
    return repo


def _message() -> str:
    """Read the tip's commit message in the current directory.

    Returns:
        the message.

    """
    return _g("log", "-1", "--format=%B")


def _local(repo: Path, body: str, *, executable: bool = True) -> None:
    """Write the repo's post-commit.local."""
    (repo / ".githooks").mkdir(exist_ok=True)
    hook = repo / ".githooks" / "post-commit.local"
    hook.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    hook.chmod(0o755 if executable else 0o644)


def test_a_commit_gains_the_marker_and_the_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """After a commit, main amends the tip so its message carries the marker, and prints it."""
    _decoy(tmp_path, monkeypatch)
    assert main() == 0
    message = _message()
    assert message.startswith("first\n")
    assert f"{MARKER}:\n    {HEADER}" in message
    assert HEADER in capsys.readouterr().out


def test_the_local_hooks_output_is_folded_into_the_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """post-commit.local's stdout becomes the advisory body beneath the marker."""
    repo = _decoy(tmp_path, monkeypatch)
    _local(repo, "echo grounding: 3 findings\n")
    assert main() == 0
    assert "    grounding: 3 findings" in _message()


def test_a_failing_local_hook_is_recorded_not_hidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A post-commit.local that exits 4 still gets the marker, and the advisory says it failed."""
    repo = _decoy(tmp_path, monkeypatch)
    _local(repo, "echo partial\nexit 4\n")
    assert main() == 0
    message = _message()
    assert "    partial" in message
    assert "post-commit.local FAILED (exit 4)" in message


def test_a_second_run_does_not_append_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Idempotent: a tip that already carries the marker is left alone."""
    _decoy(tmp_path, monkeypatch)
    assert main() == 0
    once = _message()
    assert main() == 0
    assert _message() == once
    assert once.count(MARKER) == 1


def test_an_operation_in_flight_prints_but_does_not_amend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With MERGE_HEAD present, the advisory prints and the commit is not rewritten."""
    repo = _decoy(tmp_path, monkeypatch)
    (repo / ".git" / "MERGE_HEAD").write_text("0" * 40 + "\n", encoding="utf-8")
    assert main() == 0
    assert MARKER not in _message()
    assert HEADER in capsys.readouterr().out


def test_the_amends_own_refire_does_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With the guard variable set, main prints nothing and writes nothing."""
    _decoy(tmp_path, monkeypatch)
    monkeypatch.setenv(GUARD, "1")
    assert main() == 0
    assert MARKER not in _message()
    assert not capsys.readouterr().out


def test_outside_a_repository_nothing_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Not in a repository: exit 1, the reason on stderr, nothing on stdout, no file created."""
    _clean_env(tmp_path, monkeypatch)
    bare = tmp_path / "not-a-repo"
    bare.mkdir()
    monkeypatch.chdir(bare)
    assert main() == 1
    seen = capsys.readouterr()
    assert "not in a git repository" in seen.err
    assert not seen.out
    assert not list(bare.iterdir())


def test_a_failed_amend_is_reported_not_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An index.lock makes git refuse the amend: exit 1, the failure on stderr, no marker."""
    repo = _decoy(tmp_path, monkeypatch)
    (repo / ".git" / "index.lock").touch()
    assert main() == 1
    assert "amend FAILED" in capsys.readouterr().err
    assert MARKER not in _message()


def test_no_git_on_path_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without git on PATH, main exits 1 and says why, rather than skipping silently."""
    _decoy(tmp_path, monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert main() == 1
    assert "no git on PATH" in capsys.readouterr().err


def test_run_git_returns_a_result_and_raises_without_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_git returns the result whatever its status, and raises when git is absent."""
    _decoy(tmp_path, monkeypatch)
    assert run_git("rev-parse", "--git-dir").returncode == 0
    assert run_git("no-such-subcommand").returncode != 0
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(GitUnavailableError):
        run_git("rev-parse", "--git-dir")


def test_the_hook_never_pushes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With a remote configured, a post-commit run leaves the remote without any ref."""
    _decoy(tmp_path, monkeypatch)
    remote = tmp_path / "remote.git"
    _g("init", "--quiet", "--bare", str(remote))
    _g("remote", "add", "origin", str(remote))
    assert main() == 0
    assert not _g("-C", str(remote), "for-each-ref")
    assert MARKER in _message()


def test_in_flight_names_the_first_marker(tmp_path: Path) -> None:
    """in_flight is None for a clean git dir and names a present marker otherwise."""
    assert in_flight(tmp_path) is None
    (tmp_path / "REVERT_HEAD").touch()
    assert in_flight(tmp_path) == "REVERT_HEAD"


def test_index_lock_is_not_an_in_flight_marker(tmp_path: Path) -> None:
    """Unlike pre-push, post-commit does not treat index.lock as in flight (the shell did not)."""
    (tmp_path / "index.lock").touch()
    assert in_flight(tmp_path) is None


def test_advisory_is_the_header_alone_without_a_local_hook(tmp_path: Path) -> None:
    """With no post-commit.local, or a non-executable one, the advisory is just the header."""
    assert advisory(tmp_path) == HEADER
    _local(tmp_path, "echo ignored\n", executable=False)
    assert advisory(tmp_path) == HEADER


def test_advisory_appends_the_local_hooks_stdout(tmp_path: Path) -> None:
    """An executable post-commit.local's stdout follows the header, trailing newlines trimmed."""
    _local(tmp_path, "printf 'one\\ntwo\\n\\n'\n")
    assert advisory(tmp_path) == f"{HEADER}\none\ntwo"


def test_folded_indents_the_advisory_under_the_marker() -> None:
    """The marker follows the message after a blank line, and each advisory line is indented."""
    assert folded("subject\n\n", "a\nb") == f"subject\n\n{MARKER}:\n    a\n    b\n"

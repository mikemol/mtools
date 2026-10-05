# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the shared git pre-push, run against a DECOY repository in tmp_path.

These are githooks_test.sh's five arms, ported: the shell hook (521d77c) is the specification.
⚑ Every GIT_* variable is removed first, so nothing inherited can point a probe at a real
repository (a probe once aimed GIT_DIR at the real repo and made nine junk commits).
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks.githook_pre_push import main

if TYPE_CHECKING:
    import pytest

_REPO_STUB = Path(__file__).parent.parent.parent / ".githooks" / "pre-push"
_REFS = (
    b"refs/heads/main 1111111111111111111111111111111111111111 "
    b"refs/heads/main 0000000000000000000000000000000000000000\n"
)
_ARGS = ["origin", "url"]


def _decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build an empty decoy repository with a .githooks directory, and work inside it.

    Returns:
        the repository's root.

    """
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    git = shutil.which("git")
    assert git is not None
    repo = tmp_path / "decoy"
    subprocess.run([git, "init", "--quiet", str(repo)], check=True)
    (repo / ".githooks").mkdir()
    monkeypatch.chdir(repo)
    return repo


def _local(repo: Path, body: str, *, executable: bool = True) -> None:
    """Write the repo's pre-push.local."""
    hook = repo / ".githooks" / "pre-push.local"
    hook.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    hook.chmod(0o755 if executable else 0o644)


def test_without_a_local_hook_a_clean_repo_pushes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no pre-push.local, the shared checks alone decide, and a clean repo may push."""
    _decoy(tmp_path, monkeypatch)
    assert main(_ARGS, refs=io.BytesIO(_REFS)) == 0


def test_the_local_hook_gets_the_same_stdin_and_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The local hook receives git's ref list byte for byte, and git's arguments.

    ⚑ Git sends the ref list once; a shared check that consumed it would hand the local hook an
    empty list, and a hook looping over refs would then check nothing and pass.
    """
    repo = _decoy(tmp_path, monkeypatch)
    seen = tmp_path / "seen"
    _local(repo, f'cat >"{seen}.stdin"\nprintf "%s\\n" "$@" >"{seen}.args"\n')
    assert main(_ARGS, refs=io.BytesIO(_REFS)) == 0
    assert (tmp_path / "seen.stdin").read_bytes() == _REFS
    assert (tmp_path / "seen.args").read_text(encoding="utf-8").split() == _ARGS


def test_a_failing_local_hook_refuses_the_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-push.local that exits non-zero refuses the push."""
    _local(_decoy(tmp_path, monkeypatch), "exit 7\n")
    assert main(_ARGS, refs=io.BytesIO(_REFS)) == 1


def test_a_non_executable_local_hook_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-push.local without the executable bit is not run, even one that would fail."""
    _local(_decoy(tmp_path, monkeypatch), "exit 7\n", executable=False)
    assert main(_ARGS, refs=io.BytesIO(_REFS)) == 0


def test_an_operation_in_flight_refuses_before_the_local_hook_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """index.lock refuses the push, and the local hook is never reached."""
    repo = _decoy(tmp_path, monkeypatch)
    ran = tmp_path / "ran"
    _local(repo, f'touch "{ran}"\n')
    (repo / ".git" / "index.lock").touch()
    assert main(_ARGS, refs=io.BytesIO(_REFS)) == 1
    assert not ran.exists()


_LAUNCHER_EXIT = 7


def _run_stub(repo: Path, stdin: bytes) -> subprocess.CompletedProcess[bytes]:
    """Run this repository's `.githooks/pre-push` stub from inside a decoy repository.

    Returns:
        the finished process, its streams captured.

    """
    bash = shutil.which("bash")
    assert bash is not None
    return subprocess.run(
        [bash, str(_REPO_STUB), *_ARGS], input=stdin, cwd=repo, capture_output=True, check=False
    )


def test_the_repo_stub_hands_the_launcher_its_arguments_and_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W588: the stub execs the venv launcher with git's arguments and ref list; its exit stands.

    ⚑ A stub that dropped `"$@"` or read stdin itself would hand the launcher an empty ref list,
    and a hook looping over refs would then check nothing and pass.
    """
    repo = _decoy(tmp_path, monkeypatch)
    launcher = repo / "hooks" / ".venv" / "bin" / "mikemol-githook-pre-push"
    launcher.parent.mkdir(parents=True)
    seen = tmp_path / "seen"
    launcher.write_text(
        f'#!/usr/bin/env bash\ncat >"{seen}.stdin"\nprintf "%s\\n" "$@" >"{seen}.args"\n'
        f"exit {_LAUNCHER_EXIT}\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    done = _run_stub(repo, _REFS)
    assert done.returncode == _LAUNCHER_EXIT
    assert (tmp_path / "seen.stdin").read_bytes() == _REFS
    assert (tmp_path / "seen.args").read_text(encoding="utf-8").split() == _ARGS


def test_the_repo_stub_refuses_when_its_launcher_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W588: with no venv launcher the push is refused and the message names the missing file.

    ⚑ A stub that skipped on an absent checker would be armed while refusing nothing.
    """
    repo = _decoy(tmp_path, monkeypatch)
    done = _run_stub(repo, _REFS)
    assert done.returncode == 1
    assert b"mikemol-githook-pre-push is missing or not executable" in done.stderr
    assert b"push refused" in done.stderr

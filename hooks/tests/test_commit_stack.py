# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `mikemol-commit REPO --stack FILE` lands a stack through its real entry point.

W1164. ⚑ THE ENTRY POINT IS THE UNDER-TEST: `commit_kata.main` is called with the argument form, so
the parse, the routing line, the isolation check and the verdict lines are all read from what it
prints. ⚑ THE PLAIN-PATH REFUSAL IS THE CONTROL: the same stack, with isolation opted out, must
land nothing and say why, not fall back to some other way of committing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks.snapshot import NAMESPACE_ENV

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_EXECUTABLE = 0o755
_PASSING = '#!/bin/sh\necho run >> "$MIKEMOL_REAL_ROOT/runs"\n'
_PUSH = "#!/bin/sh\ngit push origin HEAD:main\n"


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated: str) -> tuple[Path, Path]:
    """Build a pushed repository, a stack file for a.txt and b.txt, and the environment for main.

    Returns:
        the working repository's root and the stack file's path.

    """
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
        NAMESPACE_ENV: str(tmp_path / "gate"),
        ck.HELD_ENV: "1",
        ck.ISOLATED_ENV: isolated,
    }.items():
        monkeypatch.setenv(key, value)
    remote = tmp_path / "origin.git"
    remote.mkdir()
    _git(remote, "init", "--quiet", "--bare", "-b", "main")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    for name in ("a.txt", "b.txt"):
        (root / name).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "--quiet", "origin", "HEAD:main")
    for hook_name, text in (("pre-commit", _PASSING), ("post-commit", _PUSH)):
        hook = root / ".git" / "hooks" / hook_name
        hook.write_text(text, encoding="utf-8")
        hook.chmod(_EXECUTABLE)
    (root / "a.txt").write_text("edited a\n", encoding="utf-8")
    (root / "b.txt").write_text("edited b\n", encoding="utf-8")
    stack = tmp_path / "stack.json"
    entries = [
        {"waypoint": "W1", "subject": "first card", "paths": ["a.txt"]},
        {"waypoint": "W2", "subject": "second card", "body": "why", "paths": ["b.txt"]},
    ]
    stack.write_text(json.dumps(entries), encoding="utf-8")
    return root, stack


def test_main_lands_a_stack_with_the_routing_line_and_a_verdict_per_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 0, the routing line names the isolated path, two COMMITTED lines, trailers on both."""
    root, stack = _repo(tmp_path, monkeypatch, "1")
    assert ck.main([str(root), "--stack", str(stack)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert any(line.startswith("mikemol-commit: path: isolated") for line in lines)
    verdicts = [line for line in lines if line.startswith("COMMITTED")]
    assert len(verdicts) == len(("first", "second"))
    assert verdicts[0].endswith("first card [PUSHED]")
    assert verdicts[1].endswith("second card [PUSHED]")
    assert "Waypoint: W2" in _git(root, "log", "-1", "--format=%B")
    assert "Waypoint: W1" in _git(root, "log", "-1", "--format=%B", "HEAD^")
    assert (root / "runs").read_text(encoding="utf-8") == "run\n"


def test_a_repository_that_cannot_isolate_lands_nothing_and_says_why(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: isolation opted out, so no commit is made and the line names the reason."""
    root, stack = _repo(tmp_path, monkeypatch, "0")
    start = _git(root, "rev-parse", "HEAD").strip()
    assert ck.main([str(root), "--stack", str(stack)]) == ck.EXIT_NOT_COMMITTED
    out = capsys.readouterr().out
    assert "NOT COMMITTED repo: a stack needs the isolated commit path" in out
    assert _git(root, "rev-parse", "HEAD").strip() == start


def test_an_unreadable_stack_file_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing file exits 2 and names it; nothing is committed."""
    root, _stack = _repo(tmp_path, monkeypatch, "1")
    assert ck.main([str(root), "--stack", str(tmp_path / "absent.json")]) == ck.EXIT_USAGE
    assert "absent.json" in capsys.readouterr().err

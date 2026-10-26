# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The commit a hook really pushes ends PUSHED, from the remote itself (W1082; split W2025).

nemik:W426. The two tests that run the pushing hook, apart from the verdict-only ones in
`test_commit_remote`: each is a real commit and a real push against a bare repository under
tmp_path, 2 to 3 s of mostly short processes, so a module of five of them waited 13 s of wall for
2.5 s of CPU and timed out at the 60 s bazel limit on a saturated host. One target is now a
fraction of that (the ruling: shard finer, never a longer timeout).
"""

from __future__ import annotations

import io
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata

if TYPE_CHECKING:
    from pathlib import Path

GIT = shutil.which("git") or "git"
EXECUTABLE = 0o755
SHORT = 7


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        [GIT, "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _git(remote, "init", "-q", "--bare", "-b", "main")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "user.email", "t@t")
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "-q", "origin", "main")
    (root / "a.txt").write_text("two\n", encoding="utf-8")
    return root


def _pushing(root: Path) -> None:
    hook = root / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\ngit push -q origin HEAD:main\n", encoding="utf-8")
    hook.chmod(EXECUTABLE)


def _last(root: Path) -> str:
    out = io.StringIO()
    request = commit_kata.Request(waypoint="W1", subject="the work", paths=("a.txt",))
    assert commit_kata.commit(root, request, out) == 0
    return out.getvalue().strip().splitlines()[-1]


def test_a_commit_the_remote_holds_is_pushed(tmp_path: Path) -> None:
    """The positive control: the hook pushed, ls-remote shows the sha, the line ends [PUSHED]."""
    root = _repo(tmp_path)
    _pushing(root)
    assert _last(root).endswith("[PUSHED]")


def test_a_peer_pushing_on_top_does_not_unpush_the_commit(tmp_path: Path) -> None:
    """The remote moved past the commit to a sha this clone lacks: still PUSHED, after one fetch."""
    root = _repo(tmp_path)
    _pushing(root)
    request = commit_kata.Request(waypoint="W1", subject="the work", paths=("a.txt",))
    assert commit_kata.commit(root, request, io.StringIO()) == 0
    mine = _git(root, "rev-parse", "HEAD").strip()
    peer = tmp_path / "peer"
    _git(tmp_path, "clone", "-q", str(tmp_path / "remote.git"), str(peer))
    (peer / "b.txt").write_text("peer\n", encoding="utf-8")
    _git(peer, "add", ".")
    _git(peer, "commit", "-q", "-m", "peer on top")
    _git(peer, "push", "-q", "origin", "main")
    line = commit_kata.verdict(root, _git(root, "rev-parse", "HEAD~1").strip(), mine, 0)
    assert line.endswith("[PUSHED]")
    assert commit_kata.on_remote(root, mine, _git(peer, "rev-parse", "HEAD").strip())

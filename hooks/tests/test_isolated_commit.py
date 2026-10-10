# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a commit can run in a private index over a snapshot of its own tree (W901).

⚑ THIS IS W891's EXPERIMENT, ON REAL GIT, BEFORE ANY CODE IS BUILT ON IT. `git commit` is run with
GIT_DIR the real repository, GIT_WORK_TREE a snapshot of the tree that lands, GIT_INDEX_FILE a
private index, and the snapshot as cwd. The questions: do the repo's own hooks run there and see a
worktree equal to the index; does HEAD move; does the real index lock exist during the hook; is the
real worktree and index untouched; does a peer's unstaged file stay out of the commit and out of
the way; and does post-commit still see the real git dir?

Every GIT_* variable is removed first, so nothing inherited can point a probe at a real repository.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import NamedTuple

_PRE_COMMIT = """#!/bin/sh
git update-index -q --refresh
if git diff --quiet; then tree=CLEAN; else tree=DIRTY; fi
if [ -e "$GIT_DIR/index.lock" ]; then lock=LOCK; else lock=NOLOCK; fi
printf '%s\\n%s\\n%s\\n' "$(pwd -P)" "$lock" "$tree" > "$PROBE"
"""
_POST_COMMIT = """#!/bin/sh
git rev-parse --git-dir > "$PROBE.post"
"""
_ORIGINAL = "original\n"
_EDITED = "edited by this session\n"
_PEER = "edited by a peer, not staged\n"


class Scene(NamedTuple):
    """What one isolated commit left behind, for the arms to read."""

    real: Path
    snap: Path
    probe: Path
    index_before: bytes
    head_before: str
    code: int
    stderr: str


def _env(tmp_path: Path, extra: dict[str, str]) -> dict[str, str]:
    """Build an environment with no inherited GIT_* variable and a fixed identity.

    Returns:
        the environment for one call.

    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        {
            "HOME": str(tmp_path),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CEILING_DIRECTORIES": str(tmp_path),
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        }
    )
    env.update(extra)
    return env


def _run(
    tmp_path: Path,
    tool: str,
    cwd: Path,
    args: list[str],
    extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run a tool resolved by `shutil.which` (never by partial path) and return the result.

    Returns:
        the completed process; the caller reads the exit code.

    """
    path = shutil.which(tool)
    assert path is not None
    return subprocess.run(
        [path, *args],
        cwd=cwd,
        env=_env(tmp_path, extra or {}),
        check=False,
        capture_output=True,
    )


def _git(tmp_path: Path, cwd: Path, *args: str, extra: dict[str, str] | None = None) -> str:
    """Run git and fail loudly.

    Returns:
        git's stdout.

    """
    done = _run(tmp_path, "git", cwd, list(args), extra)
    assert done.returncode == 0, done.stderr
    return done.stdout.decode()


def _hook(real: Path, name: str, body: str) -> None:
    """Install an executable hook in the repository."""
    path = real / ".git" / "hooks" / name
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _snapshot(tmp_path: Path, real: Path, tree: str) -> Path:
    """Materialize a tree into a fresh directory with `git archive | tar -x`.

    Returns:
        the directory.

    """
    snap = tmp_path / "snap"
    snap.mkdir()
    archive = _run(tmp_path, "git", real, ["archive", tree], {"GIT_DIR": str(real / ".git")})
    assert archive.returncode == 0, archive.stderr
    tar = shutil.which("tar")
    assert tar is not None
    subprocess.run([tar, "-x", "-C", str(snap)], input=archive.stdout, check=True)
    return snap


def _commit_isolated(tmp_path: Path) -> Scene:
    """Make a repo with a peer's unstaged edit, then commit this session's edit in isolation.

    Returns:
        the scene after the commit.

    """
    real = tmp_path / "real"
    real.mkdir()
    _git(tmp_path, real, "init", "--quiet")
    for name in ("a.txt", "b.txt"):
        (real / name).write_text(_ORIGINAL, encoding="utf-8")
    _git(tmp_path, real, "add", "a.txt", "b.txt")
    _git(tmp_path, real, "commit", "--quiet", "-m", "first")
    (real / "a.txt").write_text(_EDITED, encoding="utf-8")
    (real / "b.txt").write_text(_PEER, encoding="utf-8")
    _hook(real, "pre-commit", _PRE_COMMIT)
    _hook(real, "post-commit", _POST_COMMIT)
    git_dir = real / ".git"
    scope = {"GIT_DIR": str(git_dir), "GIT_INDEX_FILE": str(tmp_path / "commit.index")}
    _git(tmp_path, real, "read-tree", "HEAD", extra=scope)
    _git(tmp_path, real, "add", "-A", "--", "a.txt", extra={**scope, "GIT_WORK_TREE": str(real)})
    tree = _git(tmp_path, real, "write-tree", extra=scope).strip()
    snap = _snapshot(tmp_path, real, tree)
    index_before = (git_dir / "index").read_bytes()
    head_before = _git(tmp_path, real, "rev-parse", "HEAD").strip()
    probe = tmp_path / "probe"
    work = {**scope, "GIT_WORK_TREE": str(snap), "PROBE": str(probe)}
    done = _run(tmp_path, "git", snap, ["commit", "-m", "isolated"], work)
    return Scene(
        real, snap, probe, index_before, head_before, done.returncode, done.stderr.decode()
    )


def test_the_commit_runs_and_head_moves_to_a_tree_without_the_peers_edit(tmp_path: Path) -> None:
    """The positive control: HEAD advances, holds this session's edit, and not the peer's."""
    scene = _commit_isolated(tmp_path)
    assert scene.code == 0, scene.stderr
    head = _git(tmp_path, scene.real, "rev-parse", "HEAD").strip()
    assert head != scene.head_before
    assert _git(tmp_path, scene.real, "show", "HEAD:a.txt") == _EDITED
    assert _git(tmp_path, scene.real, "show", "HEAD:b.txt") == _ORIGINAL


def test_the_hook_ran_in_the_snapshot_where_the_worktree_equals_the_index(tmp_path: Path) -> None:
    """pre-commit saw the snapshot as its directory, a clean tree, and no real index lock."""
    scene = _commit_isolated(tmp_path)
    cwd, lock, tree = scene.probe.read_text(encoding="utf-8").split("\n")[:3]
    assert cwd == str(scene.snap.resolve())
    assert lock == "NOLOCK"
    assert tree == "CLEAN"


def test_the_real_worktree_and_index_are_untouched_and_no_lock_remains(tmp_path: Path) -> None:
    """The peer's unstaged edit survives; the real index is byte-identical; no lock is left."""
    scene = _commit_isolated(tmp_path)
    assert (scene.real / "b.txt").read_text(encoding="utf-8") == _PEER
    assert (scene.real / "a.txt").read_text(encoding="utf-8") == _EDITED
    assert (scene.real / ".git" / "index").read_bytes() == scene.index_before
    assert not (scene.real / ".git" / "index.lock").exists()


def test_post_commit_still_sees_the_real_git_dir(tmp_path: Path) -> None:
    """post-commit's `git rev-parse --git-dir` names the real repo, so push and witness hold."""
    scene = _commit_isolated(tmp_path)
    post = Path(f"{scene.probe}.post").read_text(encoding="utf-8").strip()
    assert Path(post).resolve() == (scene.real / ".git").resolve()

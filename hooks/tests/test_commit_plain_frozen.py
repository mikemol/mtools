# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A plain commit lands the bytes it froze at submit, not what the tree holds when it runs (W2120).

⚑ THE WITNESS (real git): submit a plain commit, edit one of its paths in the main tree while it
waits, and the landed tree holds the SUBMITTED bytes; the later edit stays in the working tree,
uncommitted. THE CONTROLS: with no snapshot the commit reads the tree late as it always did, and a
queue file is never frozen, so it lands as the card updates left it.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks.snapshot import NAMESPACE_ENV
from mikemol.hooks.stackfreeze import SNAP_ENV, at_submit_paths

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_ORIGINAL = "original\n"
_SUBMITTED = "submitted bytes\n"
_LATER = "edited in main while the commit waited\n"
_QUEUE = ".claude/paths-forward.json"
_REQUEST = ck.Request(waypoint="W1", subject="plain subject", paths=("a.txt",))


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def _decoy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with a.txt and a queue file committed, in a clean git environment.

    Returns:
        the repository's root.

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
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    _git(root, "init", "--quiet")
    (root / "a.txt").write_text(_ORIGINAL, encoding="utf-8")
    (root / _QUEUE).write_text("{}\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    return root


def _submit(root: Path, request: ck.Request, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = root / ".git" / "mtools"
    named = at_submit_paths(root, request.paths, ledger, "1", ck.run_git_in)
    monkeypatch.setenv(SNAP_ENV, named)


def _land(root: Path, request: ck.Request) -> int:
    return ck.commit(root, request, io.StringIO(), isolated=True)


def test_an_edit_after_submit_does_not_ride_into_the_landed_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The landed a.txt is the submitted bytes; the later edit stays in the working tree."""
    root = _decoy(tmp_path, monkeypatch)
    (root / "a.txt").write_text(_SUBMITTED, encoding="utf-8")
    _submit(root, _REQUEST, monkeypatch)
    (root / "a.txt").write_text(_LATER, encoding="utf-8")
    assert _land(root, _REQUEST) == 0
    assert _git(root, "show", "HEAD:a.txt") == _SUBMITTED
    assert (root / "a.txt").read_text(encoding="utf-8") == _LATER
    assert _git(root, "status", "--porcelain").splitlines() == [" M a.txt"]


def test_with_no_snapshot_the_commit_reads_the_tree_late_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: nothing frozen, so the later edit is what lands."""
    root = _decoy(tmp_path, monkeypatch)
    monkeypatch.delenv(SNAP_ENV, raising=False)
    (root / "a.txt").write_text(_LATER, encoding="utf-8")
    assert _land(root, _REQUEST) == 0
    assert _git(root, "show", "HEAD:a.txt") == _LATER


def test_a_queue_file_is_read_at_land_time_and_never_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A card update after submit lands with the commit; the frozen file keeps its submit bytes."""
    root = _decoy(tmp_path, monkeypatch)
    request = ck.Request(waypoint="W1", subject="s", paths=("a.txt", _QUEUE))
    (root / "a.txt").write_text(_SUBMITTED, encoding="utf-8")
    _submit(root, request, monkeypatch)
    (root / "a.txt").write_text(_LATER, encoding="utf-8")
    (root / _QUEUE).write_text('{"updated": 1}\n', encoding="utf-8")
    assert _land(root, request) == 0
    assert _git(root, "show", "HEAD:a.txt") == _SUBMITTED
    assert _git(root, "show", f"HEAD:{_QUEUE}") == '{"updated": 1}\n'


def test_the_snapshot_is_taken_only_for_a_fresh_plain_submit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stacked or re-exec'd run keeps the snapshot already in its environment."""
    root = _decoy(tmp_path, monkeypatch)
    ledger = root / ".git" / "mtools"
    parsed = (root, _REQUEST)
    held = {ck.HELD_ENV: "1", SNAP_ENV: "kept"}
    assert ck.plain_snapshot(root, parsed, ledger, "1", held) == "kept"
    assert ck.plain_snapshot(root, None, ledger, "1", {SNAP_ENV: "s"}) == "s"
    assert not ck.plain_snapshot(root, parsed, None, "1", {})
    fresh = ck.plain_snapshot(root, parsed, ledger, "7", {})
    assert fresh.endswith("stack-7.snap")
    assert (ledger / "stack-7.snap").is_file()

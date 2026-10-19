# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit REPO --stack FILE` pins the stack's trees at submit and releases them (W1615).

⚑ THE ENTRY POINT IS THE UNDER-TEST, with both seams spied: `pin_trees` must be called once at
submit with the snapshot the freeze made, and `release_trees` once at the run's end with the same
key, whatever the stack's verdict. The lease is not held (no HELD_ENV), as in the build-file
witness, because the pin sits on the submit path.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks.snapshot import NAMESPACE_ENV

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _git(root: Path, *args: str) -> str:
    return ck.run_git_in(list(args), {}, root).stdout


def _no_claim(*_args: object, **_kwargs: object) -> str:
    """Stand in for the fence claim: the lease is neither taken nor refused here (W1696).

    Returns:
        the empty reason, which `main` reads as a lease already held.

    """
    return ""


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", ck.HELD_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(ck, "claim_of", _no_claim)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
        NAMESPACE_ENV: str(tmp_path / "gate"),
        ck.ISOLATED_ENV: "1",
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    stack = tmp_path / "stack.json"
    entries = [{"waypoint": "W1", "subject": "a file", "paths": ["a.txt"]}]
    stack.write_text(json.dumps(entries), encoding="utf-8")
    return root, stack


def test_submit_pins_once_with_the_snapshot_and_the_run_releases_with_the_same_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One pin at submit with a real snapshot path, one release at the end, both under one key."""
    root, stack = _repo(tmp_path, monkeypatch)
    pinned: list[tuple[str, str]] = []
    released: list[str] = []

    def spy_pin(_root: Path, _ledger: Path | None, key: str, snap: str, _run: object) -> list[str]:
        pinned.append((key, snap))
        return []

    def spy_release(_root: Path, _ledger: Path | None, key: str, _run: object) -> int:
        released.append(key)
        return 0

    monkeypatch.setattr(ck, "pin_trees", spy_pin)
    monkeypatch.setattr(ck, "release_trees", spy_release)
    ck.main([str(root), "--stack", str(stack)])
    assert len(pinned) == 1
    assert pinned[0][1].endswith(f"stack-{pinned[0][0]}.snap")
    assert released == [pinned[0][0]]

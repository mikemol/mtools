# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A follower whose leader left a verdict prints it and exits without committing (W1671).

⚑ THE ENTRY POINT IS THE UNDER-TEST: `commit_kata.main` is called with a stack whose submit key is
fixed, and the verdict file for that key is written first, as a train leader would have. The lease
is not held (no HELD_ENV), because the check sits on the submit path after the turn. ⚑ THE CONTROL
IS THE REAL EFFECT: the leader's text reaches stdout, its code is the return value, HEAD does not
move, and the file is gone, so the same process cannot print it twice.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import trainverdict
from mikemol.hooks.commit_span import SUBMIT_ENV
from mikemol.hooks.snapshot import NAMESPACE_ENV
from mikemol.hooks.traindrive import Verdict

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

KEY = "1792000000000000001"
LEADER_CODE = 7


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
        SUBMIT_ENV: KEY,
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


def test_a_follower_prints_its_leaders_verdict_returns_its_code_and_commits_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Text on stdout, the leader's code returned, HEAD unmoved, the file taken."""
    root, stack = _repo(tmp_path, monkeypatch)
    ledger = ck.ledger_of(root)
    assert ledger is not None
    text = "REFUSED repo (rc=1): found bad\n"
    assert trainverdict.write(ledger, Verdict(KEY, LEADER_CODE, text))
    start = _git(root, "rev-parse", "HEAD").strip()
    assert ck.main([str(root), "--stack", str(stack)]) == LEADER_CODE
    assert capsys.readouterr().out == text
    assert _git(root, "rev-parse", "HEAD").strip() == start
    assert trainverdict.read(ledger, KEY) is None

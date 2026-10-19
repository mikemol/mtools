# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit REPO --in-gate` prints the commits the gate holds, with waypoints (W1587)."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING, cast

from mikemol.hooks import commit_counts, commit_kata

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

GIT = shutil.which("git") or "git"


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run([GIT, "-C", str(root), "init", "-q", "-b", "main"], check=True)
    return root


def _plant(root: Path, entries: dict[str, dict[str, object]]) -> None:
    ledger = root / ".git" / "mtools"
    ledger.mkdir()
    (ledger / "commit.counts").write_text(json.dumps(entries), encoding="utf-8")


def test_the_gate_prints_its_live_commits_with_their_waypoints(tmp_path: Path) -> None:
    """A live entry is listed with its waypoints; a dead one is not."""
    root = _repo(tmp_path)
    start = commit_counts.proc_start(os.getpid())
    _plant(
        root,
        {
            "1": {"state": "inflight", "pid": os.getpid(), "start": start, "waypoints": ["W1"]},
            "2": {"state": "queued", "pid": 2**31 - 1, "start": "1", "waypoints": ["W2"]},
        },
    )
    out = io.StringIO()
    assert commit_kata.in_gate([str(root)], {}, out) == 0
    rows = cast("list[dict[str, object]]", json.loads(out.getvalue()))
    assert rows == [{"key": "1", "state": "inflight", "waypoints": ["W1"], "began_ns": None}]


def test_an_empty_gate_prints_an_empty_list(tmp_path: Path) -> None:
    """No map at all is not an error: nothing is gating."""
    root = _repo(tmp_path)
    out = io.StringIO()
    assert commit_kata.in_gate([str(root)], {}, out) == 0
    assert cast("list[object]", json.loads(out.getvalue())) == []


def test_no_repository_named_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """A flag alone names nothing to read."""
    assert commit_kata.in_gate(["--json"], {}, io.StringIO()) == commit_kata.EXIT_USAGE
    assert "usage" in capsys.readouterr().err


def test_main_takes_the_flag_before_anything_is_queued(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Asking leaves no entry behind: the map is as it was after the call."""
    root = _repo(tmp_path)
    assert commit_kata.main([str(root), "--in-gate", "--json"]) == 0
    assert capsys.readouterr().out.strip() == "[]"
    assert not (root / ".git" / "mtools" / "commit.counts").exists()

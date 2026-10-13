# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `fleet.flush_targets` leaves a held repo alone: a live session, a red gate.

W1098. Its own module, not a case in `test_fleet`: that target builds a real repository per case
and sits at its timeout under host load, and the operator's ruling (2026-10-10) is to shard a slow
target, never to lengthen it. ⚑ THE QUIET REPO IS THE POSITIVE CONTROL: it has the same pending
queue and no claim.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

from mikemol.katas import fleet

if TYPE_CHECKING:
    from pathlib import Path

_QUEUE = ".claude/paths-forward.json"
_NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
_LIVE = '{"lock": {"holder": "s1", "taken_at": "2026-10-13T11:50:00Z"}, "waypoints": []}\n'
_RED = '{"waypoints": [{"title": "x commit gate is red: y", "status": "ready"}]}\n'
_QUIET = '{"x": 1}\n'


def _git(path: Path, *args: str) -> None:
    capture(("git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(path), *args))


def _repo(root: Path, name: str, body: str) -> None:
    """Make a repo whose committed queue is empty and whose working queue is `body`."""
    path = root / name
    (path / ".claude").mkdir(parents=True)
    capture(("git", "init", "-q", str(path)))
    (path / _QUEUE).write_text("{}\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "first")
    (path / _QUEUE).write_text(body, encoding="utf-8")


def test_a_repo_with_a_live_session_or_a_red_gate_is_not_a_target(tmp_path: Path) -> None:
    """A fresh tick lock and an open gate-red card each keep the flush out; the quiet repo is in."""
    host = fleet.Fleet(tmp_path / "hosts", tmp_path / "logs")
    for name, body in (("live", _LIVE), ("red", _RED), ("quiet", _QUIET)):
        _repo(host.root, name, body)
    assert fleet.flush_targets(host, now=_NOW) == ["quiet"]

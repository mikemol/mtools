# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The watchdog start line reaches a session whose tick stays open (W1540, nemik)."""

import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.pathsforward import cli


def _state(tmp_path: Path) -> Path:
    state = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    root = str(state.parent.parent)
    doc: dict[str, object] = {"counter": 0, "waypoints": [], "project_root": root}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def test_the_mode_prints_the_line_alone_and_takes_no_lock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One `watchdog:` line, exit 0, and the queue afterwards holds no lock."""
    state = _state(tmp_path)
    assert cli.main(["--state", str(state), "--watchdog-line"]) == 0
    said = capsys.readouterr().out.splitlines()
    assert len(said) == 1
    assert said[0].startswith("watchdog: ")
    doc = cast("dict[str, object]", json.loads(state.read_text(encoding="utf-8")))
    assert "lock" not in doc


def test_a_held_lock_still_prints_the_line_before_the_skip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The nemik case: the tick was already open, and the skipped open still says how to arm."""
    state = _state(tmp_path)
    assert cli.main(["--state", str(state), "--tick-open", "first"]) == 0
    capsys.readouterr()
    assert cli.main(["--state", str(state), "--tick-open", "second"]) == cli.EXIT_LOCKED
    said = capsys.readouterr().out.splitlines()
    assert any(line.startswith("watchdog: ") for line in said)

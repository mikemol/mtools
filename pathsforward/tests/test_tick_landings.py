# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""--tick-open prints the commits landed since the previous tick open (W2070)."""

import json
from pathlib import Path

import pytest

from mikemol.pathsforward import cli


def test_tick_open_prints_the_landing_lines_and_names_the_tip_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The open asks `landing_tips` for the repo and its stored-tip file, and prints the answer."""
    asked: list[tuple[Path, Path]] = []

    def tips(root: Path, seen: Path) -> list[str]:
        asked.append((root, seen))
        return ["landings: a canned line"]

    monkeypatch.setattr(cli, "_landing_tips", tips)
    state = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    root = tmp_path / "myrepo"
    doc: dict[str, object] = {"counter": 0, "waypoints": [], "project_root": str(root)}
    state.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(state), "--tick-open", "tester"]) == 0
    assert "landings: a canned line" in capsys.readouterr().out
    assert asked == [(root, root / ".git" / "mtools" / "branch.tip")]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The standing rules are readable: `--standing` alone and `--tick-open` with the rest (W1470)."""

import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.pathsforward import cli, standing


def _repo(tmp_path: Path, rules: list[str] | None) -> Path:
    state = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    doc: dict[str, object] = {
        "counter": 0,
        "waypoints": [],
        "project_root": str(tmp_path / "myrepo"),
    }
    if rules is not None:
        doc[standing.KEY] = rules
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def test_lines_number_each_rule_in_stored_order() -> None:
    """A caller cites a rule by its number, and the list reads in the order it was stored."""
    doc: dict[str, object] = {standing.KEY: ["first rule", "second rule"]}
    assert standing.lines(doc) == ["standing 1: first rule", "standing 2: second rule"]


def test_no_stored_rules_says_so_and_names_the_writer() -> None:
    """An absent or empty list is a reading, not a silence."""
    assert standing.lines({}) == [standing.NONE_LINE]
    assert standing.lines({standing.KEY: []}) == [standing.NONE_LINE]
    assert "--standing-set" in standing.NONE_LINE


def test_the_standing_mode_prints_the_rules_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing else is printed and no lock is taken."""
    state = _repo(tmp_path, ["one", "two"])
    assert cli.main(["--state", str(state), "--standing"]) == 0
    assert capsys.readouterr().out.splitlines() == ["standing 1: one", "standing 2: two"]
    held = cast("dict[str, object]", json.loads(state.read_text(encoding="utf-8")))
    assert not held.get("lock")


def test_tick_open_prints_the_rules_before_its_closing_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A tick that opens has read the repo's rules, so no session greps its queue for them."""
    state = _repo(tmp_path, ["keep a commit in flight"])
    assert cli.main(["--state", str(state), "--tick-open", "tester"]) == 0
    said = capsys.readouterr().out.splitlines()
    assert "standing 1: keep a commit in flight" in said
    assert said[-1].startswith("tick open as tester")

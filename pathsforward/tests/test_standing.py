# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for --standing-set: the standing list has a writer and is replaced whole (W862)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, ops
from mikemol.pathsforward.model import validate

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import State

Rec = dict[str, object]

_OLD = ["run the old script", "never do the other thing"]


def _state() -> State:
    """Build a state that already carries a standing list.

    Returns:
        the state.

    """
    return validate({"counter": 0, "waypoints": [], "residue": [], "standing": list(_OLD)})


def test_the_list_is_replaced_whole_and_blank_lines_are_not_rules() -> None:
    """A rule left out of the file is retired; surrounding blanks and indentation are dropped."""
    state = _state()
    stored = ops.set_standing(state, ["", "  first rule  ", "", "second rule", "   "])
    assert stored == len(("first rule", "second rule"))
    assert state.doc["standing"] == ["first rule", "second rule"]


@pytest.mark.parametrize("lines", [[], [""], ["   ", "\t"]])
def test_a_file_with_no_rule_is_refused_and_leaves_the_list_alone(lines: list[str]) -> None:
    """An empty list is a decision, not a side effect of an empty file."""
    state = _state()
    with pytest.raises(ops.RefusedError, match="0 non-blank lines"):
        ops.set_standing(state, lines)
    assert state.doc["standing"] == _OLD


def test_the_cli_reads_a_file_stores_it_and_the_payload_emits_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end: the verb stores the file's rules, and --payload carries them verbatim."""
    path = tmp_path / "paths-forward.json"
    doc: Rec = {
        "counter": 0,
        "project_root": str(tmp_path),
        "waypoints": [],
        "residue": [],
        "standing": list(_OLD),
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    rules = tmp_path / "rules.txt"
    rules.write_text("keep this rule\n\nand this one\n", encoding="utf-8")
    assert cli.main(["--state", str(path), "--standing-set", str(rules)]) == cli.EXIT_OK
    assert "standing set: 2 rule(s)" in capsys.readouterr().out
    stored = cast("Rec", json.loads(path.read_text(encoding="utf-8")))["standing"]
    assert stored == ["keep this rule", "and this one"]
    assert cli.main(["--state", str(path), "--payload", "--root", str(tmp_path)]) == cli.EXIT_OK
    payload = capsys.readouterr().out
    assert "  - keep this rule\n  - and this one\n" in payload
    assert "run the old script" not in payload


def test_the_cli_refuses_an_empty_file_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 2 with the reason on stderr; the file on disk is byte for byte what it was."""
    path = tmp_path / "paths-forward.json"
    doc: Rec = {"counter": 0, "waypoints": [], "residue": [], "standing": list(_OLD)}
    path.write_text(json.dumps(doc), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    empty = tmp_path / "empty.txt"
    empty.write_text("\n  \n", encoding="utf-8")
    assert cli.main(["--state", str(path), "--standing-set", str(empty)]) == cli.EXIT_REFUSED
    assert "0 non-blank lines" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == before

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--standing --raw` prints the bare rules and round-trips through `--standing-set` (W2137).

⚑ THE CONTROLS: the numbered form is unchanged without `--raw`, and setting the queue from the raw
output changes no rule, while setting it from an edited copy changes exactly the edited rule.
"""

import json
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, standing, store

_RULES = ["never edit the settings file", "do not expand the baseline", "run the gate alone"]


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    state = tmp_path / ".claude" / "paths-forward.json"
    doc = {"counter": 1, "project_root": "/x", "waypoints": [], "residue": [], "standing": _RULES}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def test_raw_prints_the_bare_rules_and_the_default_stays_numbered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--raw` has no `standing N:` prefix; without it the numbered lines are as before."""
    state = _project(tmp_path)
    assert cli.main(["--state", str(state), "--standing", "--raw"]) == 0
    assert capsys.readouterr().out.splitlines() == _RULES
    assert cli.main(["--state", str(state), "--standing"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == f"standing 1: {_RULES[0]}"


def test_setting_from_the_raw_output_changes_nothing_and_an_edit_changes_one_rule(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Round trip: the raw output as the file keeps the list; one edited line changes one rule."""
    state = _project(tmp_path)
    assert cli.main(["--state", str(state), "--standing", "--raw"]) == 0
    raw = tmp_path / "raw.txt"
    raw.write_text(capsys.readouterr().out, encoding="utf-8")
    assert cli.main(["--state", str(state), "--standing-set", str(raw)]) == 0
    assert standing.rules(store.load(state).doc) == _RULES
    edited = [_RULES[0], "do not widen the baseline", _RULES[2]]
    declared = f"# replaces: {_RULES[1]}"
    raw.write_text("\n".join([*edited, declared]) + "\n", encoding="utf-8")
    assert cli.main(["--state", str(state), "--standing-set", str(raw)]) == 0
    assert standing.rules(store.load(state).doc) == edited

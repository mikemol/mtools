# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that --manifests-from stores many manifests at once, all or nothing (W1453).

⚑ THE CONTROL IS THE STATE FILE'S BYTES: a dry run and every refused file leave them identical; only
--write on a well-formed file changes them, and then every card in the file is written together.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]
_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
_COUNTER = 3


def _card(sym: str) -> Rec:
    return {
        "symbol": sym,
        "title": f"t{sym}",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path) -> Path:
    doc: Rec = {
        "counter": _COUNTER,
        "project_root": str(tmp_path),
        "waypoints": [_card("W1"), _card("W2")],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _drafts(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "manifests.json"
    path.write_text(body, encoding="utf-8")
    return path


def _run(state: Path, *args: str) -> int:
    return cli.main(["--state", str(state), *args])


def _cards(state: Path) -> list[Rec]:
    doc = cast("Rec", json.loads(state.read_text(encoding="utf-8")))
    return cast("list[Rec]", doc["waypoints"])


GOOD = (
    '[{"symbol": "W1", "manifest": ["a.py", "b.py"], "size": "small"},'
    ' {"symbol": "W2", "manifest": ["c.py"], "size": "medium"}]'
)


def test_a_dry_run_prints_each_change_and_stores_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --write the plan is printed, one line per card, and the file is byte-identical."""
    state = _state(tmp_path)
    before = state.read_bytes()
    assert _run(state, "--manifests-from", str(_drafts(tmp_path, GOOD))) == _OK
    out = capsys.readouterr().out
    assert "W1: manifest [a.py, b.py] size small" in out
    assert "W2: manifest [c.py] size medium" in out
    assert "dry run: 2 manifest(s) would be stored" in out
    assert state.read_bytes() == before


def test_write_stores_every_manifest_and_size_together(tmp_path: Path) -> None:
    """With --write every card in the file gets its manifest and size class in one call."""
    state = _state(tmp_path)
    assert _run(state, "--manifests-from", str(_drafts(tmp_path, GOOD)), "--write") == _OK
    first, second = _cards(state)
    assert first["manifest"] == ["a.py", "b.py"]
    assert first["size_class"] == "small"
    assert second["manifest"] == ["c.py"]
    assert second["size_class"] == "medium"


@pytest.mark.parametrize(
    "body",
    [
        '[{"symbol": "W1", "manifest": ["a.py"]}, {"symbol": "W9", "manifest": ["b.py"]}]',
        '[{"symbol": "W1", "manifest": ["a.py"]}, {"symbol": "W2", "manifest": ["src/"]}]',
        '[{"symbol": "W1", "manifest": ["*.py"]}]',
        '[{"symbol": "W1", "manifest": ["a.py"]}, {"symbol": "W1", "manifest": ["b.py"]}]',
        '[{"symbol": "W1", "manifest": ["a.py"], "size": "huge"}]',
        '[{"symbol": "W1", "manifest": "a.py"}]',
        "not json",
    ],
)
def test_a_refused_file_leaves_the_state_byte_identical_even_with_write(
    tmp_path: Path, body: str
) -> None:
    """The control: one bad card refuses the whole file, so the good ones are not stored either."""
    state = _state(tmp_path)
    before = state.read_bytes()
    assert _run(state, "--manifests-from", str(_drafts(tmp_path, body)), "--write") == _REFUSED
    assert state.read_bytes() == before


def test_a_refusal_names_every_fault_at_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown symbol and a glob are both named, so the review fixes them in one pass."""
    state = _state(tmp_path)
    body = '[{"symbol": "W9", "manifest": ["a.py"]}, {"symbol": "W1", "manifest": ["*.py"]}]'
    assert _run(state, "--manifests-from", str(_drafts(tmp_path, body))) == _REFUSED
    err = capsys.readouterr().err
    assert "W9" in err
    assert "glob" in err

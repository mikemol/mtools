# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a generated file is not an exclusive write, and a real file still is (W1468).

⚑ THE CONTROL IS THE REAL FILE: two working cards that both declare `src/a.py` for write still
conflict, and only a path the repo lists in `.claude/generated.json` leaves the lease. A list that
is absent or malformed exempts nothing.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, generated

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
_HOLDER = "mtools-tick-opus"


def _card(symbol: str, touches: list[str]) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": "ready",
        "enables": [],
        "touches": touches,
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path, shared: str) -> Path:
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path),
        "waypoints": [_card("W1", [shared]), _card("W2", [shared])],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(path), "--lock", _HOLDER]) == _OK
    return path


def _list(tmp_path: Path, body: str) -> None:
    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / ".claude" / "generated.json").write_text(body, encoding="utf-8")


def _work(path: Path, symbol: str) -> int:
    return cli.main(["--state", str(path), "--update", symbol, "--status", "working"])


def _status(path: Path, symbol: str) -> str:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    card = next(c for c in cast("list[Rec]", doc["waypoints"]) if c["symbol"] == symbol)
    return str(card["status"])


def test_two_cards_writing_a_real_file_still_conflict(tmp_path: Path) -> None:
    """The control: with no list, the second card to work a shared `!w` file is refused."""
    state = _state(tmp_path, "file:src/a.py!w")
    assert _work(state, "W1") == _OK
    assert _work(state, "W2") == _REFUSED
    assert _status(state, "W2") == "ready"


def test_two_cards_writing_a_generated_file_both_work(tmp_path: Path) -> None:
    """The el-openglo case: the shared file is listed as generated, so neither holds a lease."""
    _list(tmp_path, '{"generated": [{"path": "src/closures.bzl"}]}')
    state = _state(tmp_path, "file:src/closures.bzl!w")
    assert _work(state, "W1") == _OK
    assert _work(state, "W2") == _OK
    assert _status(state, "W1") == "working"
    assert _status(state, "W2") == "working"


def test_a_list_that_does_not_parse_exempts_nothing(tmp_path: Path) -> None:
    """A broken or wrongly shaped list is no list, so the conflict stands."""
    for body in ("{not json", '["src/closures.bzl"]', '{"generated": "src/closures.bzl"}'):
        _list(tmp_path, body)
        assert generated.paths(tmp_path) == frozenset()


def test_only_the_listed_file_leaves_the_lease() -> None:
    """Another file of the same card is still leased: the tags are filtered one by one."""
    tags = ["file:src/closures.bzl!w", "file:src/real.py!w", "topic:x"]
    kept = generated.leased(tags, frozenset({"src/closures.bzl"}))
    assert kept == ["file:src/real.py!w", "topic:x"]

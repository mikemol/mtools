# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card says whether its change ships as a deployment, and the check holds the two rules (W1814).

⚑ THE CARD THAT SAYS NOTHING IS THE NEGATIVE CONTROL: a card with no `deploys` is not a card
that deploys nothing in the stored file, so a flag that was never given writes no key.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import check as chk
from mikemol.pathsforward import cli
from mikemol.pathsforward.model import State, validate

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]
_OK = cli.EXIT_OK
_QUERY = "input.git_ref"


def _wp(sym: str, status: str = "ready", **extra: object) -> Rec:
    w: Rec = {
        "symbol": sym,
        "title": f"t{sym}",
        "status": status,
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    w.update(extra)
    return w


def _file(tmp_path: Path) -> Path:
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path),
        "state_path": "/elsewhere/live/paths-forward.json",
        "waypoints": [_wp("W1"), _wp("W2")],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _waypoints(path: Path) -> list[Rec]:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return cast("list[Rec]", doc["waypoints"])


def _state(root: Path, *cards: Rec) -> State:
    return validate(
        {"counter": len(cards), "project_root": str(root), "waypoints": list(cards), "residue": []}
    )


def test_update_stores_deploys_true_and_false_and_a_card_never_given_it_has_no_key(
    tmp_path: Path,
) -> None:
    """The flag takes the words true and false; an untouched card grows no field."""
    path = _file(tmp_path)
    assert cli.main(["--state", str(path), "--update", "W1", "--deploys", "true"]) == _OK
    assert _waypoints(path)[0]["deploys"] is True
    assert cli.main(["--state", str(path), "--update", "W1", "--deploys", "false"]) == _OK
    assert _waypoints(path)[0]["deploys"] is False
    assert "deploys" not in _waypoints(path)[1]


def test_a_landed_card_must_declare_deploys_true(tmp_path: Path) -> None:
    """Landed with deploys false or absent is a card in the wrong state; true is clean."""
    cards = (
        _wp("W1", "landed", witness=_QUERY, deploys=True),
        _wp("W2", "landed", witness=_QUERY, deploys=False),
        _wp("W3", "landed", witness=_QUERY),
    )
    found = chk.deploys_rules(_state(tmp_path, *cards))
    assert [f.split(":")[0] for f in found] == ["W2", "W3"]
    assert "landed without deploys true" in found[0]


def test_a_done_card_that_deploys_needs_its_witness_and_its_language(tmp_path: Path) -> None:
    """Done with deploys true and no witness or no language is found; both present is clean."""
    cards = (
        _wp("W1", "done", deploys=True),
        _wp("W2", "done", deploys=True, witness=_QUERY),
        _wp("W3", "done", deploys=True, witness=_QUERY, witness_lang="rego"),
    )
    found = chk.deploys_rules(_state(tmp_path, *cards))
    assert [f.split(":")[0] for f in found] == ["W1", "W2"]


def test_a_done_card_that_deploys_nothing_and_a_ready_card_raise_nothing(tmp_path: Path) -> None:
    """The controls: done with deploys false or absent, and any non-landed card, are clean."""
    cards = (_wp("W1", "done"), _wp("W2", "done", deploys=False), _wp("W3", deploys=True))
    assert chk.deploys_rules(_state(tmp_path, *cards)) == []

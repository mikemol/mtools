# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card can be withheld from the repo's export, whole, by a flag (W1836, nemik:W516).

⚑ THE CARD THAT SAYS NOTHING IS THE NEGATIVE CONTROL: a card never given the flag is published, so
a flag that was never given writes no key, and clearing it writes false, not a deletion.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]
_OK = cli.EXIT_OK


def _wp(sym: str) -> Rec:
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


def test_update_stores_withheld_true_and_false_and_an_untouched_card_has_no_key(
    tmp_path: Path,
) -> None:
    """The flag takes the words true and false; a card never given it grows no field."""
    path = _file(tmp_path)
    assert cli.main(["--state", str(path), "--update", "W1", "--withheld", "true"]) == _OK
    assert _waypoints(path)[0]["withheld"] is True
    assert cli.main(["--state", str(path), "--update", "W1", "--withheld", "false"]) == _OK
    assert _waypoints(path)[0]["withheld"] is False
    assert "withheld" not in _waypoints(path)[1]


def test_a_withheld_card_stays_withheld_when_it_is_dropped_to_residue(tmp_path: Path) -> None:
    """Residue is exported too (W1840), so a dropped card must not lose the flag and publish."""
    path = _file(tmp_path)
    cli.main(["--state", str(path), "--update", "W1", "--withheld", "true"])
    assert cli.main(["--state", str(path), "--drop", "W1", "no longer needed"]) == _OK
    assert cli.main(["--state", str(path), "--drop", "W2", "no longer needed"]) == _OK
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    withheld, plain = cast("list[Rec]", doc["residue"])
    assert (withheld["symbol"], withheld["withheld"]) == ("W1", True)
    assert "withheld" not in plain


def test_the_flag_survives_a_later_update_of_another_field(tmp_path: Path) -> None:
    """Setting the next step on a withheld card does not publish it."""
    path = _file(tmp_path)
    cli.main(["--state", str(path), "--update", "W1", "--withheld", "true"])
    assert cli.main(["--state", str(path), "--update", "W1", "--next", "later"]) == _OK
    assert _waypoints(path)[0]["withheld"] is True

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for --mint-residue: one claimable card per waypoint and gate, never duplicated."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, closure, opa_eval, store
from mikemol.pathsforward.model import RefusedError, validate

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_CLOSES = "--population SOURCE BOUND"
_WAYPOINT: Rec = {
    "symbol": "W1",
    "title": "one bounded thing",
    "status": "ready",
    "blocked_on": [],
    "blocked_kind": None,
    "touches": ["pin", "gate"],
    "next_bounded_step": "run it",
    "evidence": "it printed OK",
    "ticks_blocked": 0,
}


def _queue(tmp_path: Path, *extra: Rec) -> Path:
    """Write `<tmp>/home/.claude/paths-forward.json`: W1 with no population, plus any extras.

    Returns:
        the queue's path.

    """
    path = tmp_path / "home" / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    doc: Rec = {"counter": 1 + len(extra), "waypoints": [_WAYPOINT, *extra], "residue": []}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _mint(path: Path, root: Path, symbol: str, gate: str) -> int:
    """Run `--mint-residue` on a queue.

    Returns:
        the exit code.

    """
    return cli.main(["--state", str(path), "--mint-residue", symbol, gate, "--root", str(root)])


def _live(path: Path) -> list[Rec]:
    """Read the live waypoints of a queue.

    Returns:
        the waypoints.

    """
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return cast("list[Rec]", doc["waypoints"])


def test_the_title_starts_with_the_symbol_and_gate_and_is_clipped() -> None:
    """The prefix is the idempotency key, and a long closes_by stays under the bundled limit."""
    assert closure.prefix("W9", "observable") == "W9 observable: "
    short = closure.title_for("W9", "coverable", "name a\n finite  source")
    assert short == "W9 coverable: name a finite source"
    long = closure.title_for("W9", "coverable", "x" * 500)
    assert len(long) == closure.TITLE_CHARS
    assert long.startswith("W9 coverable: ")
    assert long.endswith("…")


def test_the_entry_at_a_gate_is_found_and_a_missing_one_is_refused() -> None:
    """Only a gate the verdict has residue at can be minted for."""
    residue: list[Rec] = [{"gate": "observable", "closes_by": "a"}, {"gate": "coverable"}]
    assert closure.entry_at(residue, "coverable") == {"gate": "coverable"}
    with pytest.raises(RefusedError, match="no residue at reachable"):
        closure.entry_at(residue, "reachable")


def test_an_existing_card_is_found_by_cause_and_title_prefix() -> None:
    """Only a live waypoint caused by the symbol with the gate's prefix counts as the card."""
    state = validate(
        {
            "counter": 4,
            "waypoints": [
                {**_WAYPOINT, "symbol": "W2", "caused_by": "W1", "title": "W1 coverable: x"},
                {**_WAYPOINT, "symbol": "W3", "caused_by": "W9", "title": "W1 observable: y"},
                {**_WAYPOINT, "symbol": "W4", "caused_by": "W1", "title": "W1 observable: z"},
            ],
            "residue": [],
        }
    )
    assert closure.existing(state, "W1", "coverable") == "W2"
    assert closure.existing(state, "W1", "observable") == "W4"
    assert closure.existing(state, "W1", "reachable") is None


def test_minting_creates_one_claimable_card_caused_by_the_waypoint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The real policy's closes_by becomes the card's title and next step, with the touches."""
    path = _queue(tmp_path)
    assert _mint(path, tmp_path, "W1", "coverable") == cli.EXIT_OK
    assert "W1 coverable: minting a card for:" in capsys.readouterr().out
    card = _live(path)[-1]
    assert card["symbol"] == "W2"
    assert card["title"] == f"W1 coverable: {_CLOSES}"
    assert (card["next_bounded_step"], card["caused_by"]) == (_CLOSES, "W1")
    assert card["touches"] == ["pin", "gate"]
    assert card["status"] == "ready"
    ledger = store.sibling(path, store.LEDGER).read_text(encoding="utf-8")
    assert "W2" in ledger
    assert "minted" in ledger


def test_a_rerun_finds_the_card_and_mints_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One card per waypoint and gate: the second call names the first and changes nothing."""
    path = _queue(tmp_path)
    assert _mint(path, tmp_path, "W1", "coverable") == cli.EXIT_OK
    capsys.readouterr()
    before = path.read_text(encoding="utf-8")
    assert _mint(path, tmp_path, "W1", "coverable") == cli.EXIT_OK
    assert "already minted as W2" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == before


def test_an_entry_that_names_a_closes_ref_mints_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A deferral that already cites the card that closes it points at a card that exists."""
    deferral = {
        "gate": "coverable",
        "reference_arm": "host:luthen",
        "what": "population is unbounded",
        "closes_by": "name a finite source",
        "closes_ref": "W9",
    }
    # W5 has no population, so the policy derives its own coverable entry too: the cited card
    # closes the gap for both, and the derived entry does not draw a duplicate.
    path = _queue(tmp_path, {**_WAYPOINT, "symbol": "W2", "deferred": [deferral]})
    assert _mint(path, tmp_path, "W2", "coverable") == cli.EXIT_OK
    assert "closes_ref W9 already names the card" in capsys.readouterr().out
    assert len(_live(path)) == len(("W1", "W2"))


def test_no_residue_at_the_gate_or_a_symbol_not_live_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing is minted for a gate the waypoint has no gap at, or for an unknown waypoint."""
    path = _queue(tmp_path)
    assert _mint(path, tmp_path, "W1", "reachable") == cli.EXIT_REFUSED
    assert _mint(path, tmp_path, "W77", "coverable") == cli.EXIT_REFUSED
    assert len(_live(path)) == 1
    assert capsys.readouterr().err.count("not minted") == len(("gate", "symbol"))


def test_nothing_is_minted_unjudged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the pinned opa the residue cannot be known, so the command is exit 2."""
    path = _queue(tmp_path)
    monkeypatch.setenv(opa_eval.OPA_ENV, str(tmp_path / "absent"))
    assert _mint(path, tmp_path, "W1", "coverable") == cli.EXIT_REFUSED
    assert "not minted" in capsys.readouterr().err
    assert len(_live(path)) == 1

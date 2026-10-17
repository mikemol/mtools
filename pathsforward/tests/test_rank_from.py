# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `--rank-from` refuses a close that skipped the top ranked card (W1368).

⚑ THE CONTROL IS THE CLOSE THAT WOULD HAVE PASSED: W2 (blocked) is a named block and W3, W4 are
ready, so without the rank file the close goes through. With the file naming W4 as top, the same
close is refused until W4 is the card worked, a `--blocked-by`, or cited by `--reason`; a top card
that is itself blocked is not skipped, and a close with no file keeps its old behaviour.
"""

from __future__ import annotations

import json
from itertools import starmap
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
_HOLDER = "mtools-tick-opus"
_STATUSES = (("W1", "working"), ("W2", "blocked"), ("W3", "ready"), ("W4", "ready"))


def _card(symbol: str, status: str) -> Rec:
    blocked = status == "blocked"
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": [],
        "blocked_on": ["operator: act x"] if blocked else [],
        "blocked_kind": "human" if blocked else None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path) -> Path:
    cards = list(starmap(_card, _STATUSES))
    doc: Rec = {
        "counter": len(cards),
        "project_root": str(tmp_path),
        "waypoints": cards,
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(path), "--lock", _HOLDER]) == _OK
    return path


def _rank(tmp_path: Path, body: str) -> str:
    path = tmp_path / "rank.json"
    path.write_text(body, encoding="utf-8")
    return str(path)


def _top(symbol: str) -> str:
    rows: list[Rec] = [{"symbol": symbol, "weight": 9}, {"symbol": "W3", "weight": 1}]
    return json.dumps(rows)


def _close(state: Path, *extra: str) -> int:
    close = ["--tick-close", _HOLDER, "W1", "advanced", "unblock", "the note", *extra]
    return cli.main(["--state", str(state), *close])


def _locked(state: Path) -> bool:
    doc = cast("Rec", json.loads(state.read_text(encoding="utf-8")))
    lock = doc.get("lock")
    return isinstance(lock, dict) and bool(cast("Rec", lock).get("holder"))


def test_without_a_rank_file_a_named_block_closes_as_before(tmp_path: Path) -> None:
    """The control: this exact close passes, so the refusals below are the rank file's doing."""
    state = _state(tmp_path)
    assert _close(state, "--blocked-by", "W2") == _OK
    assert not _locked(state)


def test_a_skipped_top_card_refuses_the_close_and_names_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W4 is top, ready, not worked and not named: refused, lock kept, the reason to give shown."""
    state = _state(tmp_path)
    rank = _rank(tmp_path, _top("W4"))
    assert _close(state, "--blocked-by", "W2", "--rank-from", rank) == _REFUSED
    out = capsys.readouterr().out
    assert "the top card by nemik rank is W4" in out
    assert '--reason "W4: <why it waits>"' in out
    assert _locked(state)


@pytest.mark.parametrize(
    "extra",
    [
        ("--blocked-by", "W4"),
        ("--reason", "W4 waits on the gate"),
    ],
)
def test_naming_the_top_card_lets_the_close_through(tmp_path: Path, extra: tuple[str, ...]) -> None:
    """A --blocked-by of the top card, or a --reason that cites it, accounts for it."""
    state = _state(tmp_path)
    rank = _rank(tmp_path, _top("W4"))
    assert _close(state, *extra, "--rank-from", rank) == _OK
    assert not _locked(state)


def test_the_worked_card_being_top_is_not_a_skip(tmp_path: Path) -> None:
    """Top is W1, the card this tick worked: nothing was passed over."""
    state = _state(tmp_path)
    rank = _rank(tmp_path, _top("W1"))
    assert _close(state, "--blocked-by", "W2", "--rank-from", rank) == _OK


def test_a_blocked_top_card_is_not_a_skip(tmp_path: Path) -> None:
    """Top is W2, which is blocked: it could not have been worked, so the close passes."""
    state = _state(tmp_path)
    rank = _rank(tmp_path, _top("W2"))
    assert _close(state, "--blocked-by", "W2", "--rank-from", rank) == _OK


def test_an_empty_rank_list_adds_no_refusal(tmp_path: Path) -> None:
    """No ranked card, no new refusal."""
    state = _state(tmp_path)
    assert _close(state, "--blocked-by", "W2", "--rank-from", _rank(tmp_path, "[]")) == _OK


@pytest.mark.parametrize("body", ["not json", '{"symbol": "W4"}', '[{"title": "x"}]', "[7]"])
def test_a_rank_file_that_is_not_a_ranked_list_refuses_the_close(tmp_path: Path, body: str) -> None:
    """Data we were asked to read and cannot is a refusal, and the lock stays held."""
    state = _state(tmp_path)
    rank = _rank(tmp_path, body)
    assert _close(state, "--blocked-by", "W2", "--rank-from", rank) == _REFUSED
    assert _locked(state)


def test_close_gate_applies_the_same_rule_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The read half refuses on a skipped top card too, and leaves the state as it found it."""
    state = _state(tmp_path)
    before = state.read_bytes()
    rank = _rank(tmp_path, _top("W4"))
    gate = ["--state", str(state), "--close-gate", "--blocked-by", "W2", "--rank-from", rank]
    assert cli.main(gate) == _REFUSED
    assert "the top card by nemik rank is W4" in capsys.readouterr().out
    assert state.read_bytes() == before

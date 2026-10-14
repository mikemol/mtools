# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `--tick-close` refuses while a ready, unblocked card exists (W1203).

⚑ A TICK IS A LOOP CYCLE, NOT A CARD (operator, 2026-10-14). The close reads the queue: a ready card
that waits behind nothing refuses it, and only a NAMED block (`--blocked-by W<n>`, or `--reason`
citing a card of this queue) lets it through, and is ledgered. ⚑ THE CONTROLS ARE THE CLOSES THAT
MUST STILL WORK: an all-blocked queue, a ready card behind an open enabler, and a reason that names
no card (still refused).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]

_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
_HOLDER = "mtools-tick-opus"


def _card(symbol: str, status: str, enables: list[str] | None = None) -> Rec:
    blocked = status == "blocked"
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": enables or [],
        "blocked_on": ["operator: act x"] if blocked else [],
        "blocked_kind": "human" if blocked else None,
        "next_bounded_step": "s",
        "evidence": "done" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path, cards: list[Rec]) -> Path:
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


def _close(path: Path, *extra: str) -> int:
    close = ["--tick-close", _HOLDER, "W1", "advanced", "unblock", "the note", *extra]
    return cli.main(["--state", str(path), *close])


def _locked(path: Path) -> bool:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    lock = doc.get("lock")
    return isinstance(lock, dict) and bool(cast("Rec", lock).get("holder"))


def _ledger(tmp_path: Path) -> str:
    ledger = tmp_path / "paths-forward.ledger"
    return ledger.read_text(encoding="utf-8") if ledger.exists() else ""


def test_a_ready_unblocked_card_refuses_the_close_and_the_lock_stays_held(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two ready cards and a bare close: refused, nothing ledgered, the lock kept, count shown."""
    path = _state(tmp_path, [_card("W1", "working"), _card("W2", "ready"), _card("W3", "ready")])
    assert _close(path) == _REFUSED
    out = capsys.readouterr().out
    assert "ready and unblocked: 2; top: W2, W3" in out
    assert "a tick is a loop cycle" in out
    assert _locked(path)
    assert "the note" not in _ledger(tmp_path)


def test_the_top_three_are_shown_of_many(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Five ready cards: the count is five and only the first three are named."""
    cards = [_card("W1", "working"), *[_card(f"W{n}", "ready") for n in range(2, 7)]]
    path = _state(tmp_path, cards)
    assert _close(path) == _REFUSED
    assert "ready and unblocked: 5; top: W2, W3, W4" in capsys.readouterr().out


def test_an_all_blocked_queue_closes_as_before(tmp_path: Path) -> None:
    """The control: nothing ready, so the close is unchanged and the lock is released."""
    path = _state(tmp_path, [_card("W1", "working"), _card("W2", "blocked")])
    assert _close(path) == _OK
    assert not _locked(path)
    assert "the note" in _ledger(tmp_path)


def test_a_ready_card_behind_an_open_enabler_is_not_counted(tmp_path: Path) -> None:
    """The control: W2 is ready but W1 (open) enables it, so no tick can work it yet."""
    path = _state(tmp_path, [_card("W1", "working", ["W2"]), _card("W2", "ready")])
    assert _close(path) == _OK
    assert not _locked(path)


def test_blocked_by_a_live_card_closes_and_is_ledgered(tmp_path: Path) -> None:
    """`--blocked-by W2` (not done) lets the close through, and the ledger carries it."""
    path = _state(tmp_path, [_card("W1", "working"), _card("W2", "blocked"), _card("W3", "ready")])
    assert _close(path, "--blocked-by", "W2") == _OK
    assert not _locked(path)
    assert "blocked by W2" in _ledger(tmp_path)


def test_a_reason_citing_a_card_of_the_queue_closes_and_is_ledgered(tmp_path: Path) -> None:
    """`--reason` that names W2 lets it through, and the reason is in the ledger line."""
    path = _state(tmp_path, [_card("W1", "working"), _card("W2", "blocked"), _card("W3", "ready")])
    assert _close(path, "--reason", "waiting on W2 to land") == _OK
    assert "waiting on W2 to land" in _ledger(tmp_path)


def test_close_gate_says_the_verdict_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--close-gate` is the read half (W1202): refused with ready cards, ok when named."""
    path = _state(tmp_path, [_card("W1", "working"), _card("W2", "ready")])
    before = path.read_text(encoding="utf-8")
    gate = ["--state", str(path), "--close-gate"]
    assert cli.main(gate) == _REFUSED
    assert "ready and unblocked: 1; top: W2" in capsys.readouterr().out
    assert cli.main([*gate, "--reason", "waiting on W2"]) == _OK
    assert cli.main([*gate, "--blocked-by", "W1"]) == _OK
    assert path.read_text(encoding="utf-8") == before
    assert not (tmp_path / "paths-forward.ledger").exists()


def test_a_reason_or_blocker_that_names_no_card_of_the_queue_is_refused(tmp_path: Path) -> None:
    """The control for the escape hatch: prose, a missing card and a done one all stay refused."""
    path = _state(tmp_path, [_card("W1", "done"), _card("W2", "ready")])
    assert _close(path, "--reason", "I am tired") == _REFUSED
    assert _close(path, "--reason", "waiting on W99") == _REFUSED
    assert _close(path, "--blocked-by", "W99") == _REFUSED
    assert _close(path, "--blocked-by", "W1") == _REFUSED
    assert _locked(path)

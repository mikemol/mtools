# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Folding per-file debt cards into one idiom card (mtools:W1371), through the real writer.

⚑ THE CONTROLS ARE WHAT MUST NOT HAPPEN: folding a card the ledger does not account for (debt
would vanish with nothing to show), a second fold that mints or drops again, a done card being
touched, and an edge left pointing at a dropped card. Each test reads the queue back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mikemol.pathsforward.model import strlist, text
from mikemol.pathsforward.store import load

from mikemol.debtplan.fold import fold, survey
from mikemol.debtplan.mint import MintRefusedError, Style, mint
from mikemol.debtplan.plan import Plan
from mikemol.debtplan.queue import Queue
from mikemol.debtplan.rows import Row

if TYPE_CHECKING:
    from pathlib import Path

PREFIX = "p: "
IDIOM = "mypy"
HOW = "run the typed-args codemod"
TWO = 2
THREE = 3


def _chain() -> Plan:
    # b waits on a and c waits on b, so the per-file cards carry edges.
    rows = (
        Row("a.py", 3, (), ("b.py",)),
        Row("b.py", 2, ("a.py",), ("c.py",)),
        Row("c.py", 1, ("b.py",), ()),
    )
    return Plan(rows, {})


def _minted(tmp_path: Path) -> Queue:
    queue = Queue(tmp_path / "pf.json")
    assert queue.run("--init")[0] == 0
    mint(_chain(), queue, Style(PREFIX))
    return queue


def _status(queue: Queue, symbol: str) -> str:
    for record in load(queue.state).waypoints:
        if text(record, "symbol") == symbol:
            return text(record, "status")
    return "dropped"


def test_the_survey_names_the_open_cards_and_the_set_difference_both_ways(tmp_path: Path) -> None:
    """Three cards, the ledger the same three files: nothing on either side alone."""
    queue = _minted(tmp_path)
    seen = survey(queue, _chain(), Style(PREFIX))
    assert set(seen.cards) == {"a.py", "b.py", "c.py"}
    assert seen.agrees
    assert not seen.only_cards
    assert not seen.only_ledger


def test_a_card_the_ledger_does_not_account_for_refuses_the_fold_and_writes_nothing(
    tmp_path: Path,
) -> None:
    """A ledger without c.py would lose c's debt: refused, the cards all still open."""
    queue = _minted(tmp_path)
    short = Plan(_chain().rows[:2], {})
    assert survey(queue, short, Style(PREFIX)).only_cards == ("c.py",)
    with pytest.raises(MintRefusedError):
        fold(short, queue, Style(PREFIX), IDIOM, HOW)
    assert not queue.cards(Style(PREFIX).idiom)
    assert len(queue.cards(PREFIX)) == THREE


def test_a_fold_mints_the_idiom_card_and_drops_every_per_file_card_onto_it(tmp_path: Path) -> None:
    """Three cards become one: the file cards leave the queue, the idiom card stays."""
    queue = _minted(tmp_path)
    assert fold(_chain(), queue, Style(PREFIX), IDIOM, HOW) == THREE
    assert not queue.cards(PREFIX)
    assert set(queue.cards(Style(PREFIX).idiom)) == {IDIOM}


def test_a_second_fold_drops_and_mints_nothing_new(tmp_path: Path) -> None:
    """Idempotent: no open per-file card is left, and the idiom card is the same card."""
    queue = _minted(tmp_path)
    fold(_chain(), queue, Style(PREFIX), IDIOM, HOW)
    before = [text(r, "symbol") for r in load(queue.state).waypoints]
    assert fold(_chain(), queue, Style(PREFIX), IDIOM, HOW) == 0
    assert [text(r, "symbol") for r in load(queue.state).waypoints] == before


def test_a_done_per_file_card_is_left_where_it_is(tmp_path: Path) -> None:
    """A card that records finished work is not an open work item and is not folded."""
    queue = _minted(tmp_path)
    leaf = queue.cards(PREFIX)["c.py"]
    assert queue.run("--update", leaf.symbol, "--status", "done")[0] == 0
    assert fold(_chain(), queue, Style(PREFIX), IDIOM, HOW) == TWO
    assert _status(queue, leaf.symbol) == "done"


def test_no_edge_is_left_pointing_at_a_folded_card(tmp_path: Path) -> None:
    """The writer repoints every blocked_on and enables that named a dropped card."""
    queue = _minted(tmp_path)
    fold(_chain(), queue, Style(PREFIX), IDIOM, HOW)
    live = {text(r, "symbol") for r in load(queue.state).waypoints}
    for record in load(queue.state).waypoints:
        assert set(strlist(record, "blocked_on")) <= live
        assert set(strlist(record, "enables")) <= live

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One card for a whole ledger (mtools:W1370): many files, one card, never one per file.

⚑ THE CONTROLS ARE WHAT MUST NOT HAPPEN: a card per file, a second card on a second run, and an
idiom card read as a file card (or the other way round). Each test goes through the real writer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mikemol.pathsforward.cli import main as pf_main
from mikemol.pathsforward.model import text
from mikemol.pathsforward.store import load

from mikemol.debtplan.mint import Minted, MintRefusedError, Style, mint_idiom
from mikemol.debtplan.plan import Plan
from mikemol.debtplan.queue import Queue
from mikemol.debtplan.rows import Row

if TYPE_CHECKING:
    from pathlib import Path

PREFIX = "p: "
IDIOM = "mypy"
HOW = "run mikemol-pycodemod typed-args over the repo"


def _queue(tmp_path: Path) -> Queue:
    queue = Queue(tmp_path / "pf.json")
    assert queue.run("--init")[0] == 0
    return queue


def _plan() -> Plan:
    rows = (Row("a.py", 3, (), ()), Row("b.py", 2, (), ()), Row("c.py", 1, (), ()))
    return Plan(rows, {})


def _titles(queue: Queue) -> list[str]:
    return [text(record, "title") for record in load(queue.state).waypoints]


def test_many_files_make_one_card_with_the_counts_in_its_title(tmp_path: Path) -> None:
    """Three files, six findings: one card, titled with both, and no per-file card."""
    queue = _queue(tmp_path)
    assert mint_idiom(_plan(), queue, Style(PREFIX), IDIOM, HOW) == Minted(1, 1, 0)
    assert _titles(queue) == ["p idiom: mypy (3 files, 6 findings)"]
    assert not queue.cards(PREFIX)


def test_a_second_run_rewrites_the_one_card_and_mints_none(tmp_path: Path) -> None:
    """The key is the idiom's name: a re-run adds nothing and the title follows the counts."""
    queue = _queue(tmp_path)
    mint_idiom(_plan(), queue, Style(PREFIX), IDIOM, HOW)
    shrunk = Plan((Row("a.py", 1, (), ()),), {})
    assert mint_idiom(shrunk, queue, Style(PREFIX), IDIOM, HOW) == Minted(0, 1, 0)
    assert _titles(queue) == ["p idiom: mypy (1 files, 1 findings)"]


def test_the_step_names_the_run_and_the_card_is_ready(tmp_path: Path) -> None:
    """The next step says how it retires, and where the per-file rows live."""
    queue = _queue(tmp_path)
    mint_idiom(_plan(), queue, Style(PREFIX), IDIOM, HOW)
    record = load(queue.state).waypoints[0]
    assert text(record, "status") == "ready"
    assert text(record, "next_bounded_step").startswith(HOW)
    assert "the per-file rows are the ledger" in text(record, "next_bounded_step")


def test_an_empty_ledger_retires_the_card_once(tmp_path: Path) -> None:
    """Nothing left to pay down: the card is done, and a further run retires nothing."""
    queue = _queue(tmp_path)
    mint_idiom(_plan(), queue, Style(PREFIX), IDIOM, HOW)
    empty = Plan((), {})
    assert mint_idiom(empty, queue, Style(PREFIX), IDIOM, HOW) == Minted(0, 1, 1)
    assert mint_idiom(empty, queue, Style(PREFIX), IDIOM, HOW) == Minted(0, 1, 0)
    assert text(load(queue.state).waypoints[0], "status") == "done"


def test_a_card_being_worked_keeps_its_status(tmp_path: Path) -> None:
    """A re-run must not demote the card in hand."""
    queue = _queue(tmp_path)
    mint_idiom(_plan(), queue, Style(PREFIX), IDIOM, HOW)
    symbol = text(load(queue.state).waypoints[0], "symbol")
    assert queue.run("--update", symbol, "--status", "working")[0] == 0
    mint_idiom(_plan(), queue, Style(PREFIX), IDIOM, HOW)
    assert text(load(queue.state).waypoints[0], "status") == "working"


def test_the_idiom_prefix_is_not_the_file_prefix_and_does_not_start_with_it() -> None:
    """`p debt idiom: ` and `p debt: ` differ, so neither kind of card is read as the other."""
    style = Style("p debt: ")
    assert style.idiom == "p debt idiom: "
    assert not style.idiom.startswith(style.prefix)
    assert not style.prefix.startswith(style.idiom)


def test_a_refused_step_is_raised_and_the_lock_is_released(tmp_path: Path) -> None:
    """The writer's refusal is loud, and a later mint can take the lock."""
    state = tmp_path / "pf.json"
    assert Queue(state).run("--init")[0] == 0

    def refusing(argv: list[str]) -> int:
        return 2 if "--update" in argv else pf_main(argv)

    with pytest.raises(MintRefusedError):
        mint_idiom(_plan(), Queue(state, refusing), Style(PREFIX), IDIOM, HOW)
    assert Queue(state).run("--lock", "next")[0] == 0

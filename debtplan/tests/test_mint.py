# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Mint: a queue kept in step with a plan, through the real writer, under its tick lock."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from mikemol.pathsforward.cli import main as pf_main
from mikemol.pathsforward.model import strlist, text
from mikemol.pathsforward.store import load

from mikemol.debtplan.mint import (
    HOW,
    TOUCHES,
    VECTOR,
    Minted,
    MintRefusedError,
    Style,
    card_title,
    mint,
    step_for,
)
from mikemol.debtplan.plan import Plan
from mikemol.debtplan.queue import Queue
from mikemol.debtplan.rows import Row

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import Json

PREFIX = "p: "
THREE = 3
NINE = 9
OTHER_VECTOR = "WV:1/R:T/E:Y/C:L/I:L/A:L/X:P/S:U/F:U/W:N"


def _queue(tmp_path: Path) -> Queue:
    """Initialise a state file with the real writer.

    Returns:
        A queue over it.

    """
    queue = Queue(tmp_path / "pf.json")
    assert queue.run("--init")[0] == 0
    return queue


def _chain() -> Plan:
    """Build a plan where b waits on a, and c waits on both (so c's wait on a is implied).

    Returns:
        The plan, in pay-down order.

    """
    return Plan(
        (
            Row("a.py", THREE, (), ("b.py", "c.py")),
            Row("b.py", 2, ("a.py",), ("c.py",)),
            Row("c.py", 1, ("a.py", "b.py"), ()),
        ),
        {},
    )


def _card(queue: Queue, symbol: str) -> Json:
    """Find a card's record in the state file.

    Returns:
        The record with that symbol; the test fails when there is none.

    """
    for record in load(queue.state).waypoints:
        if text(record, "symbol") == symbol:
            return record
    return pytest.fail(f"no card {symbol}")


def test_a_first_mint_adds_a_card_for_every_file_and_rewrites_each(tmp_path: Path) -> None:
    """Three files make three cards, each rewritten, none retired."""
    queue = _queue(tmp_path)
    assert mint(_chain(), queue, Style(PREFIX)) == Minted(THREE, THREE, 0)
    assert set(queue.cards(PREFIX)) == {"a.py", "b.py", "c.py"}


def test_a_card_carries_its_title_step_tags_and_vector(tmp_path: Path) -> None:
    """A ready file says to write it; a waiting one says what to clean first."""
    queue = _queue(tmp_path)
    mint(_chain(), queue, Style(PREFIX))
    ready, waiting = _card(queue, "W1"), _card(queue, "W2")
    assert text(ready, "title") == "p: a.py (3 findings)"
    assert text(ready, "next_bounded_step") == step_for(_chain().rows[0], HOW)
    assert text(waiting, "next_bounded_step") == "Waits on 1 debt file(s): clean those first"
    assert strlist(ready, "touches") == list(TOUCHES)
    assert text(ready, "vector") == VECTOR
    assert text(ready, "blocked_kind") == "agent"


def test_edges_are_the_direct_waits_and_not_the_whole_closure(tmp_path: Path) -> None:
    """C waits on a through b, so c lists b alone and a lists only b as what it is in front of."""
    queue = _queue(tmp_path)
    mint(_chain(), queue, Style(PREFIX))
    a, b, c = (_card(queue, f"W{n}") for n in (1, 2, THREE))
    assert strlist(a, "enables") == ["W2"]
    assert strlist(b, "enables") == ["W3"]
    assert strlist(c, "enables") == []
    assert strlist(a, "blocked_on") == []
    assert strlist(b, "blocked_on") == ["W1"]
    assert strlist(c, "blocked_on") == ["W2"]


def test_a_file_that_waits_is_blocked_and_one_that_does_not_is_ready(tmp_path: Path) -> None:
    """Status follows the direct waits."""
    queue = _queue(tmp_path)
    mint(_chain(), queue, Style(PREFIX))
    got = {file: card.status for file, card in queue.cards(PREFIX).items()}
    assert got == {"a.py": "ready", "b.py": "blocked", "c.py": "blocked"}


def test_minting_again_is_a_sync_not_a_duplicate(tmp_path: Path) -> None:
    """The second run adds nothing, rewrites each card, and leaves one card per file."""
    queue = _queue(tmp_path)
    mint(_chain(), queue, Style(PREFIX))
    assert mint(_chain(), queue, Style(PREFIX)) == Minted(0, THREE, 0)
    assert len(queue.cards(PREFIX)) == THREE


def test_a_card_being_worked_keeps_its_status_and_is_still_rewritten(tmp_path: Path) -> None:
    """A re-mint does not demote the card in hand, but its title and step follow the plan."""
    queue = _queue(tmp_path)
    mint(_chain(), queue, Style(PREFIX))
    queue.run("--update", "W1", "--status", "working")
    grown = Plan((Row("a.py", NINE, (), ("b.py",)), *_chain().rows[1:]), {})
    mint(grown, queue, Style(PREFIX))
    card = _card(queue, "W1")
    assert text(card, "status") == "working"
    assert text(card, "title") == "p: a.py (9 findings)"


def test_a_card_whose_file_left_the_plan_is_retired_once(tmp_path: Path) -> None:
    """The file's card is marked done with a reason, and a third run does not retire it again."""
    queue = _queue(tmp_path)
    mint(_chain(), queue, Style(PREFIX))
    smaller = Plan(_chain().rows[:1], {})
    assert mint(smaller, queue, Style(PREFIX)) == Minted(0, 1, 2)
    assert queue.cards(PREFIX)["b.py"].status == "done"
    assert "ledger row gone" in text(_card(queue, "W2"), "evidence")
    assert mint(smaller, queue, Style(PREFIX)) == Minted(0, 1, 0)


def test_a_done_card_whose_file_returns_is_reopened(tmp_path: Path) -> None:
    """A file back in the ledger is work again: its done card is rewritten to ready or blocked."""
    queue = _queue(tmp_path)
    mint(_chain(), queue, Style(PREFIX))
    mint(Plan(_chain().rows[:1], {}), queue, Style(PREFIX))
    mint(_chain(), queue, Style(PREFIX))
    assert queue.cards(PREFIX)["b.py"].status == "blocked"


def test_a_lock_held_by_another_refuses_the_mint_and_is_left_held(tmp_path: Path) -> None:
    """The mint does not take over a tick, and does not release a lock that is not its own."""
    queue = _queue(tmp_path)
    assert queue.run("--lock", "someone")[0] == 0
    with pytest.raises(MintRefusedError, match="cannot take the tick lock"):
        mint(_chain(), queue, Style(PREFIX))
    assert queue.run("--lock", "someone-else")[0] != 0
    assert queue.cards(PREFIX) == {}


def test_the_lock_is_released_after_a_sync(tmp_path: Path) -> None:
    """After a mint the lock is free for the next holder."""
    queue = _queue(tmp_path)
    mint(_chain(), queue, Style(PREFIX))
    assert queue.run("--lock", "next")[0] == 0


def test_a_refused_step_stops_the_sync_names_it_and_releases_the_lock(tmp_path: Path) -> None:
    """The writer's own words are in the error, and the lock is free afterwards."""
    state = _queue(tmp_path).state

    def refusing(argv: list[str]) -> int:
        if "--update" in argv:
            sys.stderr.write("no way\n")
            return 2
        return pf_main(argv)

    with pytest.raises(MintRefusedError, match=r"--update refused \(exit 2\): no way"):
        mint(_chain(), Queue(state, refusing), Style(PREFIX))
    assert Queue(state).run("--lock", "next")[0] == 0


def test_an_added_card_that_cannot_be_read_back_is_refused(tmp_path: Path) -> None:
    """A writer that says it added a card it did not add must not read as a queue in step."""
    state = _queue(tmp_path).state

    def forgetful(argv: list[str]) -> int:
        return 0 if "--add" in argv else pf_main(argv)

    with pytest.raises(MintRefusedError, match=r"card for a\.py was added and could not be read"):
        mint(_chain(), Queue(state, forgetful), Style(PREFIX))


def test_the_style_overrides_the_step_the_tags_and_the_vector(tmp_path: Path) -> None:
    """A caller's wording, tags and vector are what the card carries."""
    queue = _queue(tmp_path)
    style = Style(PREFIX, how="so it passes ruff", touches=("typing", "mypy"), vector=OTHER_VECTOR)
    mint(_chain(), queue, style)
    card = _card(queue, "W1")
    assert "so it passes ruff" in text(card, "next_bounded_step")
    assert strlist(card, "touches") == ["typing", "mypy"]
    assert text(card, "vector") == OTHER_VECTOR


def test_the_title_and_step_for_a_ready_and_a_waiting_row() -> None:
    """The title carries the count; the ready step names the count, the other the waits."""
    assert card_title("a.py", THREE, PREFIX) == "p: a.py (3 findings)"
    assert step_for(Row("a.py", THREE, (), ()), "x") == (
        "Whole-file Write clearing 3 finding(s) x, then lower the ledger row"
    )
    assert step_for(Row("a.py", 1, ("b.py", "c.py"), ()), "x") == (
        "Waits on 2 debt file(s): clean those first"
    )

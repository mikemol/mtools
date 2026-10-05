# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Mint: a queue kept in step with a plan, through the real writer, under its tick lock."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from mikemol.importdag.resolve import Unsettled
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
    ambiguity_step,
    ambiguity_title,
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
BLOCKERS = "p ambiguity: "
"""The ambiguity prefix `Style(PREFIX)` derives."""

THREE = 3
NINE = 9
OTHER_VECTOR = "WV:1/R:T/E:Y/C:L/I:L/A:L/X:P/S:U/F:U/W:N"
CANDIDATES = ("p/m.py", "q/m.py")


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


def _held() -> Plan:
    """Build a plan where x imports the ambiguous name m and y waits on x, so both are held.

    Returns:
        The plan, with the one name unsettled in x.

    """
    return Plan(
        (
            Row("x.py", 2, (), ("y.py",), ("m",)),
            Row("y.py", 1, ("x.py",), (), ("m",)),
        ),
        {"x.py": (Unsettled("m", CANDIDATES),)},
    )


def _settled() -> Plan:
    """Build the plan `_held` becomes once m is settled: the same files, nothing unsettled.

    Returns:
        The plan.

    """
    return Plan((Row("x.py", 2, (), ("y.py",)), Row("y.py", 1, ("x.py",), ())), {})


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
    assert text(waiting, "next_bounded_step") == "Waits on 1 debt file(s) to clean first"
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
        "Waits on 2 debt file(s) to clean first"
    )


def test_the_step_for_a_row_held_by_an_unsettled_name_says_so() -> None:
    """A name alone, and a name with files, each say what is to be settled."""
    assert step_for(Row("a.py", 1, (), (), ("m",)), "x") == (
        "Waits on 1 ambiguous import(s) to settle first"
    )
    assert step_for(Row("a.py", 1, ("b.py", "c.py"), (), ("m",)), "x") == (
        "Waits on 2 debt file(s) to clean and 1 ambiguous import(s) to settle first"
    )


def test_the_ambiguity_title_and_step_name_the_count_the_candidates_and_the_way_out() -> None:
    """The title counts the candidate files; the step lists them and the two ways to settle."""
    assert ambiguity_title("m", 2, BLOCKERS) == "p ambiguity: m (2 files)"
    assert ambiguity_step("m", CANDIDATES) == (
        "Decide which of p/m.py, q/m.py the import `m` means: change the importer, "
        "or declare it in the resolutions file"
    )


def test_an_unsettled_name_gets_a_card_of_its_own(tmp_path: Path) -> None:
    """Two file cards and one ambiguity card; the ambiguity prefix keys a separate set of cards."""
    queue = _queue(tmp_path)
    assert mint(_held(), queue, Style(PREFIX)) == Minted(THREE, THREE, 0)
    assert set(queue.cards(PREFIX)) == {"x.py", "y.py"}
    assert set(queue.cards(BLOCKERS)) == {"m"}
    assert text(_card(queue, "W3"), "title") == "p ambiguity: m (2 files)"


def test_the_file_cards_wait_on_the_ambiguity_card_and_it_enables_them(tmp_path: Path) -> None:
    """X waits on the name; y waits on x and on the name; the name is in front of both."""
    queue = _queue(tmp_path)
    mint(_held(), queue, Style(PREFIX))
    x, y, name = (_card(queue, f"W{n}") for n in (1, 2, THREE))
    assert strlist(x, "blocked_on") == ["W3"]
    assert strlist(y, "blocked_on") == ["W1", "W3"]
    assert strlist(name, "enables") == ["W1", "W2"]
    assert (text(x, "status"), text(y, "status")) == ("blocked", "blocked")
    assert "ambiguous import(s) to settle" in text(x, "next_bounded_step")


def test_the_ambiguity_card_is_ready_work_that_says_what_settles_it(tmp_path: Path) -> None:
    """Nothing blocks the decision: the card is ready, with the candidates and the tags."""
    queue = _queue(tmp_path)
    mint(_held(), queue, Style(PREFIX))
    name = _card(queue, "W3")
    assert text(name, "status") == "ready"
    assert text(name, "next_bounded_step") == ambiguity_step("m", CANDIDATES)
    assert strlist(name, "touches") == list(TOUCHES)
    assert strlist(name, "blocked_on") == []
    assert text(name, "vector") == VECTOR


def test_an_ambiguity_card_being_worked_keeps_its_status(tmp_path: Path) -> None:
    """A re-mint does not demote the decision in hand."""
    queue = _queue(tmp_path)
    mint(_held(), queue, Style(PREFIX))
    queue.run("--update", "W3", "--status", "working")
    assert mint(_held(), queue, Style(PREFIX)) == Minted(0, THREE, 0)
    assert text(_card(queue, "W3"), "status") == "working"


def test_a_name_that_is_settled_retires_its_card_once_and_frees_the_files(tmp_path: Path) -> None:
    """The card is marked done with a reason; the file it held becomes ready."""
    queue = _queue(tmp_path)
    mint(_held(), queue, Style(PREFIX))
    assert mint(_settled(), queue, Style(PREFIX)) == Minted(0, 2, 1)
    assert queue.cards(BLOCKERS)["m"].status == "done"
    assert "no longer ambiguous" in text(_card(queue, "W3"), "evidence")
    assert queue.cards(PREFIX)["x.py"].status == "ready"
    assert mint(_settled(), queue, Style(PREFIX)) == Minted(0, 2, 0)


def test_an_ambiguity_card_that_cannot_be_read_back_is_refused(tmp_path: Path) -> None:
    """A writer that says it added the decision card and did not must not read as in step."""
    state = _queue(tmp_path).state

    def forgetful(argv: list[str]) -> int:
        added = "--add" in argv and any(arg.startswith(BLOCKERS) for arg in argv)
        return 0 if added else pf_main(argv)

    with pytest.raises(MintRefusedError, match=r"ambiguity card for m was added and could not be"):
        mint(_held(), Queue(state, forgetful), Style(PREFIX))


def test_the_ambiguity_prefix_is_the_file_prefix_without_its_colon_then_ambiguity() -> None:
    """`p: ` gives `p ambiguity: `, which neither starts with nor is started by the file prefix."""
    assert Style(PREFIX).ambiguity == BLOCKERS


def test_a_prefix_that_would_swallow_its_ambiguity_prefix_is_refused() -> None:
    """With no `: ` to strip, the ambiguity cards would be read as file cards and retired."""
    with pytest.raises(ValueError, match="overlap"):
        Style("p")

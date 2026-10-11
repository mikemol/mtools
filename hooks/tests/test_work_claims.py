# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pure parts of a session claiming the touches of its working card.

W993. ⚑ THE WORKING CARD'S CLAIMS ARE THE POSITIVE CONTROL: the ready card that claims nothing, the
session that is not found and the claim another owner holds only mean something beside a queue
whose working card does produce its labels and a plan that does take them.
"""

from __future__ import annotations

from mikemol.hooks import work_claims

REPO = "mtools"
ME = "100:555"
THEM = "200:777"
BAZEL = "claim:label:touch:mtools:bazel"
TYPING = "claim:label:touch:mtools:typing"
FENCE = "claim:label:touch:mtools:fence"
STARTTIME_AT = 19
PARENT = 42
HOOK_SHELL = 10
SESSION = 30


def _card(status: str, *touches: str | int) -> dict[str, object]:
    return {"symbol": "W1", "status": status, "touches": list(touches)}


def _stat(pid: int, comm: str, ppid: int, start: int) -> str:
    """Build a stat line with the state, parent and start-time fields where the kernel puts them.

    Returns:
        the line.

    """
    after = ["S", str(ppid)] + ["0"] * (STARTTIME_AT - 2) + [str(start), "0"]
    return f"{pid} ({comm}) " + " ".join(after)


def test_a_working_card_claims_each_of_its_tags_sorted_and_deduplicated() -> None:
    """The control: two working cards sharing a tag give each tag once, in order."""
    queue = {"waypoints": [_card("working", "typing", "bazel"), _card("working", "bazel")]}
    assert work_claims.wanted(queue, REPO) == [BAZEL, TYPING]


def test_only_a_working_card_claims() -> None:
    """Ready, blocked and done cards are plans or history, not a presence."""
    queue = {"waypoints": [_card(s, "bazel") for s in ("ready", "blocked", "done", "dropped")]}
    assert work_claims.wanted(queue, REPO) == []


def test_an_unreadable_queue_claims_nothing() -> None:
    """A missing, malformed or odd-shaped queue is no claims, never an error."""
    assert work_claims.wanted(None, REPO) == []
    assert work_claims.wanted({"waypoints": "x"}, REPO) == []
    odd = {"waypoints": [{"status": "working", "touches": "bazel"}, 5, {"status": "working"}]}
    assert work_claims.wanted(odd, REPO) == []
    assert work_claims.wanted({"waypoints": [_card("working", "", 7)]}, REPO) == []


def test_the_start_time_and_parent_come_from_after_the_comm_field() -> None:
    """A comm with spaces and a closing parenthesis cannot shift the fields."""
    stat = _stat(100, "we ird) name", PARENT, 555)
    assert work_claims.starttime_of(stat) == "555"
    assert work_claims.parent_of(stat) == PARENT
    assert work_claims.owner_string(100, stat) == ME
    assert work_claims.starttime_of("1 (x) S") is None
    assert work_claims.owner_string(1, "1 (x) S") is None
    assert work_claims.parent_of("1 (x)") is None


def test_the_session_is_the_nearest_ancestor_with_the_name() -> None:
    """Walk up from the hook's shell to the first claude, skipping the others above it."""
    names = {10: "bash", 20: "sh", 30: "claude", 40: "claude", 50: "systemd"}
    parents = {10: 20, 20: 30, 30: 40, 40: 50, 50: 1}
    assert work_claims.session_pid(HOOK_SHELL, names.get, parents.get) == SESSION


def test_no_session_ancestor_is_none_and_the_walk_is_bounded() -> None:
    """A tree with no claude, or a parent loop, ends at None instead of spinning."""
    names = {10: "bash", 20: "sh"}
    nobody: dict[int, int] = {}
    assert work_claims.session_pid(HOOK_SHELL, names.get, {10: 20, 20: 1}.get) is None
    assert work_claims.session_pid(HOOK_SHELL, names.get, {10: 20, 20: 10}.get) is None
    assert work_claims.session_pid(1, names.get, nobody.get) is None


def test_the_claims_listing_reads_label_and_owner() -> None:
    """Only touch claims with an owner are read; other lines are skipped."""
    listing = (
        f"{BAZEL} owner={ME} id=aaaaaaaaaaaa age=5s\n"
        "claim:path:/x owner=1:1 id=bbbbbbbbbbbb age=1s\n"
        f"{TYPING} id=cccccccccccc age=2s\n"
        "(no claims)\n"
    )
    assert work_claims.claims_of(listing) == {BAZEL: ME}


def test_the_plan_takes_what_is_missing_and_releases_only_its_own_unwanted() -> None:
    """Held by me and wanted: nothing; wanted and absent: take; mine and unwanted: release."""
    held = {BAZEL: ME, TYPING: ME, "claim:label:touch:mtools:hooks": THEM}
    got = work_claims.plan([BAZEL, FENCE], held, ME)
    assert got.take == (FENCE,)
    assert got.release == (TYPING,)


def test_a_claim_another_owner_holds_is_taken_again_to_learn_the_holder() -> None:
    """Wanted and held by someone else is not mine, so the plan tries it and the ledger answers."""
    got = work_claims.plan([BAZEL], {BAZEL: THEM}, ME)
    assert got.take == (BAZEL,)
    assert got.release == ()


def test_a_refusal_becomes_one_advisory_line_naming_the_holder() -> None:
    """The ledger's last line, minus its prefix, is the detail; an empty one still says held."""
    said = "membudget: REFUSED — fence.admit: waiting (CLAIMED): x is held by 200:777\n"
    line = work_claims.advice(BAZEL, said)
    assert line.startswith("work claim: mtools:bazel is held elsewhere (")
    assert "held by 200:777" in line
    assert "(held)" in work_claims.advice(BAZEL, "")

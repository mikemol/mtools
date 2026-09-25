# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the mutations: typed, all-or-nothing, and honest about the block count."""

from __future__ import annotations

import copy

import pytest

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import State, validate

Rec = dict[str, object]

_NOW = "2026-09-23T12:00:00Z"
_DATE = "2026-09-23"
_COUNTER = 3
_MINTED = 4
_OLD_TICKS = 5
_SET_TICKS = 9
_ESCALATE = 16
_QUIET = (3, 5, 15, 17, 32)


def _wp(sym: str, status: str = "ready", **extra: object) -> Rec:
    """Build a waypoint.

    Returns:
        the waypoint.

    """
    w: Rec = {
        "symbol": sym,
        "title": sym,
        "status": status,
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "step",
        "evidence": "",
        "ticks_blocked": 0,
    }
    w.update(extra)
    return w


def _blocked(sym: str, count: int = 0) -> Rec:
    """Build a blocked waypoint.

    Returns:
        the waypoint.

    """
    return _wp(sym, "blocked", blocked_on=["mikemol"], blocked_kind="human", ticks_blocked=count)


def _state(*waypoints: Rec) -> State:
    """Build a state with W3 in residue.

    Returns:
        the state.

    """
    return validate(
        {
            "counter": _COUNTER,
            "heartbeat": "h0",
            "waypoints": list(waypoints) or [_wp("W1"), _wp("W2")],
            "residue": [{"symbol": "W3", "reason": "why", "dropped_at": "d"}],
        }
    )


def test_find_resolves_a_live_symbol() -> None:
    """A live symbol resolves to its waypoint."""
    assert ops.find(_state(), "W2")["symbol"] == "W2"


def test_find_names_the_residue_reason() -> None:
    """A residue symbol is refused with its reason (skill section 2)."""
    with pytest.raises(ops.RefusedError, match=r"W3 is residue .*why"):
        ops.find(_state(), "W3")


def test_find_refuses_an_unissued_symbol() -> None:
    """A symbol in neither list is refused, never guessed."""
    with pytest.raises(ops.RefusedError, match="in neither"):
        ops.find(_state(), "W9")


@pytest.mark.parametrize(
    "upd",
    [ops.Update(status="bogus"), ops.Update(blocked_kind="robot"), ops.Update(ticks_blocked=-1)],
)
def test_an_out_of_enum_update_is_refused_and_changes_nothing(upd: ops.Update) -> None:
    """`status=bogus` (el-openglo accepted it) and its kin are refused, and nothing changes."""
    state = _state()
    before = copy.deepcopy(state.doc)
    with pytest.raises(ops.RefusedError, match=r"is not one of|is negative"):
        ops.update(state, "W1", upd, _NOW)
    assert state.doc == before


def test_blocking_without_a_party_is_refused_whole() -> None:
    """A status=blocked with no party is refused, and the next step set beside it is not kept."""
    state = _state()
    with pytest.raises(ops.RefusedError, match="blocked needs"):
        ops.update(state, "W1", ops.Update(status="blocked", next_step="new"), _NOW)
    assert state.waypoints[0]["next_bounded_step"] == "step"


def test_ready_clears_the_block() -> None:
    """Moving to ready clears blocked_on and blocked_kind, and resets the count."""
    w = ops.update(_state(_blocked("W1", _OLD_TICKS)), "W1", ops.Update(status="ready"), _NOW)
    assert (w["blocked_on"], w["blocked_kind"], w["ticks_blocked"]) == ([], None, 0)


def test_done_clears_the_next_step() -> None:
    """Moving to done clears the next step."""
    w = ops.update(_state(), "W1", ops.Update(status="done"), _NOW)
    assert (w["status"], w["next_bounded_step"]) == ("done", "")


def test_blocking_resets_the_count() -> None:
    """Blocking a waypoint resets ticks_blocked (sre never reset it)."""
    upd = ops.Update(status="blocked", blocked_on=("agent-2",), blocked_kind="agent")
    w = ops.update(_state(_wp("W1", ticks_blocked=_OLD_TICKS)), "W1", upd, _NOW)
    assert (w["ticks_blocked"], w["blocked_on"]) == (0, ["agent-2"])


def test_a_new_party_resets_the_count() -> None:
    """Changing who a block is on resets the count; something about it changed."""
    upd = ops.Update(blocked_on=("agent-9",))
    w = ops.update(_state(_blocked("W1", _OLD_TICKS)), "W1", upd, _NOW)
    assert w["ticks_blocked"] == 0


def test_an_unrelated_edit_keeps_the_count() -> None:
    """An edit that does not touch the block keeps the count (positive control for the reset)."""
    w = ops.update(_state(_blocked("W1", _OLD_TICKS)), "W1", ops.Update(next_step="n"), _NOW)
    assert (w["ticks_blocked"], w["next_bounded_step"]) == (_OLD_TICKS, "n")


def test_an_explicit_count_wins() -> None:
    """An explicit ticks_blocked is set after any reset."""
    w = ops.update(_state(_blocked("W1")), "W1", ops.Update(ticks_blocked=_SET_TICKS), _NOW)
    assert w["ticks_blocked"] == _SET_TICKS


def test_evidence_is_appended_with_its_date() -> None:
    """Evidence is appended with a date, starting clean when there was none."""
    state = _state()
    ops.update(state, "W1", ops.Update(evidence_append="a"), _NOW)
    w = ops.update(state, "W1", ops.Update(evidence_append="b"), _NOW)
    assert w["evidence"] == f"{_DATE}: a | {_DATE}: b"


def test_an_update_stamps_last_worked() -> None:
    """Every update stamps last_worked."""
    assert ops.update(_state(), "W1", ops.Update(), _NOW)["last_worked"] == _NOW


def test_add_mints_the_next_symbol() -> None:
    """Adding mints W<counter+1> as ready and advances the counter."""
    state = _state()
    sym = ops.add(state, ops.Draft("new", "first step", ("W1",), ("tag",)), _NOW)
    assert (sym, state.doc["counter"], state.waypoints[-1]["enables"]) == (
        f"W{_MINTED}",
        _MINTED,
        ["W1"],
    )


@pytest.mark.parametrize(
    ("lock", "during"),
    [
        ({"holder": "tick", "taken_at": "2026-09-23T11:50:00Z"}, "tick"),
        ({"holder": "tick", "taken_at": "2026-09-23T11:00:00Z"}, "interrupt"),
        ({"holder": "tick", "taken_at": "unreadable"}, "interrupt"),
        (None, "interrupt"),
    ],
)
def test_add_stamps_minted_during_from_the_lock(lock: Rec | None, during: str) -> None:
    """⚑ A mint under a fresh tick lock reads tick; no lock, a stale or unreadable one, interrupt.

    nemik, 2026-09-25: the tool derives it, so a caller cannot answer it from recall.
    """
    state = _state()
    if lock is not None:
        state.doc["lock"] = lock
    ops.add(state, ops.Draft("new"), _NOW)
    assert (state.waypoints[-1]["minted_during"], state.waypoints[-1]["issued_at"]) == (
        during,
        _NOW,
    )


@pytest.mark.parametrize(("ref", "stored"), [("W24", "W24"), ("", None)])
def test_add_records_caused_by(ref: str, stored: str | None) -> None:
    """⚑ The optional cause is recorded on the minted waypoint; absent, it is null."""
    state = _state()
    ops.add(state, ops.Draft("new", caused_by=ref), _NOW)
    assert state.waypoints[-1]["caused_by"] == stored


@pytest.mark.parametrize(
    "draft",
    [
        ops.Draft("  "),
        ops.Draft("t", enables=("mikemol",)),
        # ⚑ nemik 2026-09-25: el-openglo W49/W50/W52/W59 stored "W46,W35" as ONE edge that
        # resolved to nothing. Refused here, never stored.
        ops.Draft("t", enables=("W46,W35",)),
        ops.Draft("t", caused_by="two words"),
    ],
)
def test_a_refused_add_mints_nothing(draft: ops.Draft) -> None:
    """A refused add leaves the counter and the list untouched (validate before minting)."""
    state = _state()
    with pytest.raises(ops.RefusedError, match="nothing minted"):
        ops.add(state, draft, _NOW)
    assert (state.doc["counter"], [w["symbol"] for w in state.waypoints]) == (
        _COUNTER,
        ["W1", "W2"],
    )


@pytest.mark.parametrize("where", ["waypoints", "residue"])
def test_add_never_re_mints_a_claimed_symbol(where: str) -> None:
    """⚑⚑ A counter lagging a claimed symbol refuses the add; the symbol is never issued twice.

    Measured on HEAD 2026-09-25 (nemik: rosettapkg W6): counter=5 with W6 in residue minted a
    live W6, a symbol both live and in residue.
    """
    state = _state()
    claimed = f"W{_COUNTER + 1}"
    if where == "residue":
        state.residue.append({"symbol": claimed, "reason": "old", "dropped_at": "d"})
    else:
        state.waypoints.append(_wp(claimed))
    before = copy.deepcopy(state.doc)
    with pytest.raises(ops.RefusedError, match=rf"nothing minted.*{claimed}.*--check"):
        ops.add(state, ops.Draft("new"), _NOW)
    assert state.doc == before


def test_drop_moves_to_residue_with_the_reason() -> None:
    """Dropping moves a waypoint to residue with its reason."""
    state = _state()
    ops.drop(state, "W1", "superseded", _NOW)
    assert ([w["symbol"] for w in state.waypoints], state.residue[-1]["reason"]) == (
        ["W2"],
        "superseded",
    )


def test_drop_refuses_a_blank_reason() -> None:
    """A drop without a reason is refused."""
    with pytest.raises(ops.RefusedError, match="reason is required"):
        ops.drop(_state(), "W1", " ", _NOW)


def test_drop_refuses_residue() -> None:
    """Dropping a symbol that is already residue is refused."""
    with pytest.raises(ops.RefusedError, match="is residue"):
        ops.drop(_state(), "W3", "again", _NOW)


@pytest.mark.parametrize("count", ops.NUDGE_TICKS)
def test_the_backoff_ticks_nudge(count: int) -> None:
    """Ticks 1, 2, 4 and 8 nudge."""
    assert ops.action_for(count) is ops.Action.NUDGE


def test_tick_sixteen_escalates() -> None:
    """Tick 16 escalates, once."""
    assert ops.action_for(_ESCALATE) is ops.Action.ESCALATE


@pytest.mark.parametrize("count", _QUIET)
def test_other_ticks_are_quiet(count: int) -> None:
    """Every other tick is quiet, including after the escalation."""
    assert ops.action_for(count) is ops.Action.QUIET


def test_bump_counts_only_blocked_and_not_excluded() -> None:
    """Bumping counts every blocked waypoint not excluded, and nothing else."""
    state = _state(_blocked("W1"), _blocked("W2"), _wp("W4"))
    nudges = ops.bump_blocked(state, frozenset({"W2"}))
    assert (
        [(n.symbol, n.ticks, n.action) for n in nudges],
        [w["ticks_blocked"] for w in state.waypoints],
    ) == ([("W1", 1, ops.Action.NUDGE)], [1, 0, 0])


def test_bump_does_not_touch_the_heartbeat() -> None:
    """Bumping leaves heartbeat alone (sre rewrote it)."""
    state = _state(_blocked("W1"))
    ops.bump_blocked(state, frozenset())
    assert state.doc["heartbeat"] == "h0"


def test_arm_records_job_and_heartbeat() -> None:
    """Arming records the job id and the heartbeat."""
    state = _state()
    ops.arm(state, "job-9", _NOW)
    assert (state.doc["job_id"], state.doc["heartbeat"]) == ("job-9", _NOW)


def test_arm_keeps_the_outgoing_job_as_predecessor() -> None:
    """Re-arming records the outgoing job_id as predecessor_job_id before overwriting it."""
    old, new = "job-old", "job-new"
    state = _state()
    state.doc["job_id"] = old
    ops.arm(state, new, _NOW)
    assert (state.doc.get("predecessor_job_id"), state.doc["job_id"]) == (old, new)


def test_arm_refuses_an_empty_job() -> None:
    """An empty job id is refused."""
    with pytest.raises(ops.RefusedError, match="job id is empty"):
        ops.arm(_state(), "", _NOW)


def test_the_preamble_is_set_and_cleared() -> None:
    """A preamble is stored, and clearing it reports how many lines went."""
    state = _state()
    ops.set_preamble(state, ["a", "b"])
    stored = state.doc["preamble"]
    assert (stored, ops.clear_preamble(state), "preamble" in state.doc) == (["a", "b"], 2, False)


def test_a_blank_preamble_is_refused() -> None:
    """A preamble of blank lines is refused."""
    with pytest.raises(ops.RefusedError, match="0 non-blank"):
        ops.set_preamble(_state(), ["", " "])


_FOREIGN_EDGE = "luthen-observability:W55"


def test_an_edge_may_name_another_repos_waypoint() -> None:
    """⚑⚑ `repo:W<n>` is a legal edge for --add and --update (nemik, 2026-09-25)."""
    state = _state()
    ops.add(state, ops.Draft("new", enables=("W1", _FOREIGN_EDGE)), _NOW)
    ops.update(state, "W2", ops.Update(enables=(_FOREIGN_EDGE,)), _NOW)
    assert (state.waypoints[-1]["enables"], state.waypoints[1]["enables"]) == (
        ["W1", _FOREIGN_EDGE],
        [_FOREIGN_EDGE],
    )


@pytest.mark.parametrize("edge", [":W5", "repo:", "repo:X5", "repo:W0", "a b:W5", "repo:W5,W6"])
def test_a_malformed_foreign_edge_is_refused(edge: str) -> None:
    """An empty repo, a missing or zero symbol, a space, or a comma-joined pair is refused."""
    with pytest.raises(ops.RefusedError, match="not W<n>"):
        ops.update(_state(), "W1", ops.Update(enables=(edge,)), _NOW)

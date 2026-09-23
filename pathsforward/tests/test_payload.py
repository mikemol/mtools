# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the payload: budgeted with the marker counted, refused when nothing fits."""

from __future__ import annotations

from pathlib import Path

import pytest

from mikemol.pathsforward import payload as pl
from mikemol.pathsforward.digest import v2
from mikemol.pathsforward.model import State, validate

Rec = dict[str, object]

_COPY = Path("/scratch/copy/paths-forward.json")
_LIVE = "/home/someone/github/repo/.claude/paths-forward.json"
_NOW = "2026-09-23T00:00:00Z"
_HUGE_STEP = 7000
_MANY = 30
_LONG_TITLE = 100
_LONG_STEP = 400
_LONG_REASON = 300
_SWEEP = range(2000, 20000, 211)
_PRE_LINES = 100
_PRE_WIDTH = 80


def _wp(sym: str, status: str = "ready", **extra: object) -> Rec:
    """Build a waypoint.

    Returns:
        the waypoint.

    """
    w: Rec = {"symbol": sym, "title": f"title of {sym}", "status": status, "blocked_on": [],
              "blocked_kind": None, "next_bounded_step": f"step of {sym}",
              "evidence": f"evidence of {sym}\nsecond line", "ticks_blocked": 0}
    w.update(extra)
    return w


def _state(waypoints: list[Rec], **top: object) -> State:
    """Build a state whose `state_path` KEY names a live file, as mtools' did.

    Returns:
        the state.

    """
    doc: Rec = {"counter": len(waypoints) + 1, "project_root": "/proj", "state_path": _LIVE,
                "job_id": "job-7", "waypoints": waypoints,
                "residue": [{"symbol": f"W{len(waypoints) + 1}", "reason": "gone for good"}]}
    doc.update(top)
    return validate(doc)


def _build(state: State, budget: int = pl.PAYLOAD_BUDGET) -> str:
    """Build a payload from the copy path.

    Returns:
        the payload.

    """
    return pl.build(pl.Request(state, _COPY, _NOW, budget))


def _big() -> State:
    """Build a state far over budget in full, trimmable by the ladder.

    Returns:
        the state.

    """
    return _state([_wp(f"W{i}", title="t" * _LONG_TITLE, next_bounded_step="s" * _LONG_STEP)
                   for i in range(1, _MANY + 1)])


def test_a_payload_under_budget_is_not_marked_truncated() -> None:
    """A payload that fits whole carries no truncation marker (sre's was always True)."""
    assert "truncated" not in _build(_state([_wp("W1")]))


def test_the_state_path_is_the_path_read_not_the_files_key() -> None:
    """The payload names the path it was built from, never the document's `state_path` key."""
    text = _build(_state([_wp("W1")]))
    assert (f"state_path={_COPY}" in text, _LIVE in text) == (True, False)


def test_an_oversize_payload_is_refused() -> None:
    """A top step that cannot fit is refused rather than emitted over budget (D4)."""
    with pytest.raises(pl.PayloadOverBudgetError, match="budget is"):
        _build(_state([_wp("W1", next_bounded_step="x" * _HUGE_STEP)]))


def test_a_big_state_is_trimmed_under_budget_and_says_so() -> None:
    """A state far over budget in full is trimmed under it, and marked truncated."""
    text = _build(_big())
    assert (len(text) <= pl.PAYLOAD_BUDGET, "truncated=true" in text) == (True, True)


def test_no_payload_is_ever_over_its_budget() -> None:
    """Across a sweep of budgets every payload fits, marker included, or is refused."""
    outcomes: list[str] = []
    for budget in _SWEEP:
        try:
            text = _build(_big(), budget)
        except pl.PayloadOverBudgetError:
            outcomes.append("refused")
            continue
        assert len(text) <= budget
        outcomes.append("fit")
    # the positive control: the sweep exercised both outcomes, so the bound was really tested.
    assert set(outcomes) == {"refused", "fit"}


def test_residue_is_dropped_first() -> None:
    """The first rung drops residue reasons, and names it."""
    state = _state([_wp("W1")], residue=[{"symbol": "W2", "reason": "r" * _LONG_REASON}])
    trimmed = _build(state, len(_build(state)) - 1)
    assert "truncated=true dropped=residue -" in trimmed


def test_a_done_waypoint_costs_one_line() -> None:
    """A done waypoint is listed by symbol only."""
    text = _build(_state([_wp("W1"), _wp("W2", "done")]))
    assert ("  done (1): W2" in text, "step of W2" in text) == (True, False)


def test_a_dropped_status_is_not_shown_live() -> None:
    """A waypoint with status=dropped is not printed as live (summit printed it)."""
    assert "step of W2" not in _build(_state([_wp("W1"), _wp("W2", "dropped")]))


def test_evidence_is_the_first_line_only() -> None:
    """Evidence is carried as its first line."""
    text = _build(_state([_wp("W1")]))
    assert ("evidence: evidence of W1" in text, "second line" in text) == (True, False)


def test_the_standing_rules_are_emitted_verbatim() -> None:
    """`preamble`, `standing` and `host` are emitted as declared (el-openglo, mtools)."""
    state = _state([_wp("W1")], preamble="rule one\nrule two", standing=["no swarm"],
                   host={"venvs": ["a", "b"], "pandoc": "ok"})
    assert pl.rules(state) == ["preamble:", "  rule one", "  rule two", "standing:",
                               "  - no swarm", "host:", "  venvs=a,b", "  pandoc=ok"]


def test_a_list_preamble_is_accepted() -> None:
    """A preamble stored as a list is emitted line by line."""
    assert pl.rules(_state([_wp("W1")], preamble=["a"])) == ["preamble:", "  a"]


def test_no_rules_emit_no_block() -> None:
    """Without the three keys there is no block."""
    assert pl.rules(_state([_wp("W1")])) == []


def test_the_rules_are_dropped_last_and_named() -> None:
    """An over-budget preamble is dropped at the last rung and named with its line count."""
    pre = [f"rule {i} " + "x" * _PRE_WIDTH for i in range(_PRE_LINES)]
    text = _build(_state([_wp("W1")], preamble=pre))
    assert (f"rules({_PRE_LINES + 1}-lines)" in text, "rule 0 " in text) == (True, False)


def test_the_scheduler_verbs_come_from_bindings() -> None:
    """A bound capability is named by its binding; an unbound one by its capability."""
    state = _state([_wp("W1")], bindings={"SCHEDULE_CREATE": "CronCreate"})
    line = pl.header(pl.Request(state, _COPY, _NOW))[-1]
    assert ("CronCreate" in line, "SCHEDULE_LIST" in line, "job_id=job-7" in line) == (
        True, True, True)


def test_the_header_carries_the_hash_and_the_build_time() -> None:
    """The header carries the v2 hash and the time it was built, not the heartbeat."""
    state = _state([_wp("W1")], heartbeat="2020-01-01T00:00:00Z")
    line = pl.header(pl.Request(state, _COPY, _NOW))[3]
    assert line == f"counter=2 state_hash={v2(state.waypoints)} generated_at={_NOW}"


def test_a_bare_string_blocked_on_is_one_party() -> None:
    """`blocked_on="mikemol"` renders as one party, not as characters."""
    first = pl.stanza(_wp("W1", "blocked", blocked_on="mikemol", blocked_kind="human"))
    assert "blocked_on=mikemol(human)" in first.splitlines()[0]


def test_a_long_line_is_clipped() -> None:
    """A collapsed stanza longer than CLIP is clipped to CLIP with an ellipsis."""
    clipped = pl.clip("y" * (pl.CLIP * 2) + "\nnext")
    assert (len(clipped), clipped.endswith("...")) == (pl.CLIP, True)


def test_a_short_line_is_kept() -> None:
    """A collapsed stanza within CLIP is its first line unchanged."""
    assert pl.clip("short\nnext") == "short"


def test_the_ladder_adds_the_rules_rung_only_with_rules() -> None:
    """The last rung (drop the rules) exists only when there are rules to drop."""
    with_rules = pl.ladder(1, has_rules=True)
    without = pl.ladder(1, has_rules=False)
    assert (len(with_rules) - len(without), with_rules[-1].dropped[-1]) == (1, "rules")

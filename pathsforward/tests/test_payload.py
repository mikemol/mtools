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
_SWEEP = range(500, 20000, 211)
_PRE_LINES = 100
_PRE_WIDTH = 80
_BLOCKED = "W22"
_READY = "W24"
_UNIT = "the unit of work this tick needs"
_ELSEWHERE = "pytest"
_RECONCILE = 4
_WIDE_STEP = 2000
_PROG = "mikemol-paths-forward"
_MODULE = "-m mikemol.pathsforward"
_SENTINEL = "never point GIT_* at the real repo"
_STANDING_LINES = 25
_HOST_OS = "host-os-sentinel"
_LAST_RUNG_TAIL = (
    "dropped=residue,evidence,host,steps-below-1,collapsed - read state_path for the rest."
)


def _wp(sym: str, status: str = "ready", **extra: object) -> Rec:
    """Build a waypoint.

    Returns:
        the waypoint.

    """
    w: Rec = {
        "symbol": sym,
        "title": f"title of {sym}",
        "status": status,
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": f"step of {sym}",
        "evidence": f"evidence of {sym}\nsecond line",
        "ticks_blocked": 0,
    }
    w.update(extra)
    return w


def _state(waypoints: list[Rec], **top: object) -> State:
    """Build a state whose `state_path` KEY names a live file, as mtools' did.

    Returns:
        the state.

    """
    doc: Rec = {
        "counter": len(waypoints) + 1,
        "project_root": "/proj",
        "state_path": _LIVE,
        "job_id": "job-7",
        "waypoints": waypoints,
        "residue": [{"symbol": f"W{len(waypoints) + 1}", "reason": "gone for good"}],
    }
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
    return _state(
        [
            _wp(f"W{i}", title="t" * _LONG_TITLE, next_bounded_step="s" * _LONG_STEP)
            for i in range(1, _MANY + 1)
        ]
    )


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
    state = _state(
        [_wp("W1")],
        preamble="rule one\nrule two",
        standing=["no swarm"],
        host={"venvs": ["a", "b"], "pandoc": "ok"},
    )
    assert pl.rules(state) == [
        "preamble:",
        "  rule one",
        "  rule two",
        "standing:",
        "  - no swarm",
        "host:",
        "  venvs=a,b",
        "  pandoc=ok",
    ]


def test_a_list_preamble_is_accepted() -> None:
    """A preamble stored as a list is emitted line by line."""
    assert pl.rules(_state([_wp("W1")], preamble=["a"])) == ["preamble:", "  a"]


def test_no_rules_emit_no_block() -> None:
    """Without the three keys there is no block."""
    assert pl.rules(_state([_wp("W1")])) == []


def test_the_standing_rules_survive_the_last_rung() -> None:
    """On the last rung the standing list is present while host and collapsed lines are gone."""
    standing = [f"{_SENTINEL} {i} " + "x" * _PRE_WIDTH for i in range(_STANDING_LINES)]
    text = _build(_state(_big().waypoints, standing=standing, host={"os": _HOST_OS}))
    # the positive control: this really is the last rung, since host and collapsed were dropped.
    assert (f"  - {_SENTINEL} 0 " in text, text.endswith(_LAST_RUNG_TAIL), _HOST_OS in text) == (
        True,
        True,
        False,
    )


def test_standing_plus_first_step_over_budget_is_refused_with_both_sizes() -> None:
    """Standing rules and a first ready step that cannot fit together are refused, sized."""
    standing = [f"rule {i} " + "x" * _PRE_WIDTH for i in range(_PRE_LINES)]
    first = _wp("W1")
    state = _state([first], standing=standing)
    rules_size = len("\n".join(["standing:", *(f"  - {line}" for line in standing)]))
    with pytest.raises(pl.PayloadOverBudgetError) as caught:
        _build(state)
    message = str(caught.value)
    assert (
        f"standing rules are {rules_size} characters" in message,
        f"stanza is {len(pl.stanza(first))}" in message,
    ) == (True, True)


def test_the_scheduler_verbs_come_from_bindings() -> None:
    """A bound capability is named by its binding; an unbound one by its capability."""
    state = _state([_wp("W1")], bindings={"SCHEDULE_CREATE": "CronCreate"})
    line = pl.header(pl.Request(state, _COPY, _NOW))[-1]
    assert ("CronCreate" in line, "SCHEDULE_LIST" in line, "job_id=job-7" in line) == (
        True,
        True,
        True,
    )


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


def test_the_ladder_adds_the_host_rung_only_with_a_host() -> None:
    """The host rung exists only with a host block; every ladder ends by dropping collapsed."""
    with_host = pl.ladder(1, has_host=True)
    without = pl.ladder(1, has_host=False)
    assert (
        len(with_host) - len(without),
        "host" in with_host[-1].dropped,
        "host" in without[-1].dropped,
        without[-1].dropped[-1],
    ) == (1, True, False, "collapsed")


def test_a_ready_waypoint_is_listed_above_a_blocked_one() -> None:
    """A ready W24 is listed above a blocked W22 that precedes it in the file (skill section 3)."""
    blocked = _wp(_BLOCKED, "blocked", blocked_on=["mikemol"], blocked_kind="human")
    text = _build(_state([blocked, _wp(_READY)]))
    assert text.index(f"  {_READY} [") < text.index(f"  {_BLOCKED} [")


def test_the_first_ready_step_survives_steps_below_1() -> None:
    """At steps-below-1 the first ready waypoint's step is kept whole below two working ones."""
    ws = [
        _wp(f"W{i}", title="t" * _LONG_TITLE, next_bounded_step="s" * _LONG_STEP)
        for i in range(1, _MANY + 1)
    ]
    ws[0]["status"], ws[1]["status"] = "working", "working"
    ws[1]["next_bounded_step"] = "w" * _WIDE_STEP
    ws[2]["next_bounded_step"] = _UNIT
    text = _build(_state(ws))
    assert ("steps-below-1" in text, f"next: {_UNIT}" in text) == (True, True)


def test_a_first_ready_step_that_cannot_fit_is_refused() -> None:
    """A first ready step too big for the budget is refused, never collapsed away (D4)."""
    ws = [_wp("W1", "working"), _wp("W2", next_bounded_step="x" * _HUGE_STEP)]
    with pytest.raises(pl.PayloadOverBudgetError, match="budget is"):
        _build(_state(ws))


def test_the_reconcile_command_is_the_running_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run as the console script, the reconcile line names it by its resolved absolute path."""
    script = tmp_path / _PROG
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.argv", [str(script)])
    line = pl.header(pl.Request(_state([_wp("W1")]), _COPY, _NOW))[_RECONCILE]
    assert line.startswith(f"Reconcile first: `{script.resolve()} --state {_COPY} --verify ")


def test_the_reconcile_command_is_absolute_when_run_otherwise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run by pytest, the command is the venv's script or `<python> -m`, and absolute either way."""
    monkeypatch.setattr("sys.argv", [_ELSEWHERE])
    line = pl.header(pl.Request(_state([_wp("W1")]), _COPY, _NOW))[_RECONCILE]
    command = line.split("`")[1].split(" --state ")[0]
    first = Path(command.split()[0])
    assert (first.is_absolute(), first.name == _PROG or command.endswith(_MODULE)) == (True, True)

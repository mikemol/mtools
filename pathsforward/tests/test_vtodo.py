# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the --ics projection: one VTODO per waypoint, mapped as life accepted (W313)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import cli
from mikemol.pathsforward.model import State, validate
from mikemol.pathsforward.vtodo import calendar, overrides, todo

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]
_STAMP = "20261001T090000Z"
_WHERE = {"repo": "life", "host": "box", "stamp": _STAMP}


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
        "next_bounded_step": "the step",
        "evidence": "",
        "ticks_blocked": 0,
    }
    w.update(extra)
    return w


def _lines(w: Rec) -> list[str]:
    """Project one waypoint.

    Returns:
        its VTODO's content lines.

    """
    return todo(w, repo="life", host="box", stamp=_STAMP)


def test_a_dated_waypoint_carries_its_uid_status_and_times_as_stored() -> None:
    """Life's W9 and W12: a TZID start and an all-day due, each in the form it needs (W300)."""
    w = _wp("W9", dtstart="TZID=America/Detroit:20261001T163000", due="20261001")
    assert _lines(w) == [
        "BEGIN:VTODO",
        "UID:life:W9@box",
        f"DTSTAMP:{_STAMP}",
        "SUMMARY:W9 title of W9",
        "STATUS:NEEDS-ACTION",
        "DESCRIPTION:next: the step",
        "DTSTART;TZID=America/Detroit:20261001T163000",
        "DUE;VALUE=DATE:20261001",
        "END:VTODO",
    ]


def test_an_operator_ask_is_categorized_and_says_what_it_waits_on() -> None:
    """⚑ "operator: decide ..." becomes CATEGORIES:decide (nemik rule 4); the kind is marked."""
    w = _wp(
        "W4",
        "blocked",
        blocked_on=["operator: decide which bank, A or B"],
        blocked_kind="human",
    )
    lines = _lines(w)
    assert "CATEGORIES:decide" in lines
    assert "X-PATHS-FORWARD-BLOCKED:human" in lines
    assert "DESCRIPTION:next: the step\\nblocked on: operator: decide which bank\\, A or B" in lines


def test_a_blocker_that_is_a_waypoint_becomes_a_depends_on_relation() -> None:
    """Local and foreign waypoints become RELATED-TO DEPENDS-ON (RFC 9253); prose does not."""
    w = _wp("W5", "blocked", blocked_on=["W1", "nemik:W129", "the weather"], blocked_kind="agent")
    related = [line for line in _lines(w) if line.startswith("RELATED-TO")]
    assert related == [
        "RELATED-TO;RELTYPE=DEPENDS-ON:life:W1@box",
        "RELATED-TO;RELTYPE=DEPENDS-ON:nemik:W129@box",
    ]


@pytest.mark.parametrize(
    ("status", "expected"),
    [("ready", "NEEDS-ACTION"), ("working", "IN-PROCESS"), ("done", "COMPLETED")],
)
def test_each_status_maps_to_its_vtodo_status(status: str, expected: str) -> None:
    """Ready and blocked need action, working is in process, and done is completed."""
    assert f"STATUS:{expected}" in _lines(_wp("W1", status))


def _monthly(**extra: object) -> Rec:
    """Build life's monthly waypoint: the first of each month from 2026-11-01, January skipped.

    Returns:
        the waypoint.

    """
    w = _wp("W7", dtstart="20261101", rrule="FREQ=MONTHLY;BYMONTHDAY=1", exdates=["20270101"])
    w.update(extra)
    return w


def test_a_recurring_waypoint_carries_its_rule_and_exdates_as_stored() -> None:
    """⚑ The RRULE is written verbatim, its ';' unescaped; an EXDATE takes DTSTART's form (W309)."""
    lines = _lines(_monthly())
    end = lines.index("END:VTODO")
    assert lines[end - 2 : end] == ["RRULE:FREQ=MONTHLY;BYMONTHDAY=1", "EXDATE;VALUE=DATE:20270101"]


@pytest.mark.parametrize(
    ("alarm", "trigger"),
    [
        ("-PT15M", "TRIGGER:-PT15M"),
        ("RELATED=END:-PT2H", "TRIGGER;RELATED=END:-PT2H"),
        ("VALUE=DATE-TIME:20261001T190000Z", "TRIGGER;VALUE=DATE-TIME:20261001T190000Z"),
    ],
)
def test_each_alarm_is_a_display_valarm_with_its_trigger(alarm: str, trigger: str) -> None:
    """A stored TRIGGER's RELATED or VALUE becomes the TRIGGER's param (RFC 5545 3.8.6.3, W279)."""
    lines = _lines(_wp("W9", dtstart="20261001T203000Z", due="20261002", alarms=[alarm]))
    start = lines.index("BEGIN:VALARM")
    assert lines[start : start + 5] == [
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:W9 title of W9",
        trigger,
        "END:VALARM",
    ]


def test_a_completed_occurrence_is_an_override_and_a_missed_one_is_absent() -> None:
    """Life's model (W310): December done, November missed, so ONE override, keyed by its RID."""
    w = _monthly(occurrences={"20261201": "20261201T180000Z"})
    assert overrides(w, repo="life", host="box", stamp=_STAMP) == [
        "BEGIN:VTODO",
        "UID:life:W7@box",
        f"DTSTAMP:{_STAMP}",
        "RECURRENCE-ID;VALUE=DATE:20261201",
        "DTSTART;VALUE=DATE:20261201",
        "SUMMARY:W7 title of W7",
        "STATUS:COMPLETED",
        "COMPLETED:20261201T180000Z",
        "END:VTODO",
    ]


def test_a_done_waypoint_carries_its_completed_stamp() -> None:
    """COMPLETED is the stamp W301 recorded, as stored."""
    lines = _lines(_wp("W1", "done", completed="20261001T074234Z"))
    assert "COMPLETED:20261001T074234Z" in lines


def test_a_done_waypoint_is_one_hundred_percent_complete() -> None:
    """⚑ done is the one status with a clean PERCENT-COMPLETE (RFC 5545 3.8.1.8): 100 (W280)."""
    lines = _lines(_wp("W1", "done"))
    status = lines.index("STATUS:COMPLETED")
    assert lines[status + 1] == "PERCENT-COMPLETE:100"


@pytest.mark.parametrize("status", ["ready", "blocked", "working"])
def test_an_unfinished_waypoint_claims_no_percentage(status: str) -> None:
    """ready, blocked and working carry no measure of progress, so none is invented (W280)."""
    lines = _lines(_wp("W1", status))
    assert not [line for line in lines if line.startswith("PERCENT-COMPLETE")]


@pytest.mark.parametrize("weight", [0, 1, 9, 58])
def test_a_weight_is_never_guessed_into_a_priority(weight: int) -> None:
    """⚑ weight is an unbounded relative rank (0-58 across the fleet), not RFC 5545's 1-9 (W280)."""
    lines = _lines(_wp("W1", weight=weight))
    assert not [line for line in lines if line.startswith("PRIORITY")]


def _state() -> State:
    """Build a state with two waypoints and one residue entry.

    Returns:
        the state.

    """
    return validate(
        {
            "counter": 3,
            "heartbeat": "h0",
            "waypoints": [_wp("W1"), _wp("W2", "done")],
            "residue": [{"symbol": "W3", "reason": "why", "dropped_at": "d"}],
        }
    )


def test_the_calendar_wraps_every_waypoint_and_omits_residue() -> None:
    """One VCALENDAR, one VTODO per waypoint, nothing for the dropped W3, CRLF throughout."""
    text = calendar(_state(), repo="life", host="box", stamp=_STAMP)
    lines = text.split("\r\n")
    assert (lines[0], lines[1], lines[-2], lines[-1]) == (
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "END:VCALENDAR",
        "",
    )
    assert [line for line in lines if line.startswith("UID:")] == [
        "UID:life:W1@box",
        "UID:life:W2@box",
    ]


def test_ics_mode_prints_the_calendar_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """⚑ --ics is READ-ONLY: the state file is byte-identical after it runs."""
    path = tmp_path / "paths-forward.json"
    doc: Rec = {"project_root": "/x/life", "counter": 1, "waypoints": [_wp("W1")]}
    path.write_text(json.dumps(doc), encoding="utf-8")
    before = path.read_bytes()
    assert cli.main(["--state", str(path), "--ics"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert (out.startswith("BEGIN:VCALENDAR\r\n"), "UID:life:W1@" in out) == (True, True)
    assert path.read_bytes() == before

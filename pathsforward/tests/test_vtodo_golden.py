# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The writer's iCalendar output is pinned to a tracked golden file (mtools:W1258).

⚑ A STRING CHECK ON ONE LINE CANNOT SEE THE WHOLE CALENDAR DRIFT. The other vtodo tests assert a
few content lines; this one holds the entire VCALENDAR for a queue that exercises every projection
(a TZID start with its VTIMEZONE, an all-day due, an alarm, a monthly rule with an EXDATE and a
completed-occurrence override, a done card, a waypoint dependency, an operator ask) against
`tests/golden/queue.ics`, byte for byte, so a change to any of them is a reviewed diff of that file
and not a silent edit. The golden is the fixture an iCalendar PARSER test reads (the parse
round-trip is W1258's second half, in the distribution that owns a parser).

⚑ NEVER AUTO-UPDATED: a mismatch fails and names the file. To accept a deliberate change, run this
module directly (`python3 tests/test_vtodo_golden.py`) and review the diff of the golden.
"""

from __future__ import annotations

from pathlib import Path

from mikemol.pathsforward.model import State, validate
from mikemol.pathsforward.vtodo import calendar

GOLDEN = Path(__file__).parent / "golden" / "queue.ics"
_STAMP = "20261001T090000Z"
_ASK = "operator: act apply the settings change"


def _wp(sym: str, status: str = "ready", **extra: object) -> dict[str, object]:
    w: dict[str, object] = {
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


def _state() -> State:
    """Build the queue the golden is rendered from.

    Returns:
        a state with six waypoints and one residue entry.

    """
    return validate(
        {
            "counter": 7,
            "heartbeat": "h0",
            "waypoints": [
                _wp(
                    "W1",
                    dtstart="TZID=America/Detroit:20261001T163000",
                    due="20261002",
                    alarms=["-PT15M"],
                ),
                _wp(
                    "W2",
                    dtstart="20261101",
                    rrule="FREQ=MONTHLY;BYMONTHDAY=1",
                    exdates=["20270101"],
                    occurrences={"20261201": "20261201T180000Z"},
                ),
                _wp("W3", "done", completed="20261001T120000Z", next_bounded_step=None),
                _wp("W4", "blocked", blocked_on=["W1"], blocked_kind="agent"),
                _wp("W5", "blocked", blocked_on=[_ASK], blocked_kind="human"),
                _wp("W6", "working", weight=5),
            ],
            "residue": [{"symbol": "W7", "reason": "why", "dropped_at": "d"}],
        }
    )


def render() -> str:
    """Render the golden's calendar.

    Returns:
        the VCALENDAR text with CRLF line ends.

    """
    return calendar(_state(), repo="life", host="box", stamp=_STAMP)


def test_the_calendar_for_the_golden_queue_matches_the_tracked_file_byte_for_byte() -> None:
    """Any change to the writer's output for a full queue is a diff of `tests/golden/queue.ics`."""
    assert GOLDEN.read_bytes() == render().encode("utf-8"), (
        f"the calendar no longer matches {GOLDEN}; if the change is deliberate, run this module "
        "directly and review the diff of the golden"
    )


def test_the_golden_queue_exercises_every_projection_it_claims_to() -> None:
    """The control: the calendar carries a VTIMEZONE, an alarm, an override and a dependency."""
    text = render()
    for needle in (
        "BEGIN:VTIMEZONE",
        "TZID:America/Detroit",
        "BEGIN:VALARM",
        "RRULE:FREQ=MONTHLY;BYMONTHDAY=1",
        "EXDATE;VALUE=DATE:20270101",
        "RECURRENCE-ID;VALUE=DATE:20261201",
        "STATUS:COMPLETED",
        "RELATED-TO",
    ):
        assert needle in text
    assert "W7" not in text


if __name__ == "__main__":
    GOLDEN.parent.mkdir(exist_ok=True)
    GOLDEN.write_bytes(render().encode("utf-8"))

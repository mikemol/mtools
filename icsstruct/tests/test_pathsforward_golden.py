# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The lossless reader parses pathsforward's golden calendar with no malformed line (W1263).

⚑ THE WRITER'S TESTS ONLY SAW STRINGS. pathsforward pins its iCalendar output to
`tests/golden/queue.ics` byte for byte (W1258) but nothing parsed it, so a change that kept every
asserted line and broke folding, nesting or a parameter would pass. This reads the same file with
an independent reader, the one the fleet already trusts for calendars it did not write: stage 1 must
return only well-formed, well-nested content lines, with the components the queue was built to
produce.

⚑ WHAT THIS DOES NOT CHECK, said so: icsstruct expands VEVENT, not VTODO, so the RRULE and the
RECURRENCE-ID override are checked as lines and as nesting, not by a recurrence expander; a real
expansion of the VTODO series is what a parser dependency in pathsforward (W1259) would add.

⚑ OFF THE CHECKOUT THE TEST SKIPS, WITH ITS REASON (W1227, as pathsforward's test_frontier_copy):
the gate names the file through `PATHSFORWARD_GOLDEN` and there a missing file fails; from a built
sdist, with no sibling checkout and no variable, there is nothing to parse.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mikemol.icsstruct.expand import components
from mikemol.icsstruct.lexical import ContentLine, Malformed, lex

_REL = "pathsforward/tests/golden/queue.ics"
_TODOS = 7
_ZONES = 1
_SERIES_AND_OVERRIDE = 2


def _golden() -> Path:
    """Find the golden calendar: the bazel-declared path, else the checkout beside this dist.

    Returns:
        the path of pathsforward's `queue.ics`.

    """
    named = os.environ.get("PATHSFORWARD_GOLDEN")
    if named:
        return Path(named)
    return Path(__file__).parents[2] / _REL


def _records() -> tuple[ContentLine | Malformed, ...]:
    path = _golden()
    if not os.environ.get("PATHSFORWARD_GOLDEN") and not path.is_file():
        pytest.skip("no sibling pathsforward checkout and PATHSFORWARD_GOLDEN is unset")
    assert path.is_file(), path
    return lex(path.read_bytes().decode("utf-8"))


def test_the_golden_calendar_lexes_with_no_malformed_line() -> None:
    """Every physical line of the writer's output is a well-formed, well-nested content line."""
    records = _records()
    assert records
    assert [r for r in records if isinstance(r, Malformed)] == []


def test_the_golden_calendar_has_the_components_the_queue_was_built_to_produce() -> None:
    """One calendar, one VTIMEZONE, and a VTODO per waypoint plus the completed override."""
    records = _records()
    assert len(components(records, "VCALENDAR")) == 1
    assert len(components(records, "VTIMEZONE")) == _ZONES
    assert len(components(records, "VTODO")) == _TODOS


def test_the_recurring_series_and_its_override_share_one_uid_and_the_alarm_is_nested() -> None:
    """W2's series and its December override carry one UID; the VALARM sits inside a VTODO."""
    lines = [r for r in _records() if isinstance(r, ContentLine)]
    uids = [r.value for r in lines if r.name == "UID"]
    assert uids.count("life:W2@box") == _SERIES_AND_OVERRIDE
    assert len(set(uids)) == len(uids) - 1
    alarms = [r for r in lines if r.name == "BEGIN" and r.value == "VALARM"]
    assert len(alarms) == 1
    assert [name for name, _ordinal in alarms[0].path] == ["VCALENDAR", "VTODO"]
    assert any(r.name == "RECURRENCE-ID" for r in lines)
    assert any(r.name == "RRULE" and r.value == "FREQ=MONTHLY;BYMONTHDAY=1" for r in lines)

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the RRULE grammar: an expandable rule passes unchanged, the rest are refused."""

from __future__ import annotations

import pytest

from mikemol.pathsforward.model import RefusedError
from mikemol.pathsforward.recurrence import check


@pytest.mark.parametrize(
    "rule",
    [
        "FREQ=MONTHLY;BYMONTHDAY=1",
        "FREQ=WEEKLY;BYDAY=MO,WE;COUNT=10",
        "FREQ=DAILY;UNTIL=20261231",
        "FREQ=MONTHLY;BYDAY=-1FR;UNTIL=20271231T235959Z",
        "FREQ=YEARLY;INTERVAL=2;BYMONTH=1,7;BYMONTHDAY=-1;WKST=SU",
        "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1",
    ],
)
def test_a_rule_a_reader_can_expand_is_accepted_unchanged(rule: str) -> None:
    """Monthly, weekly, ending by UNTIL or COUNT, and BY* parts all pass as written (W309)."""
    assert check(rule) == rule


@pytest.mark.parametrize(
    ("rule", "reason"),
    [
        ("BYMONTHDAY=1", "FREQ must be one of"),
        ("FREQ=FORTNIGHTLY", "FREQ must be one of"),
        ("FREQ=DAILY;UNTIL=20261231;COUNT=3", "UNTIL and COUNT cannot both"),
        ("FREQ=DAILY;UNTIL=TZID=America/Detroit:20261231T000000", "not a TZID"),
        ("FREQ=DAILY;UNTIL=20261231T000000", "floating time"),
        ("FREQ=DAILY;COUNT=0", "COUNT must be a positive integer"),
        ("FREQ=DAILY;INTERVAL=x", "INTERVAL must be a positive integer"),
        ("FREQ=MONTHLY;BYMONTHDAY=32", "BYMONTHDAY value '32' is outside 1..31"),
        ("FREQ=YEARLY;BYMONTH=-1", "BYMONTH value '-1' is outside 1..12"),
        ("FREQ=WEEKLY;BYDAY=MONDAY", "BYDAY value 'MONDAY' is not a weekday"),
        ("FREQ=MONTHLY;BYDAY=54MO", "BYDAY value '54MO' is not a weekday"),
        ("FREQ=WEEKLY;WKST=XX", "WKST must be a weekday"),
        ("FREQ=DAILY;FREQ=WEEKLY", "FREQ is given twice"),
        ("FREQ=DAILY;BYEASTER=1", "unknown part BYEASTER"),
        ("FREQ=DAILY;", "'' is not NAME=VALUE"),
    ],
)
def test_a_rule_no_reader_could_expand_is_refused(rule: str, reason: str) -> None:
    """⚑ No FREQ, UNTIL with COUNT, an out-of-range or unknown part: refused, naming why."""
    with pytest.raises(RefusedError, match=f"is not an RFC 5545 RRULE: .*{reason}"):
        check(rule)

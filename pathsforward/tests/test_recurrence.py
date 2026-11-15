# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the RRULE grammar: an expandable rule passes unchanged, the rest are refused."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward.model import RefusedError
from mikemol.pathsforward.recurrence import check, disagreements, rules_of

if TYPE_CHECKING:
    from collections.abc import Callable


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


_GOOD = "FREQ=MONTHLY;BYMONTHDAY=1"
_BAD = "FREQ=SOMETIMES"
_ONLY_OURS = "FREQ=DAILY;BYSECOND=60"


def _oracle(accepted: set[str]) -> Callable[[str], bool]:
    def reference(rule: str) -> bool:
        return rule in accepted

    return reference


def test_rules_both_readers_accept_or_both_reject_are_no_disagreement() -> None:
    """The controls: agreement in both directions reports nothing."""
    assert disagreements([_GOOD, _BAD], _oracle({_GOOD})) == []


def test_a_rule_only_we_accept_and_a_rule_only_the_reference_accepts_are_each_named() -> None:
    """Each direction of disagreement is one line saying which reader accepts."""
    found = disagreements([_ONLY_OURS, _BAD], _oracle({_BAD}))
    assert found == [
        f"{_ONLY_OURS!r}: we accept, the reference rejects",
        f"{_BAD!r}: the reference accepts, we reject",
    ]


def test_the_stored_rules_of_a_queue_are_read_in_order_and_junk_reads_as_none() -> None:
    """Only a waypoint with a string, non-empty `rrule` is listed; a non-queue document is empty."""
    document = {
        "waypoints": [
            {"symbol": "W1", "rrule": _GOOD},
            {"symbol": "W2"},
            {"symbol": "W3", "rrule": ""},
            {"symbol": "W4", "rrule": 7},
            "not a waypoint",
            {"symbol": "W5", "rrule": _BAD},
        ]
    }
    assert rules_of(document) == [("W1", _GOOD), ("W5", _BAD)]
    assert rules_of([]) == []
    assert rules_of({"waypoints": "x"}) == []

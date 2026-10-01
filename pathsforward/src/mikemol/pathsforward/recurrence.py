# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""RFC 5545 RRULE grammar for a recurring waypoint: checked here, expanded elsewhere (W309).

A rule is stored as written, after this module accepts it (RFC 5545 3.3.10):

    FREQ=MONTHLY;BYMONTHDAY=1          the first of every month
    FREQ=WEEKLY;BYDAY=MO,WE;COUNT=10   ten Mondays and Wednesdays
    FREQ=DAILY;UNTIL=20261231          every day through the end of the year

⚑ GRAMMAR ONLY, STANDARD LIBRARY ONLY (W299's decision). Expanding a rule into occurrences is the
reader's job: icsstruct does it with recurring_ical_events, and nemik fires per occurrence
(nemik:W145). What is refused here is what no reader could expand: no FREQ, UNTIL with COUNT, an
unknown part, a part given twice, or a value out of its range.
"""

from __future__ import annotations

import re

from mikemol.pathsforward import timevalue
from mikemol.pathsforward.model import RefusedError

_FREQS = frozenset({"SECONDLY", "MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "YEARLY"})
_DAYS = "SU|MO|TU|WE|TH|FR|SA"
_WEEKDAY = re.compile(rf"(?:{_DAYS})")
# BYDAY: an optional signed week number 1..53, then a weekday (RFC 5545 3.3.10 weekdaynum).
_BYDAY = re.compile(rf"(?:[+-]?(?:[1-9]|[1-4]\d|5[0-3]))?(?:{_DAYS})")
_INT = re.compile(r"([+-]?)(\d+)")

# part -> (lowest, highest, signed): a BY* list of integers in that range (RFC 5545 3.3.10).
_RANGES = {
    "BYSECOND": (0, 60, False),
    "BYMINUTE": (0, 59, False),
    "BYHOUR": (0, 23, False),
    "BYMONTHDAY": (1, 31, True),
    "BYYEARDAY": (1, 366, True),
    "BYWEEKNO": (1, 53, True),
    "BYMONTH": (1, 12, False),
    "BYSETPOS": (1, 366, True),
}
_PARTS = frozenset({"FREQ", "UNTIL", "COUNT", "INTERVAL", "BYDAY", "WKST", *_RANGES})


def _why(rule: str, reason: str) -> str:
    """Word the refusal for one rule.

    Returns:
        the message, naming the rule and what is wrong with it.

    """
    return f"{rule!r} is not an RFC 5545 RRULE: {reason}"


def _parts(rule: str) -> dict[str, str]:
    """Split a rule into its NAME=VALUE parts, refusing an unknown or repeated name.

    Returns:
        the parts, by name.

    Raises:
        RefusedError: for a part with no "=", an unknown name, or a name given twice.

    """
    parts: dict[str, str] = {}
    for part in rule.split(";"):
        name, sep, value = part.partition("=")
        reason = ""
        if not (sep and value):
            reason = f"{part!r} is not NAME=VALUE"
        elif name not in _PARTS:
            reason = f"unknown part {name}"
        elif name in parts:
            reason = f"{name} is given twice"
        if reason:
            raise RefusedError(_why(rule, reason))
        parts[name] = value
    return parts


def _list_error(name: str, value: str) -> str:
    """Find the first BY* integer outside its range.

    Returns:
        what is wrong, or "" when every item is in range.

    """
    low, high, signed = _RANGES[name]
    for item in value.split(","):
        match = _INT.fullmatch(item)
        if match is None or (match[1] and not signed) or not low <= int(match[2]) <= high:
            return f"{name} value {item!r} is outside {low}..{high}"
    return ""


def _until_error(value: str) -> str:
    """Check UNTIL: a DATE or a UTC DATE-TIME (RFC 5545 3.3.10 has no TZID here).

    Returns:
        what is wrong, or "" when it is accepted.

    """
    if value.startswith("TZID="):
        return "UNTIL takes a DATE or a UTC DATE-TIME, not a TZID"
    try:
        timevalue.parse(value)
    except RefusedError as exc:
        return f"UNTIL {exc}"
    return ""


def _errors(parts: dict[str, str]) -> list[str]:
    """List everything wrong with a split rule, in a fixed order.

    Returns:
        the reasons, empty for a rule a reader can expand.

    """
    reasons: list[str] = []
    if parts.get("FREQ") not in _FREQS:
        reasons.append(f"FREQ must be one of {', '.join(sorted(_FREQS))}")
    if "UNTIL" in parts and "COUNT" in parts:
        reasons.append("UNTIL and COUNT cannot both be given")
    reasons.append(_until_error(parts["UNTIL"]) if "UNTIL" in parts else "")
    reasons.extend(
        f"{name} must be a positive integer, not {parts[name]!r}"
        for name in ("COUNT", "INTERVAL")
        if name in parts and not (parts[name].isdigit() and int(parts[name]) >= 1)
    )
    reasons.extend(_list_error(name, parts[name]) for name in sorted(_RANGES.keys() & parts.keys()))
    reasons.extend(
        f"BYDAY value {item!r} is not a weekday like MO, 1MO or -1FR"
        for item in parts.get("BYDAY", "MO").split(",")
        if _BYDAY.fullmatch(item) is None
    )
    if _WEEKDAY.fullmatch(parts.get("WKST", "MO")) is None:
        reasons.append("WKST must be a weekday like MO")
    return [reason for reason in reasons if reason]


def check(rule: str) -> str:
    """Accept one RRULE value, unchanged, or refuse it (W309).

    Returns:
        the rule as given.

    Raises:
        RefusedError: for a rule no reader could expand, naming the first thing wrong.

    """
    reasons = _errors(_parts(rule))
    if reasons:
        raise RefusedError(_why(rule, reasons[0]))
    return rule

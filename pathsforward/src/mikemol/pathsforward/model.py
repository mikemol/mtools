# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The state file's shape: what a waypoint is, and the refusal of a document that is not one.

⚑ STRUCTURE IS REFUSED HERE; CONTENT IS JUDGED BY `check`. A document whose `waypoints` is not a
list of objects cannot be hashed, rendered or repaired, so it is refused at the door (summit's
`_waypoints`). A waypoint whose `status` is `bogus` or whose `blocked_on` is a bare string CAN
still be loaded — that is what lets `--update` repair it — and `check` reports it.

⚑ A SYMBOL IS PARSED, NEVER `int()`-ED. gabion's check crashed on `Wx` with a ValueError; here a
malformed symbol parses to `None` and every caller decides what that means.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

Json = dict[str, object]

STATUSES: tuple[str, ...] = ("ready", "blocked", "working", "done")
BLOCKED_KINDS: tuple[str, ...] = ("agent", "human")
NO_SYMBOL = "--"

_SYMBOL = re.compile(r"W([1-9][0-9]*)")


class MalformedStateError(ValueError):
    """The document is not a paths-forward state; it is refused, never guessed at."""


@dataclass(frozen=True)
class State:
    """A validated state document, with its two record lists bound to the document itself.

    Mutating `waypoints` or `residue` mutates `doc`, so a save writes what was changed and every
    top-level key a repo added (`goal`, `cadence`, `standing`, ...) survives the round trip.
    """

    doc: Json
    waypoints: list[Json]
    residue: list[Json]
    counter: int


def symbol_number(sym: object) -> int | None:
    """Parse `W<n>` to `n`.

    Returns:
        the positive integer, or None for anything that is not exactly `W<n>` with n >= 1.

    """
    if not isinstance(sym, str):
        return None
    match = _SYMBOL.fullmatch(sym)
    return int(match.group(1)) if match else None


def _records(doc: Json, key: str) -> list[Json]:
    """Validate one record list: a list of objects, each carrying a string `symbol`.

    Returns:
        the list, as stored in `doc`.

    Raises:
        MalformedStateError: when the list or any record in it is malformed.

    """
    raw = doc.get(key)
    if not isinstance(raw, list):
        msg = f"`{key}` is not a list"
        raise MalformedStateError(msg)
    records = cast("list[object]", raw)
    for index, rec in enumerate(records):
        if not isinstance(rec, dict):
            msg = f"`{key}[{index}]` is not an object"
            raise MalformedStateError(msg)
        if not isinstance(cast("Json", rec).get("symbol"), str):
            msg = f"`{key}[{index}]` has no string `symbol`"
            raise MalformedStateError(msg)
    return cast("list[Json]", records)


def validate(raw: object) -> State:
    """Refuse anything that is not structurally a state document.

    An absent `residue` is created empty, because the skill's schema carries it and a drop
    needs somewhere to go; nothing else is invented.

    Returns:
        the validated state.

    Raises:
        MalformedStateError: when the document is not an object, a record list is malformed,
            or `counter` is not a non-negative integer.

    """
    if not isinstance(raw, dict):
        msg = "the state document is not a JSON object"
        raise MalformedStateError(msg)
    doc = cast("Json", raw)
    doc.setdefault("residue", [])
    counter = doc.get("counter")
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
        msg = f"`counter` is {counter!r}, not a non-negative integer"
        raise MalformedStateError(msg)
    return State(doc, _records(doc, "waypoints"), _records(doc, "residue"), counter)


def text(rec: Json, key: str) -> str:
    """Read a field as text.

    Returns:
        the field as a string, or "" when it is absent or null.

    """
    value = rec.get(key)
    return "" if value is None else str(value)


def strlist(rec: Json, key: str) -> list[str]:
    """Read a list field, guarding against a bare string.

    ⚑ A STRING IS AN ITERABLE OF CHARACTERS: el-openglo's payload once printed
    `blocked_on=m,i,k,e,m,o,l` for five ticks. A bare string is read as ONE element here, and
    `check` still reports it as the wrong type.

    Returns:
        the elements as strings; [] when absent.

    """
    value = rec.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in cast("list[object]", value)]
    return [str(value)]


def ticks(rec: Json) -> int:
    """Read `ticks_blocked`.

    Returns:
        the count, or 0 when it is absent or not an integer.

    """
    value = rec.get("ticks_blocked")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List the working cards that are not in flight, oldest first (W2195, github-33's census ask).

⚑ `working` MEANS IN FLIGHT OR IN SCRATCH RIGHT NOW, A HANDFUL: the count had climbed from about 32
to 72 against about ten landings, because a card taken as working and never released stays working
(`--reconcile` is a dry run in `--tick-open`). A working card is STALE when no live stack names it
and its `last_worked` stamp (its `issued_at` when it was never worked) is more than the bound old.
Several working cards are fine; no gate entry with an old stamp is the flag.

A row is `<symbol> <age>d <next step>` and the last line counts the rows. A card whose stamp does
not read is listed first with age `?` (unknown is not fresh).

CONSUMED BY: `--working-stale DAYS` (`cli._working_stale`).
"""

from collections.abc import Collection
from datetime import datetime

from mikemol.pathsforward.model import State, text

_SECONDS_PER_DAY = 86400
_UNKNOWN = float("inf")


def _age(stamp: str, now: datetime) -> float:
    """Count days from a stamp to now.

    Returns:
        the age in days; infinity when the stamp does not read.

    """
    try:
        return (now - datetime.fromisoformat(stamp)).total_seconds() / _SECONDS_PER_DAY
    except ValueError:
        return _UNKNOWN


def _label(age: float) -> str:
    """Show an age for a row.

    Returns:
        the days to one decimal, or `?` when the stamp did not read.

    """
    return "?" if age == _UNKNOWN else f"{age:.1f}"


def report(state: State, days: float, now: datetime, live: Collection[str]) -> list[str]:
    """List the working cards no live stack names whose last work is older than `days`.

    Returns:
        one `<symbol> <age>d <next step>` row per card, oldest first, then a
        `# N working, none in flight, older than Dd` line.

    """
    stale: list[tuple[float, str, str]] = []
    for w in state.waypoints:
        symbol = text(w, "symbol")
        if text(w, "status") != "working" or symbol in live:
            continue
        age = _age(text(w, "last_worked") or text(w, "issued_at"), now)
        if age > days:
            stale.append((age, symbol, text(w, "next_bounded_step")))
    stale.sort(reverse=True)
    rows = [f"{sym} {_label(age)}d {step}" for age, sym, step in stale]
    return [*rows, f"# {len(stale)} working, none in flight, older than {days:g}d"]

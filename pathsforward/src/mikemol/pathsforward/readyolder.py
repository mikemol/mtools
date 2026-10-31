# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List the ready cards older than a bound, oldest first (W2118, for the W1929 sweep).

⚑ NOTHING LISTED THEM BY AGE: the W1929 sweep (operator: sweep the ready cards past the 2.2 d
bound, oldest first) ran for hours by hand, because `--queue` prints order without ages,
`--triage` proposes nothing and `--ready-count` is a number. A row is
`<symbol> <age>d <next step>` and the last line counts the rows, so the bound is MEASURED on the
queue and a before and after count can be compared.

A READY card is the one `--ready-count` counts: status `ready` and no witness. A card whose stamp
does not read is not listed (its age is unknown, not old).

CONSUMED BY: `--ready-older-than DAYS` (`cli._ready_older_than`).
"""

from datetime import datetime

from mikemol.pathsforward.model import State, text

_SECONDS_PER_DAY = 86400


def parse_days(given: str) -> float | None:
    """Read a day bound, an integer or a decimal such as `2.2`.

    Returns:
        the bound, or None when it is not a non-negative number.

    """
    try:
        days = float(given)
    except ValueError:
        return None
    return days if days >= 0 else None


def report(state: State, days: float, now: datetime) -> list[str]:
    """List the ready cards issued more than `days` days before `now`, oldest first.

    Returns:
        one `<symbol> <age>d <next step>` row per card, then a `# N ready older than D d` line.

    """
    aged: list[tuple[float, str, str]] = []
    for w in state.waypoints:
        if text(w, "status") != "ready" or text(w, "witness"):
            continue
        try:
            age = (now - datetime.fromisoformat(text(w, "issued_at"))).total_seconds()
        except ValueError:
            continue
        if age / _SECONDS_PER_DAY > days:
            aged.append((age, text(w, "symbol"), text(w, "next_bounded_step")))
    aged.sort(reverse=True)
    rows = [f"{sym} {age / _SECONDS_PER_DAY:.1f}d {step}" for age, sym, step in aged]
    return [*rows, f"# {len(aged)} ready older than {days:g}d"]

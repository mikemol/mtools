# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List the open cards blocked on one card, newest first, bounded (W2184, luthen:W1285).

⚑ NOTHING LISTED THEM: `--queue` prints ready cards only, `--triage` one summary line, and the
host has no jq, so 121 cards blocked on luthen:W1285 could not be named to atomize them by symbol.
A row is `<symbol> <status> age=<n>d touches=<a,b> :: <title>`; the age is whole days since the
card was issued, so a row reads the same on any later call that day.

⚑ ONLY AN EXACT, LOCAL BLOCKER COUNTS: a card is listed when its `blocked_on` holds the symbol as
written, so `W1285` does not list a card blocked on `luthen-observability:W1285` (another queue's
card, a different thing), and a done or dropped card is no longer blocked on anything.

CONSUMED BY: `--blocked-on-list SYMBOL [--all]` (`cli._blocked_on_list`).
"""

from datetime import datetime

from mikemol.pathsforward.model import State, strlist, text

LIMIT = 50
_OPEN = frozenset({"ready", "working", "blocked"})
_SECONDS_PER_DAY = 86400


def _age_days(issued: str, now: datetime) -> str:
    """Count whole days from an issue stamp to now.

    Returns:
        the count, or `?` when the stamp does not read.

    """
    try:
        then = datetime.fromisoformat(issued)
    except ValueError:
        return "?"
    return str(max(0, int((now - then).total_seconds() // _SECONDS_PER_DAY)))


def report(state: State, symbol: str, now: datetime, limit: int | None = LIMIT) -> list[str]:
    """List the open cards whose `blocked_on` holds `symbol`, newest issued first.

    Returns:
        one row per card, at most `limit` of them (all when None), then a `# N blocked on S`
        line that counts all of them, so a bounded list says how many it left out.

    """
    held = [
        w
        for w in state.waypoints
        if text(w, "status") in _OPEN and symbol in strlist(w, "blocked_on")
    ]
    held.sort(key=lambda w: text(w, "issued_at"), reverse=True)
    shown = held if limit is None else held[:limit]
    rows = [
        f"{text(w, 'symbol')} {text(w, 'status')} age={_age_days(text(w, 'issued_at'), now)}d "
        f"touches={','.join(strlist(w, 'touches'))} :: {text(w, 'title')}"
        for w in shown
    ]
    return [*rows, f"# {len(held)} blocked on {symbol}"]

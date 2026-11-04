# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read nemik's stackable set for a repository and pick the cards worth submitting (W1428).

`nemik-stackable <repo>` prints one text row per ready card that has a manifest:

    STACK|WAITING <repo>:W<n> <file> <file> ...
    19 stackable of 100 ready; 79 have no manifest

A STACK row can be submitted now; a WAITING row conflicts on files with a STACK row (measured:
W2132 against W2131 on commit_kata.py) and waits its turn. The closing count line and blank lines
are not rows. Cards with no manifest are counted by nemik, not listed, so they never appear here.

⚑ A ROW THAT STARTS LIKE ONE BUT DOES NOT FIT IS REFUSED, NOT SKIPPED: dropping it silently would
lose a card from the set, so `parse` raises ValueError naming the line. ⚑ A ROW'S STATUS IS NOT
TRUSTED FOR LANDING: nemik lists cards that landed and are still marked ready (measured: W2126,
W1895, W1960), so `submit_set` also takes the symbols git says landed and leaves those out.
"""

import re
from collections.abc import Collection
from dataclasses import dataclass
from typing import cast

STACK = "STACK"
WAITING = "WAITING"
_STATES = (STACK, WAITING)
_MIN_FIELDS = 2
_TRAILER = re.compile(r"^Waypoint: (W[0-9]+)[ \t]*$", re.MULTILINE)


@dataclass(frozen=True)
class Row:
    """One row of the stackable set."""

    state: str
    repo: str
    symbol: str
    files: tuple[str, ...]


def _row(line: str) -> Row:
    fields = line.split()
    state = fields[0]
    cite = fields[1] if len(fields) >= _MIN_FIELDS else ""
    repo, colon, symbol = cite.partition(":")
    if not (colon and repo and symbol.startswith("W") and symbol[1:].isdigit()):
        msg = f"stackable row has no <repo>:W<n> after {state}: {line!r}"
        raise ValueError(msg)
    return Row(state, repo, symbol, tuple(fields[2:]))


def parse(text: str) -> list[Row]:
    """Read `nemik-stackable`'s text output into rows, in the order printed.

    Returns:
        one row per STACK or WAITING line; the closing count line and blank lines are ignored.

    """
    rows: list[Row] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.split(" ", 1)[0] in _STATES:
            rows.append(_row(line))
    return rows


def landed_in(log: str) -> frozenset[str]:
    """Name the cards a git log says landed, from the `Waypoint:` trailers of its messages.

    ⚑ EVERY COMMIT `mikemol-commit` WRITES ENDS IN A `Waypoint: W<n>` TRAILER, so the trailers
    of the commits since a time name what landed; a card nemik still lists as ready but whose
    symbol is here has already shipped. The caller reads the log (`git log --format=%B`); this
    takes its text, so it is tested without git.

    Returns:
        the distinct symbols.

    """
    return frozenset(cast("list[str]", _TRAILER.findall(log)))


def with_edits(rows: list[Row], dirty: Collection[str]) -> list[Row]:
    """Keep the rows whose manifest has at least one file edited in the tree.

    ⚑ A CARD WITH NO EDITED MANIFEST FILE HAS NOTHING TO SUBMIT: a stack of an unchanged file
    is an empty commit, so the kata skips it. A row with no files at all is kept, because an
    empty manifest says nothing about what changed (nemik counts those and does not list them,
    so this is a guard, not a case).

    Returns:
        the rows in the order given.

    """
    changed = set(dirty)
    return [row for row in rows if not row.files or changed.intersection(row.files)]


def submit_set(rows: list[Row], landed: Collection[str]) -> list[Row]:
    """Pick the rows to submit now: STACK rows whose card has not already landed.

    Returns:
        the STACK rows, in the order given, without any whose symbol is in `landed`.

    """
    done = set(landed)
    return [row for row in rows if row.state == STACK and row.symbol not in done]

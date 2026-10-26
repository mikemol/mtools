# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List ready cards whose symbol leads a landed commit's subject, with its open markers (W2033).

A card can be ready while a commit has already landed under its symbol. Most are not ghosts: the
commit landed one part and the subject says so (`step one`, `first slice`, `NOT DONE`). Measured on
mtools by github-8f (2026-10-25): of 97 ready cards, 10 had a landing commit and none was a true
ghost, so the answer is a LIST for a reader to judge, never a close.

⚑ THIS LISTS AND NEVER CLOSES. The open markers a subject uses vary and no table of them is
complete, so a card with no marker is still only a candidate; the reader decides.
⚑ NO LOG IS A REFUSAL, NOT AN EMPTY LIST: a log that could not be read must not read as "no ghosts".

CONSUMED BY: `cli` (`--ghosts`).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from mikemol.pathsforward import landed
from mikemol.pathsforward.model import RefusedError, State, text
from mikemol.pathsforward.reconcile import Commit
from mikemol.pathsforward.reconcilecmd import Log, parse_log

_LEAD = re.compile(r"^(W[0-9]+)\b")
_MARKERS = (
    "NOT DONE",
    "step one",
    "first slice",
    "first part",
    "second rung",
    "third part",
    "fourth part",
    "remain",
)
_SHOWN = 100
_SHA = 7


@dataclass(frozen=True, slots=True)
class Ghost:
    """One ready card and a commit that leads with its symbol."""

    symbol: str
    sha: str
    markers: tuple[str, ...]
    subject: str


def markers_in(subject: str) -> tuple[str, ...]:
    """Find the open markers a subject uses.

    Returns:
        the markers present, in the order of the table, matched without regard to case.

    """
    lowered = subject.lower()
    return tuple(m for m in _MARKERS if m.lower() in lowered)


def candidates(ready: Iterable[str], commits: Iterable[Commit]) -> list[Ghost]:
    """Pair each ready card with the commits whose first line leads with its symbol.

    Returns:
        one Ghost per such commit, newest first as the commits were given.

    """
    wanted = set(ready)
    found: list[Ghost] = []
    for commit in commits:
        subject = commit.body.split("\n", 1)[0]
        lead = _LEAD.match(subject)
        if lead is not None and lead.group(1) in wanted:
            found.append(Ghost(lead.group(1), commit.sha, markers_in(subject), subject))
    return found


def line(ghost: Ghost) -> str:
    """Render one candidate for the reader.

    Returns:
        the symbol, the short sha, the markers (or `no marker`) and the head of the subject.

    """
    said = ", ".join(ghost.markers) if ghost.markers else "no marker"
    return f"{ghost.symbol}  {ghost.sha[:_SHA]}  [{said}]  {ghost.subject[:_SHOWN]}"


def report(state: State, root: Path, log: Log = landed.read_commits) -> list[str]:
    """Print each ready card that leads a landed commit's subject, then a count.

    Returns:
        one line per candidate commit, then a count line.

    Raises:
        RefusedError: when the git log cannot be read.

    """
    raw = log(root)
    if raw is None:
        msg = "git log could not be read"
        raise RefusedError(msg)
    ready = [text(w, "symbol") for w in state.waypoints if text(w, "status") == "ready"]
    found = candidates(ready, parse_log(raw))
    count = len({g.symbol for g in found})
    tally = f"{count} of {len(ready)} ready card(s) lead a landed commit's subject; none is closed"
    return [*(line(g) for g in found), tally]

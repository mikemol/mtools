# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Give each working card one verdict: GATING, LANDED or STALE (W1638).

⚑ NOTHING RECONCILED A WORKING CARD WITH WHAT HAD HAPPENED TO IT (operator, 2026-10-18, 695f3e0a
line 81610: 'I feel like I'm seeing Working cards that I thought had already landed? What do we
have for cleaning up Working cards?'): the only signals were nemik's stall warning and the landed
count at close. This is the pure part. It takes the queue, the commits since, and the stacks in the
gate, and says for each working card what is true of it and what to do about it.

⚑ THE THREE VERDICTS, IN THIS ORDER:
  GATING <stack id>  a queued or running stack carries its Waypoint (W1586's map of the gate).
  LANDED <sha>       a commit since the card went working names it by a `Waypoint: W<n>` line,
                     matched over the whole body as `landed.py` does, since nemik's commits put it
                     outside git's trailer block. A card that ships as a deployment is proposed
                     `landed`, not done (a commit is not a deploy, operator 2026-10-18); one whose
                     next step is empty is proposed done; any other is proposed ready.
  STALE              neither; proposed ready, or blocked when it still waits on an open card.
Nothing here writes.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from mikemol.pathsforward.landed import trailer_cards
from mikemol.pathsforward.model import Json, State, strlist, text

GATING = "GATING"
LANDED = "LANDED"
STALE = "STALE"


@dataclass(frozen=True)
class Commit:
    """A landed commit: its sha, when it was made (a sortable UTC stamp) and its whole message."""

    sha: str
    stamp: str
    body: str


@dataclass(frozen=True)
class Verdict:
    """What is true of one working card, and the status to propose for it."""

    symbol: str
    kind: str
    detail: str
    proposal: str


def gating_of(counts: object) -> dict[str, str]:
    """Read which stack carries which Waypoint from the live-commit map (W1586).

    Returns:
        waypoint mapped to the submission key of the first entry that names it; empty for a map
        that is not a mapping or whose entries carry no waypoints.

    """
    found: dict[str, str] = {}
    if not isinstance(counts, dict):
        return found
    for key, entry in cast("dict[object, object]", counts).items():
        if not isinstance(entry, dict):
            continue
        names = cast("dict[object, object]", entry).get("waypoints")
        if isinstance(names, list):
            for name in cast("list[object]", names):
                if isinstance(name, str):
                    found.setdefault(name, str(key))
    return found


def _open_blockers(card: Json, state: State) -> bool:
    # True when a blocker of the card is a live card of this queue that is not done.
    live = {text(w, "symbol"): text(w, "status") for w in state.waypoints}
    return any(live.get(b, "done") != "done" for b in strlist(card, "blocked_on"))


def _landing(symbol: str, since: str, commits: Sequence[Commit]) -> Commit | None:
    # The newest commit made at or after `since` that names the card.
    newest: Commit | None = None
    for commit in commits:
        if commit.stamp < since or symbol not in trailer_cards(commit.body):
            continue
        if newest is None or commit.stamp > newest.stamp:
            newest = commit
    return newest


def _proposal(card: Json) -> str:
    # What a landed commit means for the card: landed if it ships, done if nothing is left.
    if text(card, "deploys") == "True":
        return "landed"
    return "ready" if text(card, "next_bounded_step") else "done"


def verdicts(
    state: State,
    commits: Sequence[Commit],
    gating: Mapping[str, str],
    working_since: Mapping[str, str],
) -> list[Verdict]:
    """Judge every working card of the queue.

    `working_since` maps a symbol to the stamp it went working; a card with none is read from its
    own `issued_at`, so an old card is looked for across every commit given.

    Returns:
        one verdict per working card, in queue order.

    """
    out: list[Verdict] = []
    for card in state.waypoints:
        if text(card, "status") != "working":
            continue
        symbol = text(card, "symbol")
        if symbol in gating:
            out.append(Verdict(symbol, GATING, gating[symbol], ""))
            continue
        since = working_since.get(symbol) or text(card, "issued_at")
        landed = _landing(symbol, since, commits)
        if landed is not None:
            out.append(Verdict(symbol, LANDED, landed.sha, _proposal(card)))
            continue
        status = "blocked" if _open_blockers(card, state) else "ready"
        out.append(Verdict(symbol, STALE, "", status))
    return out

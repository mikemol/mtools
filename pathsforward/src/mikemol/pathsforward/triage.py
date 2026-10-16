# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Propose the repairs that shrink a queue's ready frontier, never inventing a wait (W1332).

⚑ THE OPERATOR'S GOAL (2026-10-16, relayed): the fleet's unblocked frontier under 50, "whether by
finishing cards or by better planning; a broad ready frontier is unhealthy". Part of a broad
frontier is cards stored ready that are not: they wait on something the queue already says, or
they are one card said twice, or an umbrella's edge points the wrong way and hides its children.
This reads one queue and proposes those repairs. It CHANGES NOTHING; `apply` does, and the CLI
keeps the dry-run-first shape of `--block-behind-open`.

Three kinds, each a defect of RECORD and never a judgement about the work:

    ready-with-blocker  a card stored ready whose `blocked_on` still names an open card (or a
                        foreign card, or an operator ask): it is waiting and says it is not
    inverted-umbrella   U enables L AND U is blocked on L: a two-card ring in the record (paperkit
                        W305). L is U's child, so U waits for L; the edge is flipped. ⚑ `caused_by`
                        alone is not the signal: a follow-on card is also minted by its
                        predecessor, and that edge is a true prerequisite (found on mtools' own
                        W1327 and W1329 by the first version, which flagged it wrongly)
    duplicate           two open cards with the same touches and near-identical titles: the later
                        is dropped with the earlier named, the earlier is never touched

⚑ NOT PROPOSED, ON PURPOSE: closing a card as done (that needs a witness or the owner's evidence:
`--certify` and `--close-umbrellas` are the tools) and blocking a card on a guessed dependency. A
dependency that is not already in the record is not this tool's to invent.
"""

import re
from dataclasses import dataclass
from typing import cast

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import Json, State, strlist, text

_CLOSED = frozenset({"done", "dropped"})
_OPEN = frozenset({"ready", "working", "blocked"})
_WORD = re.compile(r"[a-z0-9]+")
_NAMING = "/._:#0123456789"
_MIN_WORDS = 4
_SIMILAR = 0.75
_OPERATOR = "operator"
_HUMAN = "human"
_AGENT = "agent"


@dataclass(frozen=True)
class Proposal:
    """One repair: which card, which kind, the line a dry run prints, and the card it concerns."""

    symbol: str
    kind: str
    said: str
    other: str = ""


def _words(title: str) -> set[str]:
    return set(cast("list[str]", _WORD.findall(title.lower())))


def _identifying(title: str) -> set[str]:
    """Pick the tokens of a title that name a particular thing: a path, a symbol, a number.

    ⚑ A SERIES OF CARDS DIFFERS ONLY IN THIS TOKEN. 'gabion debt: <path> (2 findings)' repeated
    over many files is one title with the file changed, and word overlap alone called 91 of
    gabion's cards duplicates on the first dry run (found by running it on a copy of the real queue,
    2026-10-16). Two titles are one card only if they name the same things.

    Returns:
        the whitespace tokens that carry a path separator, a dot, an underscore, a colon, a hash or
        a digit.

    """
    return {t for t in title.lower().split() if any(c in t for c in _NAMING)}


def _similar(a: str, b: str) -> bool:
    """Say whether two titles are near-identical.

    Returns:
        True when both have at least `_MIN_WORDS` words, name the same things, and overlap highly.

    """
    first, second = _words(a), _words(b)
    if len(first) < _MIN_WORDS or len(second) < _MIN_WORDS:
        return False
    if _identifying(a) != _identifying(b):
        return False
    return len(first & second) / len(first | second) >= _SIMILAR


def _waiting(w: Json, open_cards: set[str], known: set[str]) -> list[str]:
    """List what a card's `blocked_on` still waits on.

    Returns:
        the entries that are an open local card, a foreign card, or an operator ask; a local card
        that is closed or absent is left to `--prune-landed`.

    """
    waiting: list[str] = []
    for entry in strlist(w, "blocked_on"):
        local_open = entry in known and entry in open_cards
        if local_open or ":" in entry or entry.startswith(_OPERATOR):
            waiting.append(entry)
    return waiting


def _ready_with_blocker(state: State) -> list[Proposal]:
    known = {text(w, "symbol") for w in state.waypoints}
    open_cards = {text(w, "symbol") for w in state.waypoints if text(w, "status") not in _CLOSED}
    found: list[Proposal] = []
    for w in state.waypoints:
        waiting = _waiting(w, open_cards, known) if text(w, "status") == "ready" else []
        if waiting:
            sym = text(w, "symbol")
            said = f"WOULD BLOCK {sym} (stored ready, still waits on {', '.join(waiting)})"
            found.append(Proposal(sym, "ready-with-blocker", said))
    return found


def _inverted_umbrellas(state: State) -> list[Proposal]:
    by_symbol = {text(w, "symbol"): w for w in state.waypoints}
    found: list[Proposal] = []
    for umbrella in state.waypoints:
        parent = text(umbrella, "symbol")
        for child in strlist(umbrella, "enables"):
            leaf = by_symbol.get(child)
            if leaf is None or child not in strlist(umbrella, "blocked_on"):
                continue
            if text(leaf, "status") in _CLOSED or parent in strlist(leaf, "enables"):
                continue
            said = f"WOULD FLIP {parent} enables {child} (and waits on it): {child} enables it"
            found.append(Proposal(parent, "inverted-umbrella", said, child))
    return found


def _duplicates(state: State) -> list[Proposal]:
    cards = [w for w in state.waypoints if text(w, "status") in _OPEN]
    found: list[Proposal] = []
    gone: set[str] = set()
    for i, older in enumerate(cards):
        tags = set(strlist(older, "touches"))
        for newer in cards[i + 1 :]:
            sym = text(newer, "symbol")
            same = bool(tags) and tags == set(strlist(newer, "touches"))
            if not same or sym in gone or not _similar(text(older, "title"), text(newer, "title")):
                continue
            gone.add(sym)
            keep = text(older, "symbol")
            found.append(
                Proposal(sym, "duplicate", f"WOULD DROP {sym} (duplicate of {keep})", keep)
            )
    return found


def plan(state: State) -> list[Proposal]:
    """Propose every repair the three detectors find, changing nothing.

    Returns:
        the proposals, blocked cards first, then flipped edges, then duplicates.

    """
    return [*_ready_with_blocker(state), *_inverted_umbrellas(state), *_duplicates(state)]


def _block(card: Json) -> None:
    """Store a card as blocked, keeping its blockers; an operator ask makes the kind human."""
    asks = [e for e in strlist(card, "blocked_on") if e.startswith(_OPERATOR)]
    card["status"] = "blocked"
    card["blocked_kind"] = _HUMAN if asks else _AGENT
    card["ticks_blocked"] = 0


def _flip(parent: Json, child: Json) -> None:
    """Move the edge from the umbrella's `enables` to the child's."""
    gone = text(child, "symbol")
    parent["enables"] = [e for e in strlist(parent, "enables") if e != gone]
    child["enables"] = [*strlist(child, "enables"), text(parent, "symbol")]


def apply(state: State, found: list[Proposal], now: str) -> None:
    """Make each proposed repair through the writer's own moves.

    A blocked card keeps its blocker; a flipped edge leaves the umbrella and joins the child; a
    duplicate is dropped with the card it duplicates named in the reason.
    """
    by_symbol = {text(w, "symbol"): w for w in state.waypoints}
    for item in found:
        card = by_symbol.get(item.symbol)
        if card is None:
            continue
        if item.kind == "ready-with-blocker":
            _block(card)
        elif item.kind == "inverted-umbrella":
            _flip(card, by_symbol[item.other])
        elif item.kind == "duplicate":
            reason = f"duplicate of {item.other} (triage): same touches, near-identical title"
            ops.drop(state, item.symbol, reason, now)

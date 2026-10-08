# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The writer admits a transition through the realizability policy, behind `--admit` (W851).

⚑⚑ MINTING IS NEVER REFUSED, AND JUDGING NEVER BLOCKS A WRITE. A refusal throws the claim away, so
an add or an update is saved first and judged after: the verdict (a coordinate and a residue
ledger) is printed and persisted as a mark (W852), and a policy that cannot run (no pinned opa)
says so on the way out and changes nothing. The one refusal is a DROP that does not say where the
waypoint died: the gate, the arm it was judged against, and why. Without them a drop is a
deletion with no account, which is what the residue array exists to prevent.

⚑ THE ORDER IS SAVE, JUDGE, MARK (W534's rule for the ledger): a mark is appended only after the
state it describes is on disk, so the marks file never records a transition the queue does not
hold. A crash between the save and the mark loses a mark, never invents one.

`card_for` (W853) is the other direction: it judges a live waypoint and turns one residue entry's
`closes_by` into the draft of a claimable card, caused by the waypoint it belongs to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import certify, closure, inbound, marks, opa_eval, ops, store
from mikemol.pathsforward.model import RefusedError, strlist, text
from mikemol.pathsforward.realizable import GATES, one_line

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import Json, State


@dataclass(frozen=True)
class Site:
    """Where a transition happens: the queue file, where peer queues live, and the clock."""

    state_path: Path
    root: Path
    now: str


def died(gate: str | None, reference_arm: str | None, reason: str) -> dict[str, str]:
    """Check what a drop must say, and shape it for the residue entry.

    ⚑ BEFORE ANYTHING MOVES: the caller checks this ahead of the drop, so a refused drop leaves
    the waypoint live.

    Returns:
        {gate, reference_arm}, to be stored with the dropped waypoint.

    Raises:
        RefusedError: when the gate is missing or not one of the four, or the arm or reason is
            blank.

    """
    if gate not in GATES:
        msg = f"drop needs --gate, one of {', '.join(GATES)} (the gate it died at), got {gate!r}"
        raise RefusedError(msg)
    arm = one_line("drop reference arm (--reference-arm)", reference_arm or "")
    one_line("drop reason", reason)
    return {"gate": gate, "reference_arm": arm}


def mark_drop(site: Site, symbol: str, reason: str, account: dict[str, str]) -> None:
    """Append the mark for a drop that was saved."""
    marks.append(
        store.sibling(site.state_path, marks.MARKS),
        marks.dropped(site.now, symbol, account["gate"], account["reference_arm"], reason),
    )


def _verdict(state: State, symbol: str, site: Site) -> tuple[Json, Json]:
    """Build the policy input for one waypoint and judge it.

    Returns:
        (the item, its verdict).

    """
    where = certify.Where(inbound.repo_name(site.state_path), site.root)
    (item,) = certify.items(state, [symbol], where, site.now)
    (verdict,) = opa_eval.verdicts([item], opa_eval.resolve())
    return item, verdict


def admit(state: State, op: str, symbol: str, site: Site) -> str:
    """Judge the waypoint as the saved state holds it, mark it, and say its coordinate.

    Returns:
        one line: the level and the residue count, or why it was not judged.

    """
    try:
        item, verdict = _verdict(state, symbol, site)
    except (RefusedError, opa_eval.OpaUnavailableError, ValueError) as exc:
        return f"admit: {symbol} not judged ({exc})"
    marks.append(
        store.sibling(site.state_path, marks.MARKS), marks.judged(op, site.now, item, verdict)
    )
    found = verdict.get("residue")
    count = len(cast("list[object]", found)) if isinstance(found, list) else 0
    return f"admit: {symbol} {verdict.get('level')}, {count} residue"


def card_for(state: State, symbol: str, gate: str, site: Site) -> tuple[str, ops.Draft | None]:
    """Turn one residue entry of a live waypoint into the draft of a claimable card (W853).

    ⚑ NOTHING IS MINTED HERE: this judges and drafts, and the caller mints and saves. A card
    already minted for this waypoint and gate, or an entry whose `closes_ref` already names the
    card that closes it, yields no draft and says why.

    Returns:
        (a one-line account, the draft or None when nothing is to be minted).

    """
    _, verdict = _verdict(state, symbol, site)
    found = verdict.get("residue")
    residue = cast("list[Json]", found) if isinstance(found, list) else []
    entry = closure.entry_at(residue, gate)
    have = closure.existing(state, symbol, gate)
    if have is not None:
        return f"{symbol} {gate}: already minted as {have}", None
    # ⚑ ANY ENTRY AT THE GATE THAT CITES A CARD COUNTS: a deferral naming `closes_ref` and the
    # policy's own derived entry for the same gate are one gap, and the cited card closes it.
    refs = [
        text(e, "closes_ref") for e in residue if text(e, "gate") == gate and text(e, "closes_ref")
    ]
    if refs:
        return f"{symbol} {gate}: closes_ref {refs[0]} already names the card, minted none", None
    waypoint = next(w for w in state.waypoints if text(w, "symbol") == symbol)
    closes_by = text(entry, "closes_by")
    draft = ops.Draft(
        closure.title_for(symbol, gate, closes_by),
        next_step=closes_by,
        touches=tuple(strlist(waypoint, "touches")),
        caused_by=symbol,
    )
    return f"{symbol} {gate}: minting a card for: {closes_by}", draft

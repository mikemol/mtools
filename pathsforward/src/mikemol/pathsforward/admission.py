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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import certify, inbound, marks, opa_eval, store
from mikemol.pathsforward.model import RefusedError
from mikemol.pathsforward.realizable import GATES, one_line

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import State


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


def admit(state: State, op: str, symbol: str, site: Site) -> str:
    """Judge the waypoint as the saved state holds it, mark it, and say its coordinate.

    Returns:
        one line: the level and the residue count, or why it was not judged.

    """
    where = certify.Where(inbound.repo_name(site.state_path), site.root)
    try:
        (item,) = certify.items(state, [symbol], where, site.now)
        (verdict,) = opa_eval.verdicts([item], opa_eval.resolve())
    except (RefusedError, opa_eval.OpaUnavailableError, ValueError) as exc:
        return f"admit: {symbol} not judged ({exc})"
    marks.append(
        store.sibling(site.state_path, marks.MARKS), marks.judged(op, site.now, item, verdict)
    )
    found = verdict.get("residue")
    count = len(cast("list[object]", found)) if isinstance(found, list) else 0
    return f"admit: {symbol} {verdict.get('level')}, {count} residue"

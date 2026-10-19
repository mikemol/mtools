# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Print the reconciler's plan for the working cards and, with a write, record each verdict (W1639).

⚑ A DRY RUN FIRST, AS `--freeze` AND `--block-matching`: without `--write` nothing is saved and
each line reads WOULD; with it, a LANDED card goes to its proposal with the verdict written into
its evidence, and a STALE card goes back to ready (or blocked). The status change reaches the
ledger as the `status` line `_mutate` already writes for every transition (W1372).

⚑ NO GATE MAP IS A REFUSAL, NOT AN EMPTY MAP: a card whose stack is still in the gate would read
STALE and be sent back to ready while its commit was minutes from landing, so a map that could
not be read stops the command before anything is judged.

⚑ A `landed` PROPOSAL IS PRINTED AND NEVER APPLIED here: the writer's `landed` status is a later
card (W1642/W1643), and a status the writer cannot yet take must not be set by a side door.

The reads are seams (`reads`) so a test hands in text and never runs git.
"""

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from mikemol.pathsforward import landed, reconcile
from mikemol.pathsforward.model import Json, RefusedError, State, text

GATING_NOTE = "the live-commit map could not be read (is mikemol-commit on PATH?)"
_FIELD = "\x1f"
_RECORD = "\x1e"
_FIELDS = 3
LANDED_PROPOSAL = "landed"
Log = Callable[[Path], str | None]
Gate = Callable[[], str | None]


def parse_log(raw: str) -> list[reconcile.Commit]:
    """Read `git log --format=%H<US>%cd<US>%B<RS>` into commits.

    Returns:
        one commit per well-formed record, newest first as git printed them.

    """
    out: list[reconcile.Commit] = []
    for record in raw.split(_RECORD):
        parts = record.strip("\n").split(_FIELD, 2)
        if len(parts) == _FIELDS and parts[0].strip():
            out.append(reconcile.Commit(parts[0].strip(), parts[1].strip(), parts[2]))
    return out


def gate_map(raw: str | None) -> dict[str, str] | None:
    """Read `mikemol-commit --in-gate --json` into waypoint -> submission key.

    Returns:
        the map, empty for an empty gate; None when the text is absent or is not the list.

    """
    if raw is None:
        return None
    try:
        rows: object = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(rows, list):
        return None
    keyed = {
        str(cast("dict[str, object]", row).get("key")): row
        for row in cast("list[object]", rows)
        if isinstance(row, dict)
    }
    return reconcile.gating_of(keyed)


def plan_line(verdict: reconcile.Verdict, *, write: bool) -> str:
    """Spell one verdict as a line, WOULD or done by `write`.

    Returns:
        the line.

    """
    head = f"{verdict.symbol} {verdict.kind}"
    if verdict.kind == reconcile.GATING:
        return f"{head} {verdict.detail}: left working"
    detail = f" {verdict.detail}" if verdict.detail else ""
    if verdict.proposal == LANDED_PROPOSAL:
        return f"{head}{detail}: proposes landed, which the writer cannot yet take (not applied)"
    verb = "SET" if write else "WOULD SET"
    return f"{head}{detail}: {verb} {verdict.proposal}"


def apply(state: State, verdicts: Sequence[reconcile.Verdict], now: str) -> list[str]:
    """Write each applicable verdict into the queue: status, and the verdict in evidence.

    Returns:
        the symbols changed.

    """
    changed: list[str] = []
    by_symbol = {text(w, "symbol"): w for w in state.waypoints}
    for verdict in verdicts:
        card: Json | None = by_symbol.get(verdict.symbol)
        if card is None or verdict.kind == reconcile.GATING or not verdict.proposal:
            continue
        if verdict.proposal == LANDED_PROPOSAL:
            continue
        card["status"] = verdict.proposal
        old = text(card, "evidence")
        note = f"{now[:10]}: reconciled {verdict.kind} {verdict.detail}".rstrip()
        card["evidence"] = f"{old} | {note}" if old else note
        if verdict.proposal == "done":
            card["completed"] = now
        changed.append(verdict.symbol)
    return changed


def real_reads(root: Path) -> tuple[Log, Gate]:
    """Pair the real git log with the real live-commit map of the repo at `root`.

    Returns:
        the two reads `run` takes.

    """
    return landed.read_commits, lambda: landed.read_gate(root)


def run(
    state: State, root: Path, *, write: bool, reads: tuple[Log, Gate] | None = None
) -> list[str]:
    """Judge the working cards and return the plan lines, writing the verdicts when asked.

    `reads` is the pair (git log, live-commit map), each a seam; none means the real ones.

    Returns:
        one line per working card, then a count line.

    Raises:
        RefusedError: when the gate map or the git log cannot be read.

    """
    log, gate = reads or real_reads(root)
    gating = gate_map(gate())
    if gating is None:
        raise RefusedError(GATING_NOTE)
    raw = log(root)
    if raw is None:
        msg = "git log could not be read"
        raise RefusedError(msg)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    found = reconcile.verdicts(state, parse_log(raw), gating, {})
    lines = [plan_line(v, write=write) for v in found]
    changed = apply(state, found, now) if write else []
    lines.append(f"{len(found)} working; {len(changed)} changed" + ("" if write else " (dry run)"))
    return lines

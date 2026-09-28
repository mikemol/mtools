# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Leases over `touches[]` (W177): a `working` waypoint's artifact writes, held by the loop.

⚑ THE OWNER IS THE LOOP, NOT THE PROCESS (.claude/design/W50-touches-lease.md, W119 point 1).
The holder is the name `--lock` already records, so a claim survives compaction and restart.

⚑ ONLY A LEASABLE TAG IS LEASED (W120 point 3): an artifact grain (`file:`/`mod:`) marked `!w`.
Two reads never collide; a topic or a party names no bytes.

⚑ THIS DECIDES; `store.exclusive` MAKES IT ATOMIC, as for the lock. Nothing here touches the
filesystem or git: the caller supplies `now` and `base_sha`.

⚑ A CONFLICT REFUSES THE WHOLE TAKE. Half a set of leases would let the tick work an item whose
other writes someone else holds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward.lock import LOCK_STALE_S, parse_time, stamp
from mikemol.pathsforward.tags import parse_tag

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from mikemol.pathsforward.model import Json, State

# ⚑ EQUAL TO THE LOCK'S STALE BOUND (W119 point 4), so a lapse and a lock takeover agree.
LEASE_TTL_S = LOCK_STALE_S
_KEY = "leases"


@dataclass(frozen=True)
class Claimant:
    """Who takes a lease, from which tree, and when: the caller's facts, never looked up here."""

    holder: str
    base_sha: str
    now: datetime


@dataclass(frozen=True)
class Conflict:
    """A leasable tag another waypoint holds unexpired."""

    tag: str
    waypoint: str
    holder: str


def leases(state: State) -> list[Json]:
    """Read the `leases` field.

    Returns:
        the lease records, or an empty list when the field is absent or not a list.

    """
    raw = state.doc.get(_KEY)
    if not isinstance(raw, list):
        return []
    return [cast("Json", x) for x in cast("list[object]", raw) if isinstance(x, dict)]


def _key(raw: str) -> tuple[str, str]:
    tag = parse_tag(raw)
    return tag.grain, tag.name


def _expired(lease: Json, now: datetime) -> bool:
    at = parse_time(str(lease.get("expires_at", "")))
    return at is None or at <= now


def take(state: State, waypoint: str, touches: Sequence[str], who: Claimant) -> list[Conflict]:
    """Lease every leasable tag of `waypoint`, or none of them.

    A tag this waypoint already holds is renewed. An expired lease never blocks.

    Returns:
        the conflicts, empty on success. On a conflict nothing is written.

    """
    wanted = [t for t in touches if parse_tag(t).leasable]
    held = leases(state)
    others = {
        _key(str(x.get("tag", ""))): x
        for x in held
        if x.get("waypoint") != waypoint and not _expired(x, who.now)
    }
    conflicts = [
        Conflict(t, str(others[_key(t)].get("waypoint")), str(others[_key(t)].get("holder")))
        for t in wanted
        if _key(t) in others
    ]
    if conflicts:
        return conflicts
    expires = stamp(who.now + timedelta(seconds=LEASE_TTL_S))
    kept = [x for x in held if x.get("waypoint") != waypoint]
    kept.extend(
        {
            "tag": t,
            "holder": who.holder,
            "waypoint": waypoint,
            "base_sha": who.base_sha,
            "taken_at": stamp(who.now),
            "renewed_at": stamp(who.now),
            "expires_at": expires,
        }
        for t in wanted
    )
    state.doc[_KEY] = kept
    return []


def release(state: State, waypoint: str) -> int:
    """Drop every lease `waypoint` holds, as it leaves `working`.

    Returns:
        how many were dropped.

    """
    held = leases(state)
    kept = [x for x in held if x.get("waypoint") != waypoint]
    state.doc[_KEY] = kept
    return len(held) - len(kept)


def renew(state: State, holder: str, head_sha: str, now: datetime) -> list[str]:
    """Extend every lease `holder` has (W119 point 5), and say which trees have moved.

    Returns:
        the tags whose `base_sha` is not `head_sha`: the stale-tree case, reported, not refused.

    """
    expires = stamp(now + timedelta(seconds=LEASE_TTL_S))
    moved: list[str] = []
    for x in leases(state):
        if x.get("holder") != holder:
            continue
        x["renewed_at"] = stamp(now)
        x["expires_at"] = expires
        if x.get("base_sha") != head_sha:
            moved.append(str(x.get("tag", "")))
    return moved


def lapsed(state: State, now: datetime) -> list[Json]:
    """List the leases past `expires_at` (W119 point 6: the caller ledgers each one).

    Returns:
        the lapsed records; an unparseable `expires_at` counts as lapsed.

    """
    return [x for x in leases(state) if _expired(x, now)]

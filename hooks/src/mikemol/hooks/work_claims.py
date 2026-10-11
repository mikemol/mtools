# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure parts of a session claiming the touches of the card it is working (mtools:W993).

⚑ THE DECLARATION TRAVELS WITH THE CARD (mtools:W889, `.claude/design/W889-work-claims.md`): a
card's `touches` tags say where it works, and shared tags are a reason to coordinate. A session
working a card takes `claim:label:touch:<repo>:<tag>` for each tag through the fence `claim` verb
(W911), so a peer about to start under the same tag is told WHO is there and since when instead of
deferring by judgment. The claim is owned by the SESSION process, not by the short hook command, so
it outlives the command and is reaped by the ledger's gc when the session dies.

⚑ ADVISORY WITH A NAME ON IT. A refusal becomes a context line naming the holder, and never a
block: two sessions can have good reason to share a tag, and the commit claim is the only true
mutex.

Nothing here reads the machine. The queue, the process ancestry, `/proc/<pid>/stat` and the
`claims` listing are all arguments, so the tests run on strings; the effectful half is the hook.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.hooks.payload import as_record

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

LABEL_PREFIX = "claim:label:touch:"
SESSION_NAME = "claude"
_WORKING = "working"
_MAX_DEPTH = 32
_STARTTIME_AFTER_COMM = 22 - 3
_PPID_AFTER_COMM = 1
_OWNER_KEY = "owner="
_REFUSED = "REFUSED — "


@dataclass(frozen=True, slots=True)
class Plan:
    """What a prompt must do about claims: take the missing ones, release the unwanted ones."""

    take: tuple[str, ...]
    release: tuple[str, ...]


def touch_label(repo: str, tag: str) -> str:
    """Name the claim a repo's touches tag makes.

    Returns:
        `claim:label:touch:<repo>:<tag>`.

    """
    return f"{LABEL_PREFIX}{repo}:{tag}"


def wanted(queue: object, repo: str) -> list[str]:
    """List the claims the working cards of a queue ask for.

    ⚑ ONLY A `working` CARD CLAIMS: a ready card is a plan, not a presence, and a done one has
    stopped. Tags are deduplicated across cards and sorted so the answer is stable.

    Returns:
        the sorted claim labels, empty when nothing is working or the queue is unreadable.

    """
    waypoints = as_record(queue).get("waypoints")
    if not isinstance(waypoints, list):
        return []
    tags: set[str] = set()
    for item in cast("list[object]", waypoints):
        card = as_record(item)
        touches = card.get("touches")
        if card.get("status") != _WORKING or not isinstance(touches, list):
            continue
        tags.update(tag for tag in cast("list[object]", touches) if isinstance(tag, str) and tag)
    return sorted(touch_label(repo, tag) for tag in tags)


def _after_comm(stat: str) -> list[str]:
    """Split a `/proc/<pid>/stat` line after its comm field, which may hold spaces and `)`.

    Returns:
        the fields from the state onward.

    """
    return stat[stat.rfind(")") + 2 :].split(" ")


def starttime_of(stat: str) -> str | None:
    """Read a process's start time, field 22 of its stat line.

    Returns:
        the start time in clock ticks as text, or None when the line is too short.

    """
    fields = _after_comm(stat)
    return fields[_STARTTIME_AFTER_COMM] if len(fields) > _STARTTIME_AFTER_COMM else None


def parent_of(stat: str) -> int | None:
    """Read a process's parent pid, field 4 of its stat line.

    Returns:
        the parent pid, or None when the line is too short or the field is not a number.

    """
    fields = _after_comm(stat)
    if len(fields) <= _PPID_AFTER_COMM or not fields[_PPID_AFTER_COMM].isdecimal():
        return None
    return int(fields[_PPID_AFTER_COMM])


def owner_string(pid: int, stat: str) -> str | None:
    """Name a process the way the ledger does, `pid:starttime`.

    Returns:
        the owner string, or None when the stat line has no start time.

    """
    start = starttime_of(stat)
    return None if start is None else f"{pid}:{start}"


def session_pid(
    start: int,
    comm_of: Callable[[int], str | None],
    parent: Callable[[int], int | None],
    name: str = SESSION_NAME,
) -> int | None:
    """Find the session process: the nearest ancestor of `start` whose command name is `name`.

    ⚑ THE HOOK'S OWN PARENT IS A SHELL THAT EXITS WITH IT. The claim must be owned by the
    long-lived session above it, so the ancestry is walked, bounded, until a process called `name`
    is found.

    Returns:
        the pid, or None when no ancestor has that name (so the caller claims nothing).

    """
    pid: int | None = start
    for _ in range(_MAX_DEPTH):
        if pid is None or pid <= 1:
            return None
        if comm_of(pid) == name:
            return pid
        pid = parent(pid)
    return None


def claims_of(listing: str) -> dict[str, str]:
    """Read the `claims` verb's listing into label -> owner.

    Returns:
        each listed claim's label and its `pid:starttime` owner; lines it cannot read are skipped.

    """
    held: dict[str, str] = {}
    for line in listing.splitlines():
        words = line.split(" ")
        owner = next((w[len(_OWNER_KEY) :] for w in words if w.startswith(_OWNER_KEY)), "")
        if words[0].startswith(LABEL_PREFIX) and owner:
            held[words[0]] = owner
    return held


def plan(want: Iterable[str], held: dict[str, str], owner: str) -> Plan:
    """Decide which claims to take and which to release.

    ⚑ ONLY THIS SESSION'S OWN CLAIMS ARE RELEASED: a touch claim held by another owner is its
    holder's, so it is never dropped here even when this session no longer wants the tag.

    Returns:
        the labels to take (wanted, and not already held by this owner) and to release (held by
        this owner, a touch claim, and no longer wanted).

    """
    wished = list(want)
    mine = {label for label, who in held.items() if who == owner}
    return Plan(
        take=tuple(label for label in wished if label not in mine),
        release=tuple(sorted(label for label in mine if label not in wished)),
    )


def advice(label: str, refusal: str) -> str:
    """Turn a refused claim into the context line a peer's session shows.

    Returns:
        one line naming the tag and what the ledger said about its holder.

    """
    detail = refusal.strip().splitlines()[-1] if refusal.strip() else "held"
    detail = detail.split(_REFUSED, 1)[-1]
    tag = label.removeprefix(LABEL_PREFIX)
    return f"work claim: {tag} is held elsewhere ({detail}); coordinate before editing under it."

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The state's mutations, pure: each takes a State and a timestamp and edits it in place.

⚑⚑ TYPED FIELDS, NOT `key=value` (sre's `update`). el-openglo's `--set W24 status=bogus
blocked_on=mikemol` exited 0 and the mirror then read `| W24 | bogus |`. Here a status or a kind
outside its enum is refused, `blocked_on` is always a list, and an update that would leave a
waypoint blocked without a party is refused whole.

⚑ `ticks_blocked` RESETS WHEN THE BLOCK CHANGES (skill section 5). sre's never reset, so a
re-blocked item inherited the old count and skipped its first nudges.

⚑ VALIDATE BEFORE MINTING (el-openglo). A refused `add` leaves the counter untouched; a burned
symbol with a partial record is indistinguishable from an honest one.

⚑ `bump_blocked` DOES NOT TOUCH `heartbeat`. sre's rewrote it, so an idle tick that only counted
blocks looked like a tick that re-armed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from mikemol.pathsforward.model import (
    BLOCKED_KINDS,
    STATUSES,
    strlist,
    symbol_number,
    text,
    ticks,
)

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

NUDGE_TICKS: tuple[int, ...] = (1, 2, 4, 8)
ESCALATE_TICK = 16
_DATE = 10
_UNBLOCKING = ("ready", "done")


class RefusedError(ValueError):
    """A mutation that would leave the file wrong; nothing was changed."""


class Action(StrEnum):
    """What the idle tick owes a blocked waypoint this tick."""

    NUDGE = "NUDGE"
    ESCALATE = "ESCALATE"
    QUIET = "quiet"


@dataclass(frozen=True)
class Nudge:
    """One blocked waypoint's count after a bump, and what it is owed."""

    symbol: str
    ticks: int
    action: Action
    blocked_on: tuple[str, ...]
    kind: str


@dataclass(frozen=True)
class Update:
    """The typed fields `--update` may set; None means leave alone."""

    status: str | None = None
    blocked_on: tuple[str, ...] | None = None
    blocked_kind: str | None = None
    next_step: str | None = None
    evidence_append: str | None = None
    ticks_blocked: int | None = None
    title: str | None = None


@dataclass(frozen=True)
class Draft:
    """A waypoint to mint."""

    title: str
    next_step: str = ""
    enables: tuple[str, ...] = ()
    touches: tuple[str, ...] = ()


def find(state: State, sym: str) -> Json:
    """Resolve a symbol to its live waypoint (skill section 2: waypoints first, then residue).

    Returns:
        the live waypoint.

    Raises:
        RefusedError: naming the residue reason, or saying the symbol was never issued.

    """
    for w in state.waypoints:
        if text(w, "symbol") == sym:
            return w
    for rec in state.residue:
        if text(rec, "symbol") == sym:
            msg = f"{sym} is residue ({text(rec, 'dropped_at')}): {text(rec, 'reason')}"
            raise RefusedError(msg)
    msg = f"{sym}: in neither waypoints nor residue (counter={state.counter})"
    raise RefusedError(msg)


def _refuse_enums(upd: Update) -> None:
    """Refuse a status or kind outside its enum, whoever called.

    Raises:
        RefusedError: on a value outside STATUSES or BLOCKED_KINDS, or a negative count.

    """
    if upd.status is not None and upd.status not in STATUSES:
        msg = f"status {upd.status!r} is not one of {', '.join(STATUSES)}"
        raise RefusedError(msg)
    if upd.blocked_kind is not None and upd.blocked_kind not in BLOCKED_KINDS:
        msg = f"blocked_kind {upd.blocked_kind!r} is not one of {', '.join(BLOCKED_KINDS)}"
        raise RefusedError(msg)
    if upd.ticks_blocked is not None and upd.ticks_blocked < 0:
        msg = f"ticks_blocked {upd.ticks_blocked} is negative"
        raise RefusedError(msg)
    _refuse_title(upd.title)


def _refuse_title(title: str | None) -> None:
    """Refuse a title that is blank or spans lines; a waypoint's title is its one-line name.

    ⚑ A TITLE GOES STALE: mtools' W24 kept "substrate offers three hooks additions…" long after
    its work changed, and `--update` had no way to say so.

    Raises:
        RefusedError: on a blank title, or one carrying a line break.

    """
    if title is None:
        return
    if not title.strip():
        msg = "title is empty"
        raise RefusedError(msg)
    if "\n" in title or "\r" in title:
        msg = f"title {title!r} is not a single line"
        raise RefusedError(msg)


def _set_given(new: Json, upd: Update) -> None:
    """Set each plain field the update gives, over whatever the status change implied."""
    given: dict[str, object | None] = {
        "blocked_on": None if upd.blocked_on is None else list(upd.blocked_on),
        "blocked_kind": upd.blocked_kind,
        "next_bounded_step": upd.next_step,
        "title": upd.title,
    }
    new.update({key: value for key, value in given.items() if value is not None})


def _applied(w: Json, upd: Update, now: str) -> Json:
    """Compute the waypoint an update produces, without touching the original.

    Returns:
        the new waypoint.

    """
    new = dict(w)
    if upd.status is not None:
        new["status"] = upd.status
        if upd.status in _UNBLOCKING:
            new["blocked_on"], new["blocked_kind"] = [], None
        if upd.status == "done":
            new["next_bounded_step"] = ""
    _set_given(new, upd)
    if upd.evidence_append is not None:
        old = text(w, "evidence")
        entry = f"{now[:_DATE]}: {upd.evidence_append}"
        new["evidence"] = f"{old} | {entry}" if old else entry
    was_blocked = text(w, "status") == "blocked"
    if (text(new, "status") == "blocked") != was_blocked or (
        strlist(new, "blocked_on") != strlist(w, "blocked_on")
    ):
        new["ticks_blocked"] = 0
    if upd.ticks_blocked is not None:
        new["ticks_blocked"] = upd.ticks_blocked
    new["last_worked"] = now
    return new


def update(state: State, sym: str, upd: Update, now: str) -> Json:
    """Apply typed fields to a live waypoint, all or nothing.

    Returns:
        the updated waypoint.

    Raises:
        RefusedError: on an enum violation, or a result blocked without a party and a kind.

    """
    _refuse_enums(upd)
    w = find(state, sym)
    new = _applied(w, upd, now)
    if text(new, "status") == "blocked" and (
        not strlist(new, "blocked_on") or text(new, "blocked_kind") not in BLOCKED_KINDS
    ):
        msg = f"{sym}: blocked needs --blocked-on and --blocked-kind agent|human"
        raise RefusedError(msg)
    w.clear()
    w.update(new)
    return w


def add(state: State, draft: Draft, now: str) -> str:
    """Mint the next symbol as a ready waypoint, validating first.

    Returns:
        the minted symbol.

    Raises:
        RefusedError: on an empty title or a malformed edge; the counter is untouched.

    """
    if not draft.title.strip():
        msg = "add refused, nothing minted: the title is empty"
        raise RefusedError(msg)
    bad = [e for e in draft.enables if symbol_number(e) is None]
    if bad:
        msg = f"add refused, nothing minted: enables {bad} are not W<n> symbols"
        raise RefusedError(msg)
    # ⚑⚑ A SYMBOL IS NEVER ISSUED TWICE (skill section 2). A counter that lags a claimed symbol
    # would re-mint it: measured 2026-09-25 (nemik: rosettapkg W6), counter=5 with W6 in residue
    # minted a LIVE W6. Refused, not skipped past: a lagging counter is a finding for the file's
    # owner, which `--check` names; this tool reports and does not repair (D8).
    claimed = [
        n
        for rec in (*state.waypoints, *state.residue)
        if (n := symbol_number(text(rec, "symbol"))) is not None and n > state.counter
    ]
    if claimed:
        msg = (
            f"add refused, nothing minted: counter={state.counter} lags claimed "
            f"W{max(claimed)}; run --check"
        )
        raise RefusedError(msg)
    counter = state.counter + 1
    sym = f"W{counter}"
    state.doc["counter"] = counter
    state.waypoints.append(
        {
            "symbol": sym,
            "title": draft.title,
            "status": "ready",
            "enables": list(draft.enables),
            "touches": list(draft.touches),
            "blocked_on": [],
            "blocked_kind": None,
            "next_bounded_step": draft.next_step,
            "evidence": "",
            "issued_at": now,
            "last_worked": None,
            "ticks_blocked": 0,
        }
    )
    return sym


def drop(state: State, sym: str, reason: str, now: str) -> None:
    """Move a live waypoint to residue (skill section 5); the reason is required.

    Raises:
        RefusedError: on an empty reason, or a symbol that is not live.

    """
    if not reason.strip():
        msg = f"drop {sym}: a reason is required"
        raise RefusedError(msg)
    w = find(state, sym)
    state.waypoints.remove(w)
    state.residue.append(
        {
            "symbol": sym,
            "title": text(w, "title"),
            "dropped_at": now,
            "reason": reason,
            "recoverable": True,
        }
    )


def action_for(count: int) -> Action:
    """Map a blocked-tick count to what it is owed: backoff at 1, 2, 4, 8, escalate once at 16.

    Returns:
        the action.

    """
    if count == ESCALATE_TICK:
        return Action.ESCALATE
    return Action.NUDGE if count in NUDGE_TICKS else Action.QUIET


def bump_blocked(state: State, exclude: frozenset[str]) -> list[Nudge]:
    """Count one more blocked tick on every blocked waypoint not excluded.

    Returns:
        one Nudge per bumped waypoint, in queue order.

    """
    out: list[Nudge] = []
    for w in state.waypoints:
        sym = text(w, "symbol")
        if text(w, "status") != "blocked" or sym in exclude:
            continue
        count = ticks(w) + 1
        w["ticks_blocked"] = count
        out.append(
            Nudge(
                sym,
                count,
                action_for(count),
                tuple(strlist(w, "blocked_on")),
                text(w, "blocked_kind"),
            )
        )
    return out


def arm(state: State, job_id: str, now: str) -> None:
    """Record the verified job and the heartbeat (skill section 4.3).

    ⚑ THE OUTGOING `job_id` BECOMES `predecessor_job_id` BEFORE IT IS OVERWRITTEN: it is the job
    the re-arm must delete. Re-recording the same id keeps the predecessor it already had.

    Raises:
        RefusedError: on an empty job id.

    """
    if not job_id.strip():
        msg = "armed: the job id is empty"
        raise RefusedError(msg)
    previous = text(state.doc, "job_id")
    if previous and previous != job_id:
        state.doc["predecessor_job_id"] = previous
    state.doc["job_id"] = job_id
    state.doc["heartbeat"] = now


def set_preamble(state: State, lines: list[str]) -> None:
    """Store the standing rules the payload emits verbatim.

    Raises:
        RefusedError: when every line is blank (clear it instead).

    """
    if not any(line.strip() for line in lines):
        msg = "preamble has 0 non-blank lines; use --preamble-clear"
        raise RefusedError(msg)
    state.doc["preamble"] = lines


def clear_preamble(state: State) -> int:
    """Remove the stored preamble.

    Returns:
        how many lines were removed.

    """
    count = len(strlist(state.doc, "preamble"))
    state.doc.pop("preamble", None)
    return count

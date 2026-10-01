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
from itertools import starmap
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import lock, recurrence, timevalue, vector
from mikemol.pathsforward.model import (
    BLOCKED_KINDS,
    STATUSES,
    RefusedError,
    is_reference,
    strlist,
    symbol_number,
    text,
    ticks,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mikemol.pathsforward.model import Json, State

# RefusedError moved to model (W256) and is re-exported here for every existing importer.
__all__ = ["RefusedError"]

NUDGE_TICKS: tuple[int, ...] = (1, 2, 4, 8)
ESCALATE_TICK = 16
_DATE = 10
_UNBLOCKING = ("ready", "done")


def _bad_edges(edges: Iterable[str]) -> list[str]:
    """Name the edges that are neither a local `W<n>` nor another repo's `repo:W<n>`.

    Returns:
        each malformed edge, in order.

    """
    return [e for e in edges if not is_reference(e)]


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
    # ⚑ SET, NOT MERGED: `--update --enables` states the whole edge list, so a comma-joined edge
    # (el-openglo W49, measured by nemik 2026-09-25) has a repair path.
    enables: tuple[str, ...] | None = None
    weight: int | None = None
    # ⚑ SET, NOT MERGED, like `enables` (nemik:W50, 2026-09-27): three comma-joined tags
    # ("adapter,cleanup") were accepted at --add and had no repair path until --update took it.
    touches: tuple[str, ...] | None = None
    # ⚑ A WITNESS IS DATA, NEVER RUN HERE (nemik:W59 rev 3, 2026-09-27): a single-line Rego query
    # over nemik-observed input. nemik's observers and `opa eval` decide it; this tool neither
    # parses nor validates the Rego, and only refuses a query that is empty or not one line.
    witness: str | None = None
    # ⚑ A VECTOR IS CHECKED, NEVER SCORED HERE (W248, W256): vector.parse refuses one outside the
    # WV:1 grammar; nemik reads the stored string and owns the band.
    vector: str | None = None
    vector_source: str | None = None
    # ⚑ A MIS-CITED CAUSE IS FIXED IN PLACE (W305, nemik:W136, 2026-10-01): caused_by could be set
    # only at --add, so a wrong repo prefix (nemik W105/W107 cited luthen:, not
    # luthen-observability:) could be repaired only by drop and re-add, which re-mints the symbol
    # and breaks every citation of it. "" clears the field.
    caused_by: str | None = None
    # ⚑ RFC 5545 TIME, STORED AS WRITTEN (W300, life:W23): DTSTART and DUE, each checked by
    # timevalue.parse, so a floating time is refused before it is stored. "" clears the field.
    dtstart: str | None = None
    due: str | None = None
    # ⚑ VALARM TRIGGERS, SET NOT MERGED (W279, life:W23, nemik:W129): `--alarm` states the whole
    # list, and `--alarm` with no values clears it. Stored and projected here. Firing them is
    # nemik-wake's job (nemik:W129), never this tool's.
    alarms: tuple[str, ...] | None = None
    # ⚑ RECURRENCE (W309, life:W23, nemik:W145): an RRULE ('' clears) and its EXDATEs (SET, not
    # merged; () clears), stored as written. Expanding them is the reader's job, never this tool's.
    rrule: str | None = None
    exdates: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Draft:
    """A waypoint to mint."""

    title: str
    next_step: str = ""
    enables: tuple[str, ...] = ()
    touches: tuple[str, ...] = ()
    caused_by: str = ""
    witness: str = ""


def minted_during(state: State, now: str) -> str:
    """Say whether a mint happens inside a tick or interrupts one, from the tick lock alone.

    ⚑ THE TOOL DERIVES IT, NOT THE CALLER (nemik, 2026-09-25): a caller asked to say which it is
    answers from recall. A lock held under LOCK_STALE_S is a tick; none, a stale one, or an
    unreadable stamp is an interrupt.

    Returns:
        "tick" or "interrupt".

    """
    held = lock.current(state)
    if held is None:
        return "interrupt"
    taken, at = lock.parse_time(held[1]), lock.parse_time(now)
    if taken is None or at is None:
        return "interrupt"
    return "tick" if (at - taken).total_seconds() < lock.LOCK_STALE_S else "interrupt"


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
    bad = _bad_edges(upd.enables or ())
    if bad:
        msg = f"enables {bad} are not W<n> or repo:W<n> symbols"
        raise RefusedError(msg)
    _refuse_title(upd.title)
    _refuse_witness(upd.witness)
    _refuse_vector(upd.vector, upd.vector_source)


def _refuse_vector(vec: str | None, source: str | None) -> None:
    """Refuse a vector outside the WV:1 grammar, or one written without its provenance.

    ⚑ BOTH OR NEITHER (W256): a vector with no source is a score nobody can audit, and a
    source with no vector describes nothing.

    Raises:
        RefusedError: on a malformed vector or source, or only one of the pair.

    """
    if vec is None and source is None:
        return
    if vec is None or source is None:
        msg = "vector and vector_source are written together"
        raise RefusedError(msg)
    vector.parse(vec)
    vector.refuse_source(source)


def _refuse_witness(query: str | None) -> None:
    """Refuse a witness that is blank or spans lines; its Rego is never read here.

    Raises:
        RefusedError: on a blank query, or one carrying a line break.

    """
    if query is None:
        return
    if not query.strip():
        msg = "witness is empty"
        raise RefusedError(msg)
    if "\n" in query or "\r" in query:
        msg = f"witness {query!r} is not a single line"
        raise RefusedError(msg)


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


_ANCHOR = {"START": "dtstart", "END": "due"}


def _refuse_unanchored(sym: str, new: Json) -> None:
    """Refuse an alarm the resulting waypoint cannot place.

    ⚑ CHECKED ON THE RESULT, NOT THE REQUEST: a relative TRIGGER needs DTSTART (RELATED=START) or
    DUE (RELATED=END) on the waypoint as it will be saved, so clearing a time that an alarm still
    counts from is refused as well as adding the alarm without one.

    Raises:
        RefusedError: on a malformed TRIGGER, or a relative one whose anchor field is unset.

    """
    for alarm in strlist(new, "alarms"):
        try:
            trigger = timevalue.parse_trigger(alarm)
        except RefusedError as exc:
            msg = f"{sym}: alarm {exc}"
            raise RefusedError(msg) from None
        anchor = _ANCHOR.get(trigger.related or "")
        if anchor is not None and not text(new, anchor):
            msg = (
                f"{sym}: alarm {alarm!r} is relative to {anchor.upper()}, which is unset: "
                f"set --{anchor} first, or use VALUE=DATE-TIME:...Z"
            )
            raise RefusedError(msg)


def _refuse_bad_recurrence(sym: str, new: Json) -> None:
    """Refuse a recurrence the resulting waypoint cannot expand (W309).

    ⚑ CHECKED ON THE RESULT, like the alarms: an RRULE counts from DTSTART (RFC 5545 3.8.5.3), so
    both an RRULE without one and clearing a DTSTART a rule still counts from are refused. EXDATE
    only removes occurrences, so it needs an RRULE to remove them from.

    Raises:
        RefusedError: on a malformed RRULE or EXDATE, an RRULE with no DTSTART, or an EXDATE with
            no RRULE.

    """
    rule = text(new, "rrule")
    reason = ""
    if rule and not text(new, "dtstart"):
        reason = "rrule needs a DTSTART to count from: set --dtstart first"
    elif strlist(new, "exdates") and not rule:
        reason = "exdate removes occurrences of an rrule, and there is none: set --rrule first"
    if reason:
        msg = f"{sym}: {reason}"
        raise RefusedError(msg)
    try:
        if rule:
            recurrence.check(rule)
        for exdate in strlist(new, "exdates"):
            timevalue.parse(exdate)
    except RefusedError as exc:
        msg = f"{sym}: {exc}"
        raise RefusedError(msg) from None


def _set_given(new: Json, upd: Update) -> None:
    """Set each plain field the update gives, over whatever the status change implied."""
    given: dict[str, object | None] = {
        "blocked_on": None if upd.blocked_on is None else list(upd.blocked_on),
        "blocked_kind": upd.blocked_kind,
        "next_bounded_step": upd.next_step,
        "title": upd.title,
        "enables": None if upd.enables is None else list(upd.enables),
        "weight": upd.weight,
        "touches": None if upd.touches is None else list(upd.touches),
        "witness": upd.witness,
        "vector": upd.vector,
        "vector_source": upd.vector_source,
    }
    new.update({key: value for key, value in given.items() if value is not None})
    if upd.caused_by is not None:
        new["caused_by"] = upd.caused_by or None
    for key, value in (("dtstart", upd.dtstart), ("due", upd.due)):
        if value is not None:
            new[key] = value or None
    if upd.alarms is not None:
        new["alarms"] = list(upd.alarms) or None
    if upd.rrule is not None:
        new["rrule"] = upd.rrule or None
    if upd.exdates is not None:
        new["exdates"] = list(upd.exdates) or None


def _is_work(upd: Update) -> bool:
    """Say whether an update records WORK on the item, as opposed to metadata about it.

    ⚑ A METADATA WRITE IS NOT WORK (luthen via nemik, 2026-09-27): a per-tick `--weight` sync
    rewrote `last_worked` on 49 of 49 items, erasing the age-since-worked that the loop and the
    nudge backoff read. So `weight`, `title`, `enables`, `touches`, `witness` and `ticks_blocked`
    (bookkeeping the loop itself keeps) leave the stamp alone. Status, blockers, the next step
    and evidence are the fields a tick writes BECAUSE it worked the item.

    Returns:
        True when any work field is given.

    """
    given = (upd.status, upd.blocked_on, upd.blocked_kind, upd.next_step, upd.evidence_append)
    return any(value is not None for value in given)


def _completed(w: Json, status: str, now: str) -> str | None:
    """Compute the COMPLETED stamp a status change leaves (RFC 5545 3.8.2.1, W301).

    ⚑ Stamped ONCE, at the transition to done, from the injected clock: a second done keeps the
    first stamp, and reopening clears it.

    Returns:
        the UTC DATE-TIME, or None for a waypoint that is not done.

    """
    if status != "done":
        return None
    return text(w, "completed") or now.replace("-", "").replace(":", "")


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
            new["next_bounded_step"] = None
        new["completed"] = _completed(w, upd.status, now)
    _set_given(new, upd)
    # A blank --next is no next step: null, not "" (linux-sources' reconcile check refuses ""
    # on a done waypoint, and patched it by hand four times, W64 W69 W70 W71, 2026-09-26).
    if upd.next_step is not None and not upd.next_step.strip():
        new["next_bounded_step"] = None
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
    if _is_work(upd):
        new["last_worked"] = now
    return new


def update(state: State, sym: str, upd: Update, now: str) -> Json:
    """Apply typed fields to a live waypoint, all or nothing.

    Returns:
        the updated waypoint.

    Raises:
        RefusedError: on an enum violation, a caused_by that is not one token, or a result blocked
            without a party and a kind.

    """
    _refuse_enums(upd)
    if upd.caused_by is not None and any(ch.isspace() for ch in upd.caused_by):
        # The same one-token rule --add applies, so the two routes cannot disagree.
        msg = f"{sym}: caused_by {upd.caused_by!r} is not one token"
        raise RefusedError(msg)
    for name, value in (("dtstart", upd.dtstart), ("due", upd.due)):
        if value:
            try:
                timevalue.parse(value)
            except RefusedError as exc:
                msg = f"{sym}: {name} {exc}"
                raise RefusedError(msg) from None
    w = find(state, sym)
    new = _applied(w, upd, now)
    _refuse_unanchored(sym, new)
    _refuse_bad_recurrence(sym, new)
    if text(new, "status") == "blocked" and (
        not strlist(new, "blocked_on") or text(new, "blocked_kind") not in BLOCKED_KINDS
    ):
        # ⚑ THE UMBRELLA IS NAMED IN THE REFUSAL (W111, nemik): after an ATOMIZE split, the parent
        # waits on its own children, and "blocked on whom?" has an answer the refusal can give.
        msg = (
            f"{sym}: blocked needs --blocked-on and --blocked-kind agent|human"
            f" (an umbrella split into children: --blocked-on W<child> ... --blocked-kind agent)"
        )
        raise RefusedError(msg)
    w.clear()
    w.update(new)
    return w


def _pair(i: int, rec: object) -> tuple[str, int]:
    """Read one `{symbol, weight}` record of a weights file.

    Returns:
        the (symbol, weight) pair.

    Raises:
        RefusedError: naming the record's index, on any other shape.

    """
    if not isinstance(rec, dict):
        msg = f"weights[{i}] is not an object"
        raise RefusedError(msg)
    fields = cast("dict[str, object]", rec)
    sym, value = fields.get("symbol"), fields.get("weight")
    if not isinstance(sym, str) or not sym:
        msg = f"weights[{i}] has no string symbol"
        raise RefusedError(msg)
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"weights[{i}] {sym}: weight {value!r} is not an integer"
        raise RefusedError(msg)
    return sym, value


def weights_from(raw: object) -> list[tuple[str, int]]:
    """Parse a weights file's document: a list of `{symbol, weight}` objects.

    ⚑ A SYMBOL NAMED TWICE IS REFUSED: which of two weights the file meant is not ours to guess,
    and last-one-wins would make the file's order a silent input.

    Returns:
        the (symbol, weight) pairs in file order.

    Raises:
        RefusedError: on a non-list, a malformed record, or a repeated symbol.

    """
    if not isinstance(raw, list):
        msg = "a weights file is a JSON list of {symbol, weight} objects"
        raise RefusedError(msg)
    pairs = list(starmap(_pair, enumerate(cast("list[object]", raw))))
    syms = [sym for sym, _ in pairs]
    repeated = sorted({sym for sym in syms if syms.count(sym) > 1})
    if repeated:
        msg = f"weights name {', '.join(repeated)} more than once"
        raise RefusedError(msg)
    return pairs


def set_weights(state: State, pairs: list[tuple[str, int]], now: str) -> int:
    """Store every weight, or none: each symbol is resolved before the first write.

    ⚑ ALL OR NOTHING (nemik:W43): a sync that wrote half its weights and then hit an unknown
    symbol leaves a queue ordered by two different rankings at once, with nothing to say so.
    Weights are metadata, so `last_worked` is untouched (W117).

    Returns:
        how many waypoints were written.

    Raises:
        RefusedError: naming every symbol that is not live, before anything is written.

    """
    unknown: list[str] = []
    for sym, _ in pairs:
        try:
            find(state, sym)
        except RefusedError:
            unknown.append(sym)
    if unknown:
        msg = f"weights name {', '.join(unknown)}, which are not live waypoints; nothing written"
        raise RefusedError(msg)
    for sym, value in pairs:
        update(state, sym, Update(weight=value), now)
    return len(pairs)


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
    bad = _bad_edges(draft.enables)
    if bad:
        msg = f"add refused, nothing minted: enables {bad} are not W<n> or repo:W<n> symbols"
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
    if any(ch.isspace() for ch in draft.caused_by):
        msg = f"add refused, nothing minted: caused_by {draft.caused_by!r} is not one token"
        raise RefusedError(msg)
    _refuse_witness(draft.witness or None)
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
            "minted_during": minted_during(state, now),
            "caused_by": draft.caused_by or None,
            "last_worked": None,
            "ticks_blocked": 0,
            **({"witness": draft.witness} if draft.witness else {}),
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


def prune_done(state: State) -> list[str]:
    """Drop blockers that are this queue's own waypoints and are now done.

    ⚑ A PARENT BLOCKED ON FINISHED CHILDREN READS AS STUCK (nemik:W55, 2026-09-27): after an
    atomize, nemik W17 stayed blocked on [W45 done, W46 done, W47]. Only a LOCAL symbol can be
    checked here, so a foreign `repo:W<n>` or an agent name is kept. A list that empties returns
    the item to ready; a list that only shrinks restarts its blocked count, as `--update` does.

    Returns:
        the symbols returned to ready, in queue order.

    """
    done = {text(w, "symbol") for w in state.waypoints if text(w, "status") == "done"}
    freed: list[str] = []
    for w in state.waypoints:
        on = strlist(w, "blocked_on")
        kept = [b for b in on if b not in done]
        if text(w, "status") != "blocked" or kept == on:
            continue
        w["blocked_on"], w["ticks_blocked"] = kept, 0
        if not kept:
            w["status"], w["blocked_kind"] = "ready", None
            freed.append(text(w, "symbol"))
    return freed


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

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The state file's shape: what a waypoint is, and the refusal of a document that is not one.

⚑ STRUCTURE IS REFUSED HERE; CONTENT IS JUDGED BY `check`. A document whose `waypoints` is not a
list of objects cannot be hashed, rendered or repaired, so it is refused at the door (summit's
`_waypoints`). A waypoint whose `status` is `bogus` or whose `blocked_on` is a bare string CAN
still be loaded — that is what lets `--update` repair it — and `check` reports it.

⚑ A SYMBOL IS PARSED, NEVER `int()`-ED. gabion's check crashed on `Wx` with a ValueError; here a
malformed symbol parses to `None` and every caller decides what that means.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

Json = dict[str, object]

STATUSES: tuple[str, ...] = ("ready", "blocked", "working", "done")
BLOCKED_KINDS: tuple[str, ...] = ("agent", "human")
NO_SYMBOL = "--"

_SYMBOL = re.compile(r"W([1-9][0-9]*)")
# ⚑ A WORKSTREAM'S NAME IS ONE SEGMENT OR SEVERAL, joined by `/` (mtools:W882, nemik:W224): a queue
# nested under another is cited by its path. Each segment is shaped like today's repo name and so
# starts with a letter or digit: `..`, `.hidden`, an empty segment and a leading `/` are not names.
_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_FOREIGN = re.compile(rf"({_SEGMENT}(?:/{_SEGMENT})*):W([1-9][0-9]*)")
_RANK: dict[str, int] = {"working": 0, "ready": 1, "blocked": 2}


class MalformedStateError(ValueError):
    """The document is not a paths-forward state; it is refused, never guessed at."""


# Lives here, not in ops, so a validator ops calls (vector, W256) can raise it without a cycle.
class RefusedError(ValueError):
    """A mutation that would leave the file wrong; nothing was changed."""


@dataclass(frozen=True)
class State:
    """A validated state document, with its two record lists bound to the document itself.

    Mutating `waypoints` or `residue` mutates `doc`, so a save writes what was changed and every
    top-level key a repo added (`goal`, `cadence`, `standing`, ...) survives the round trip.
    """

    doc: Json
    waypoints: list[Json]
    residue: list[Json]
    counter: int


def symbol_number(sym: object) -> int | None:
    """Parse `W<n>` to `n`.

    Returns:
        the positive integer, or None for anything that is not exactly `W<n>` with n >= 1.

    """
    if not isinstance(sym, str):
        return None
    match = _SYMBOL.fullmatch(sym)
    return int(match.group(1)) if match else None


def foreign_symbol(sym: object) -> tuple[str, int] | None:
    """Parse another repo's `repo:W<n>` (e.g. `luthen-observability:W55`) to its repo and `n`.

    ⚑ A FOREIGN SYMBOL IS NEVER A LOCAL ONE: `symbol_number` stays local-only, so no local check
    (the counter, a dangling edge, residue) ever reads another repo's number as its own
    (nemik, 2026-09-25, who resolves these into cross-repo edges).

    Returns:
        (repo, n), or None for anything that is not exactly `<repo>:W<n>`.

    """
    if not isinstance(sym, str):
        return None
    match = _FOREIGN.fullmatch(sym)
    return (str(match.group(1)), int(match.group(2))) if match else None


def is_reference(sym: object) -> bool:
    """Say whether `sym` names a waypoint: a local `W<n>` or another repo's `repo:W<n>`.

    Returns:
        True for either form.

    """
    return symbol_number(sym) is not None or foreign_symbol(sym) is not None


def _records(doc: Json, key: str) -> list[Json]:
    """Validate one record list: a list of objects, each carrying a string `symbol`.

    Returns:
        the list, as stored in `doc`.

    Raises:
        MalformedStateError: when the list or any record in it is malformed.

    """
    raw = doc.get(key)
    if not isinstance(raw, list):
        msg = f"`{key}` is not a list"
        raise MalformedStateError(msg)
    records = cast("list[object]", raw)
    for index, rec in enumerate(records):
        if not isinstance(rec, dict):
            msg = f"`{key}[{index}]` is not an object"
            raise MalformedStateError(msg)
        if not isinstance(cast("Json", rec).get("symbol"), str):
            msg = f"`{key}[{index}]` has no string `symbol`"
            raise MalformedStateError(msg)
    return cast("list[Json]", records)


def validate(raw: object) -> State:
    """Refuse anything that is not structurally a state document.

    An absent `residue` is created empty, because the skill's schema carries it and a drop
    needs somewhere to go; nothing else is invented.

    Returns:
        the validated state.

    Raises:
        MalformedStateError: when the document is not an object, a record list is malformed,
            or `counter` is not a non-negative integer.

    """
    if not isinstance(raw, dict):
        msg = "the state document is not a JSON object"
        raise MalformedStateError(msg)
    doc = cast("Json", raw)
    doc.setdefault("residue", [])
    counter = doc.get("counter")
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
        msg = f"`counter` is {counter!r}, not a non-negative integer"
        raise MalformedStateError(msg)
    return State(doc, _records(doc, "waypoints"), _records(doc, "residue"), counter)


def text(rec: Json, key: str) -> str:
    """Read a field as text.

    Returns:
        the field as a string, or "" when it is absent or null.

    """
    value = rec.get(key)
    return "" if value is None else str(value)


def strlist(rec: Json, key: str) -> list[str]:
    """Read a list field, guarding against a bare string.

    ⚑ A STRING IS AN ITERABLE OF CHARACTERS: el-openglo's payload once printed
    `blocked_on=m,i,k,e,m,o,l` for five ticks. A bare string is read as ONE element here, and
    `check` still reports it as the wrong type.

    Returns:
        the elements as strings; [] when absent.

    """
    value = rec.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in cast("list[object]", value)]
    return [str(value)]


def strmap(rec: Json, key: str) -> dict[str, str]:
    """Read a map field of strings, such as completed occurrences (W310).

    Returns:
        the entries as strings; {} when absent or not a map.

    """
    value = rec.get(key)
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in cast("dict[object, object]", value).items()}


def workable(w: Json) -> bool:
    """Say whether a tick may pick this waypoint: working or ready, and carrying no witness.

    ⚑ A WITNESSED ITEM IS NEVER WORKABLE (nemik:W64, 2026-09-27): its evaluator, not a mind,
    marks it done, so even one wrongly left `ready` must not top the queue or keep a loop live.
    `--check` still reports that status (W132); this keeps the loop safe until it is fixed.

    Returns:
        True when a tick may work it.

    """
    return text(w, "status") in {"working", "ready"} and not text(w, "witness")


def _rank(w: Json) -> int:
    """Rank a waypoint's status: working, ready, blocked, then anything else.

    A witnessed working/ready item ranks with blocked: nothing a tick can do advances it.

    Returns:
        the rank.

    """
    if text(w, "witness") and not workable(w) and text(w, "status") in _RANK:
        return max(_RANK[text(w, "status")], _RANK["blocked"])
    return _RANK.get(text(w, "status"), len(_RANK))


def _blockers_of(sym: str, waypoints: list[Json]) -> list[str]:
    """Find every other waypoint whose `blocked_on` names `sym`.

    Returns:
        the blocked waypoints' own symbols, in file order.

    """
    return [
        text(other, "symbol") for other in waypoints if sym and sym in strlist(other, "blocked_on")
    ]


def blocker_index(waypoints: list[Json]) -> dict[str, list[str]]:
    """Map each symbol to the waypoints blocked on it, in one pass over the queue.

    ⚑ ONE PASS, NOT ONE PER WAYPOINT (mtools:W973). `ordered` scored every waypoint by scanning the
    whole queue for who it unblocks, which is quadratic: 1,500 cards cost four seconds a view and a
    payload builds several views. The answer for `sym` is `index.get(sym, [])`, identical to
    `_blockers_of`, including a blocker named twice by one waypoint counting once.

    Returns:
        for each blocker symbol, the symbols of the waypoints naming it in `blocked_on`, file order.

    """
    index: dict[str, list[str]] = {}
    for other in waypoints:
        seen: set[str] = set()
        for blocker in strlist(other, "blocked_on"):
            if blocker and blocker not in seen:
                seen.add(blocker)
                index.setdefault(blocker, []).append(text(other, "symbol"))
    return index


def leverage(w: Json, waypoints: list[Json]) -> int:
    """Score a waypoint's structural leverage: what it enables, plus who it unblocks.

    ⚑ OUT-DEGREE OF `enables` PLUS IN-DEGREE OF `blocked_on` (skill section 3's starting shape).
    A foreign `enables` target (`repo:W<n>`) counts exactly like a local one — a waypoint that
    unblocks another repo is not less of a lever for the edge being cross-repo.

    Returns:
        the leverage score; higher sorts earlier within a status bucket.

    """
    sym = text(w, "symbol")
    return len(strlist(w, "enables")) + len(_blockers_of(sym, waypoints))


def weight(w: Json) -> int:
    """Read a waypoint's stored weight: an operator's or an agent's explicit priority.

    ⚑ MISSING IS 0, AND SO IS MALFORMED: a repo that never sets a weight keeps today's order
    byte-for-byte, and a non-integer is `check`'s to report, not the sort's to crash on. A bool is
    not a weight even though Python calls it an int.

    Returns:
        the integer weight, or 0.

    """
    value = w.get("weight")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def describe_rank(w: Json, waypoints: list[Json], index: dict[str, list[str]] | None = None) -> str:
    """State one waypoint's leverage in the skill's own vocabulary (collapse/unblock/sweep).

    ⚑ THIS NEVER WRITES `rank_reason` — a manually-set value in the state file is left alone by
    every view that only reads it. This is a pure, on-demand description for a view that has none
    stored, not a recomputation of one that does.

    ⚑ A CALLER DESCRIBING EVERY ROW PASSES `blocker_index(waypoints)` ONCE (mtools:W977): the scan
    for who a card unblocks is then a lookup, where a scan per row made the queue view quadratic.
    Both answer the same.

    Returns:
        "unblocks ...", "enables ...", both joined, or "sweep: ..." when neither applies.

    """
    sym = text(w, "symbol")
    enables = strlist(w, "enables")
    unblocks = _blockers_of(sym, waypoints) if index is None else list(index.get(sym, []))
    parts = []
    if unblocks:
        parts.append(f"unblocks {', '.join(unblocks)}")
    if enables:
        parts.append(f"enables {', '.join(enables)}")
    return "; ".join(parts) if parts else "sweep: enables nothing, unblocks nothing"


def ordered(waypoints: list[Json]) -> list[Json]:
    """Order waypoints working, ready, blocked, then any other status.

    ⚑ ONE ORDER FOR EVERY VIEW: the payload, `--queue` and the mirror all call this, so the three
    cannot disagree about what comes first. A blocked W22 listed above a ready W24 put a tick's
    attention on the item it cannot work. The payload then hides `done`; the views keep it last.

    ⚑ WITHIN A STATUS BUCKET, higher `leverage` sorts first (skill section 3: unblock/collapse
    over sweep). Ties — the common case, since most waypoints touch no local `enables`/
    `blocked_on` edge — fall back to file order: the index is folded into the key itself, since
    two waypoints (plain `dict`s) are not otherwise orderable once their keys tie.

    ⚑ A STORED `weight` OUTRANKS LEVERAGE (nemik:W43): leverage is what the graph can see, a weight
    is a judgment the graph cannot, and the skill says make that judgment rather than defer it to a
    formula. Only a status bucket outranks it — a heavy blocked item is still not workable.

    Returns:
        the waypoints, stably sorted by (status rank, -weight, -leverage, file order).

    """
    index = blocker_index(waypoints)
    keyed = [
        (
            (
                _rank(w),
                -weight(w),
                -(len(strlist(w, "enables")) + len(index.get(text(w, "symbol"), []))),
                i,
            ),
            w,
        )
        for i, w in enumerate(waypoints)
    ]
    keyed.sort(key=_first)
    return [w for _, w in keyed]


def _first(pair: tuple[tuple[int, int, int, int], Json]) -> tuple[int, int, int, int]:
    """Read a `(key, waypoint)` pair's key, for `list.sort`.

    Returns:
        the key.

    """
    return pair[0]


def ticks(rec: Json) -> int:
    """Read `ticks_blocked`.

    Returns:
        the count, or 0 when it is absent or not an integer.

    """
    value = rec.get("ticks_blocked")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0

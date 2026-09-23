# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Size a memory lease from the run ledger's history, and climb it when the cap kills the payload.

Ported by design from substrate's `scripts/membudget` (`_auto_mb`, the retry block of `cmd_run`,
`cmd_verify_ceiling`), per its autosize letter of 2026-09-22. The pure half — the size, the single
cap, the next rung, the climb trigger — comes first; `climb`, over `admit` and `run_once`, sits on
top of it and decides nothing they did not already decide.

⚑⚑ THE STEP IS THE MARGIN. A lease is the power-of-two bucket of the MAX recorded peak — not the
median, which under-sizes the tail — so a peak in (2^(n-1), 2^n] leases 2^n. `ledger.bucket` is the
one function the report and the lease share; it is imported, never restated.

⚑⚑⚑ ONE CAP FOR SIZE AND CLIMB — THE ORIGIN'S LIVE INCONSISTENCY, NOT PORTED. An explicit default
above the ceiling RAISES the ceiling (`cap = max(ceiling, default)`; measured at the origin: a
module peaking ~600MB with DEFAULT=1024 was sized fine until history existed, then silently clamped
to 384 and OOM-killed). The origin's retry then clamped to the bare ceiling and ignored that raise,
so a killed 384 lease could never climb past 384. Here `cap` is computed once and used by both.

⚑⚑ THE CLIMB IS TRIGGERED BY THE COUNTERS, NEVER BY THE EXIT CODE. 137 is any SIGKILL and 143 any
SIGTERM; only `MEMORY, KILLED` in `Result.bound_by` (memory.events oom_kill > 0) says the cap did
it. A payload that `kill -9`s itself must not climb.

⚑ THE CEILING HAS NO UNIVERSAL DEFAULT. The origin's 384 is substrate-tuned, and the origin itself
calls whether it is right UNRESOLVED; it is a parameter here.

CONSUMED BY: the `mikemol-membudget` console script that closes the fence set.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.fence import admit, core
from mikemol.fence.ledger import bucket

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.fence.core import Result

# The verdict prefix `cgroup.bound_by` gives a memory cap that KILLED, as opposed to one that
# throttled.
_MEMORY_KILLED = "MEMORY, KILLED"

# Each rung doubles the last.
_CLIMB_FACTOR = 2


def cap_of(ceiling: int, default: int) -> int:
    """Return the one cap both sizing and climbing obey: the ceiling, raised by a larger default.

    Returns:
        `max(ceiling, default)`.

    """
    return max(ceiling, default)


@dataclass(frozen=True, slots=True)
class Sizing:
    """A lease size, and — when the cap cut it down — the peak it was cut down from."""

    mb: int
    clamped_from: float | None = None


def size(peaks: Sequence[float], *, default: int, ceiling: int) -> Sizing:
    """Return the lease for a key whose recorded peaks are `peaks`.

    ⚑ NO HISTORY IS THE DEFAULT, NOT A GUESS FROM NOTHING — and the default is itself under the one
    cap, since the cap is at least the default.

    Returns:
        the size, carrying the peak it was clamped from when the cap cut it.

    """
    if not peaks:
        return Sizing(default)
    top = max(peaks)
    want = bucket(top)
    cap = cap_of(ceiling, default)
    if want > cap:
        return Sizing(cap, clamped_from=top)
    return Sizing(want)


def clamp_warning(key: str, sizing: Sizing, cap: int) -> str | None:
    """Return the stderr line a clamped size owes its reader, or None when nothing was clamped.

    ⚑ CLAMPING IS LOUD: a silent clamp is how a 600MB module was leased 384 and OOM-killed with a
    clean-looking size on stdout. The line names the key, the peak, the cap, and what raises it.

    Returns:
        the warning, or None.

    """
    if sizing.clamped_from is None:
        return None
    return (f"autosize: {key} peaked at {sizing.clamped_from:g} MB but the cap is {cap} MB — "
            f"leasing {sizing.mb} MB; raise the ceiling, or declare a default above it")


def killed_by_cap(result: Result) -> bool:
    """Report whether the memory cap KILLED the payload — the only thing a climb answers.

    Returns:
        True only when `bound_by` carries a memory KILL; a throttle or a bare 137 is False.

    """
    return any(verdict.startswith(_MEMORY_KILLED) for verdict in result.bound_by)


def next_rung(mb: int, cap: int) -> int | None:
    """Return the next lease on the climb, or None when the cap is already reached.

    ⚑ BOUNDED: the climb stops at the cap rather than looping, and the kill it stopped on is the
    result the caller gets.

    Returns:
        `min(2 * mb, cap)`, or None at the cap.

    """
    if mb >= cap:
        return None
    return min(_CLIMB_FACTOR * mb, cap)


# --- the effectful half: the climb ---

# The default request a climb re-admits under: no label and no parent. Only its label and parent are
# read — each rung supplies its own size.
TOP_LEVEL = admit.Request(0)


@dataclass(frozen=True, slots=True)
class Plan:
    """A climb: where it starts, the one cap it stops at, and whether it may climb at all.

    ⚑ `retry` IS THE CALLER'S DECLARATION THAT THE ACTION IS IDEMPOTENT. Without it one rung runs
    and its kill is the result. `request` carries the label and the ORIGINAL parent every rung
    re-enters admission under; its size is ignored.
    """

    start_mb: int
    cap: int
    retry: bool
    request: admit.Request = TOP_LEVEL


def rung_caps(mb: int) -> core.Caps:
    """Return one rung's caps: the lease as the memory cap, and NO swap.

    ⚑⚑ `swap="0"` IS MANDATORY, NOT A TUNING CHOICE. On a zram host a memory cap with swap allowed
    only THROTTLES — the payload spills and completes as `MEMORY, THROTTLED` — so `killed_by_cap`
    never fires and the climb never climbs.

    Returns:
        the caps.

    """
    return core.Caps(mem=f"{mb}M", swap="0")


def climb(
    store: admit.Store,
    cmd: Sequence[str],
    plan: Plan,
    waiting: admit.Waiting = admit.WAIT,
    host: admit.Host = admit.HOST,
) -> list[Result]:
    """Run `cmd` under a lease of `plan.start_mb`, climbing while the cap kills it and retry allows.

    ⚑⚑ EVERY RUNG RE-ENTERS ADMISSION UNDER THE ORIGINAL PARENT. The lease is released before the
    next is taken, and the next names `plan.request.parent` — never the lease just released, or the
    retry would be "a child of a corpse" that cascade-gc removes.

    Returns:
        every rung's result, in order; the last is the outcome.

    """
    results: list[Result] = []
    mb = plan.start_mb
    while True:
        rung = admit.Request(mb, plan.request.label, plan.request.parent)
        with admit.admit(store, rung, waiting, host):
            result = core.run_once(cmd, rung_caps(mb))
        results.append(result)
        if not plan.retry or not killed_by_cap(result):
            return results
        nxt = next_rung(mb, plan.cap)
        if nxt is None:
            return results
        mb = nxt

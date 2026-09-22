# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Size a memory lease from the run ledger's history, and climb it when the cap kills the payload.

Ported by design from substrate's `scripts/membudget` (`_auto_mb`, the retry block of `cmd_run`,
`cmd_verify_ceiling`), per its autosize letter of 2026-09-22. This is the PURE half — the size, the
single cap, the next rung, the climb trigger; the climb over `admit` + `run_once` sits on top.

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

CONSUMED BY: the climb (next), and the `mikemol-membudget` console script that closes the fence set.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

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

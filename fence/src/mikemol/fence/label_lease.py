# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Size a label's memory lease and its wall hang guard from the run ledger's history.

Ported from substrate's `substrate/label_lease.py` per its label-lease letter of 2026-09-22 — NOT
moved verbatim: its three TSV scanners are replaced by `ledger.parse` (they read a fence-written
fractional peak as no history at all), its bucket by `ledger.bucket` via `autosize.size`, and its
`child_cpu` by `core.Result.user_s/sys_s` from `wait4`.

⚑⚑ WALL IS ONLY A HANG GUARD; CPU IS THE WORK (ruled at the origin 2026-09-20). The guard is the
larger of `margin * slowest wall` and `hang_multiple * slowest CPU`, so an observed honest run is
never killed and a multi-threaded run (CPU > wall) is not either.

⚑ PER-LABEL IS THE CALLER'S KEY for work that runs once per label; it is the wrong key for per-core
work, which `module_lease` keys by the module argument instead (substrate `_auto_mb`'s `.agda` arm).
The caller chooses; `module_of` states the rule it chooses by.

⚑ A MODULE OF ITS OWN, NOT A MODE OF `mikemol-fence`, for the reason `peaks` gives: that command
fences whatever follows its flags. `python -m mikemol.fence.label_lease` is the entry until the
`mikemol-membudget` console script takes `lease` and `deadline` as verbs.

CONSUMED BY: substrate's `scripts/membudget` `_auto_mb` and `suite_run.timeout_for`, once landed.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.fence import autosize, ledger

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

# Substrate-tuned defaults for an extrapolation, not bounds on what a caller may ask.
FLOOR_S = 120
CEILING_S = 3600
MARGIN = 2
HANG_MULTIPLE = 4
_MINUTE = 60

_USAGE = ("usage: python -m mikemol.fence.label_lease {lease LEDGER LABEL DEFAULT_MB CEILING_MB"
          " | deadline LEDGER LABEL DEFAULT_S CEILING_S}\n")

# A mode, and its four operands; and the exit code for anything else.
_ARGS = 5
_USAGE_ERROR = 2


def peaks_of(rows: Iterable[ledger.Row], label: str) -> list[float]:
    """Return the maxRSS peaks recorded for exactly `label`, skipping rows that carry none.

    Returns:
        the peaks in file order; empty when the label is unmeasured.

    """
    return [row.peak_mb for row in rows if row.label == label and row.peak_mb is not None]


def lease(rows: Iterable[ledger.Row], label: str, *, default_mb: int,
          ceiling_mb: int) -> autosize.Sizing:
    """Return the memory lease for `label` — `autosize.size` over that label's peaks.

    Returns:
        the sizing; `clamped_from` set only when the cap cut it.

    """
    return autosize.size(peaks_of(rows, label), default=default_mb, ceiling=ceiling_mb)


def minutes_up(secs: float, floor_s: int = FLOOR_S) -> int:
    """Return `secs` rounded UP to a whole minute, never below `floor_s`.

    Returns:
        whole seconds, a multiple of 60 or the floor.

    """
    return max(floor_s, math.ceil(secs / _MINUTE) * _MINUTE)


def cpu_of(row: ledger.Row) -> float | None:
    """Return a row's CPU (user + sys), or None when either half is absent — never 0.

    ⚑ HALF A MEASUREMENT IS NO MEASUREMENT: a row with user but no sys is not "user seconds of CPU".

    Returns:
        the CPU seconds, or None.

    """
    if row.user_s is None or row.sys_s is None:
        return None
    return row.user_s + row.sys_s


@dataclass(frozen=True, slots=True)
class Deadline:
    """A wall hang guard, the history it was sized from, and the one cap it obeyed.

    ⚑ `cap_s` IS CARRIED, NOT RE-DERIVED, so the warning reports the EFFECTIVE cap (the ceiling
    raised by the default) rather than a module constant — the origin's `why` printed 3600 under
    `ceiling_s=5`.
    """

    timeout_s: int
    cap_s: int
    slowest_s: float | None = None
    cpu_s: float | None = None
    clamped: bool = False


@dataclass(frozen=True, slots=True)
class Guard:
    """The deadline's tunables — the origin's numbers as defaults, every one a parameter."""

    default_s: int
    ceiling_s: int = CEILING_S
    floor_s: int = FLOOR_S
    margin: float = MARGIN
    hang_multiple: float = HANG_MULTIPLE


def deadline(rows: Iterable[ledger.Row], label: str, guard: Guard) -> Deadline:
    """Budget the wall hang guard for `label`, or the default when it has no history.

    ⚑ THE DEFAULT IS RETURNED RAW, neither floored nor rounded: an operator who names one gets it.

    Returns:
        the deadline, `clamped` when the cap cut it.

    """
    cap = autosize.cap_of(guard.ceiling_s, guard.default_s)
    mine = [row for row in rows if row.label == label]
    if not mine:
        return Deadline(guard.default_s, cap)
    slowest = max(row.wall_s for row in mine)
    cpus = [cpu for cpu in map(cpu_of, mine) if cpu is not None]
    cpu = max(cpus) if cpus else None
    by_cpu = 0.0 if cpu is None else cpu * guard.hang_multiple
    want = minutes_up(max(slowest * guard.margin, by_cpu), guard.floor_s)
    return Deadline(min(want, cap), cap, slowest, cpu, clamped=want > cap)


def deadline_warning(label: str, got: Deadline) -> str | None:
    """Return the stderr line a clamped deadline owes its reader, or None.

    Returns:
        the warning naming the label, its slowest run, the effective cap, and `ceiling_s`; or None.

    """
    if not got.clamped or got.slowest_s is None:
        return None
    return (f"label_lease: {label} ran {got.slowest_s:.0f}s at its slowest but the cap is "
            f"{got.cap_s}s — budgeting {got.timeout_s}s, BELOW the measured need, which may kill "
            f"an honest run; raise ceiling_s or name a timeout explicitly")


# --- the effectful half: read the ledger file, print for the shell ---

def read_rows(path: Path) -> list[ledger.Row]:
    """Return the ledger's rows; a missing or unreadable ledger is no history, never an error.

    Returns:
        the rows, or empty.

    """
    try:
        return ledger.parse(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return []


# --- the per-module key: substrate `_auto_mb`'s `.agda` arm and `_record_time`'s write side ---

# What makes an argument a module identity, and the ledger that sits beside it. Spelled as bash
# spells them (`*.agda|*.agdai`, `$(dirname "$mod")/.agda-times.tsv`) so the two clients share it.
MODULE_SUFFIXES = (".agda", ".agdai")
MODULE_LEDGER_NAME = ".agda-times.tsv"


def module_of(command: Iterable[str]) -> Path | None:
    """Return the command's module — its LAST argument ending `.agda` or `.agdai` — or None.

    ⚑⚑ THE KEY RULE, EXPLICIT: the module is the last such argument ANYWHERE in the command (bash
    scans every "$@" word, the program included); its history lives in `.agda-times.tsv` in THAT
    ARGUMENT's directory, keyed by its BASENAME. So a `.agdai` under `_build/` reads a ledger
    beside itself, not the source's — a decode and a compile are different workloads on one name.

    Returns:
        the module's path as given, or None when no argument names one.

    """
    found = [arg for arg in command if arg.endswith(MODULE_SUFFIXES)]
    return Path(found[-1]) if found else None


def module_ledger(module: Path) -> Path:
    """Return the ledger that holds `module`'s history: `.agda-times.tsv` beside it.

    Returns:
        the path.

    """
    return module.parent / MODULE_LEDGER_NAME


def module_lease(module: Path, *, default_mb: int, ceiling_mb: int) -> autosize.Sizing:
    """Return `module`'s lease — `autosize.size` over THAT MODULE's peaks, never its label's.

    ⚑ A MISSING OR UNREADABLE LEDGER IS NO HISTORY, and no history is the default, as bash's
    `[ -f "$led" ] || { echo "$def"; return; }`.

    Returns:
        the sizing; `clamped_from` set only when the cap cut it.

    """
    try:
        text = module_ledger(module).read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    return autosize.size(ledger.key_peaks(text, module.name), default=default_mb,
                         ceiling=ceiling_mb)


@dataclass(frozen=True, slots=True)
class _Call:
    """One CLI invocation's operands, after the mode: the ledger, the label, and two integers."""

    ledger: Path
    label: str
    default: int
    ceiling: int


def _answer(number: int, warning: str | None) -> int:
    """Write the number to stdout and any warning to stderr.

    Returns:
        0.

    """
    sys.stdout.write(f"{number}\n")
    if warning is not None:
        sys.stderr.write(warning + "\n")
    return 0


def _lease(call: _Call) -> int:
    """Answer `lease`: the memory lease in MB, and the clamp warning when the cap cut it.

    Returns:
        0.

    """
    got = lease(read_rows(call.ledger), call.label, default_mb=call.default,
                ceiling_mb=call.ceiling)
    cap = autosize.cap_of(call.ceiling, call.default)
    return _answer(got.mb, autosize.clamp_warning(call.label, got, cap))


def _deadline(call: _Call) -> int:
    """Answer `deadline`: the wall hang guard in seconds, and the warning when the cap cut it.

    Returns:
        0.

    """
    got = deadline(read_rows(call.ledger), call.label,
                   Guard(default_s=call.default, ceiling_s=call.ceiling))
    return _answer(got.timeout_s, deadline_warning(call.label, got))


_MODES: dict[str, Callable[[_Call], int]] = {"lease": _lease, "deadline": _deadline}


def main(argv: list[str] | None = None) -> int:
    """`lease LEDGER LABEL DEFAULT_MB CEILING_MB` | `deadline LEDGER LABEL DEFAULT_S CEILING_S`.

    Returns:
        0 with the number on stdout (warning on stderr); 2 on a usage error.

    """
    args = sys.argv[1:] if argv is None else argv
    mode = _MODES.get(args[0]) if len(args) == _ARGS else None
    if mode is None:
        sys.stderr.write(_USAGE)
        return _USAGE_ERROR
    try:
        call = _Call(Path(args[1]), args[2], int(args[3]), int(args[4]))
    except ValueError:
        sys.stderr.write(_USAGE)
        return _USAGE_ERROR
    return mode(call)


if __name__ == "__main__":
    sys.exit(main())

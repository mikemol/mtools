# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A per-key run ledger — one TSV row per successful fenced run — and the report that sizes caps.

Ported by design from substrate's `scripts/membudget` (`_record_time`, `cmd_peaks`), per its ledger
letter of 2026-09-22. The ledger is a CONSUMER of `core.Result`: fence gains history without gaining
any actuation.

⚑⚑⚑ THE LETTER'S ONE DECISION, AND WHAT WAS DECIDED. `peak_mb` has always been maxRSS — the largest
single process's resident set, from `/usr/bin/time -v` — while fence measures `memory.peak`, the
whole cgroup's charge. Those are different quantities, and a column that silently changes producer
is the two-producers-for-one-name defect. So: ADD, DON'T REDEFINE. `peak_mb` stays maxRSS;
`cg_peak_mb` is appended as a seventh column (appended, so a reader splitting by position still
reads the first six unchanged); a reader names which one it sizes from.
⚑⚑ AND THE PROBE IS `os.wait4`, NOT THE LETTER'S `getrusage(RUSAGE_CHILDREN)` DELTA. `run_once`
already reaps its payload; `wait4` returns THAT child's own rusage — maxRSS, user, sys — with no
`/usr/bin/time` (absent on some hosts) and no arithmetic. A delta cannot be taken of a MAXIMUM: the
children's maxRSS only ever rises, so a before/after difference of it is not the payload's peak.

⚑ THE KEY IS THE CALLER'S. Per-label suits a gate that runs once; per-module suits per-core work
(all 3,598 ingest cores once shared one label and the report sized from two small ones). This
module takes the key as given and does not choose it.

CONSUMED BY: `mikemol.fence.cli`'s `peaks` mode (next), and substrate's `scripts/membudget` once
every fence letter has landed.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from mikemol.fence.core import Result

# The smallest cap the report suggests, and the lease uses: below it a bucket is not worth sizing.
BUCKET_FLOOR_MB = 64

# A row's fields, in order. The first six are the origin's; `cg_peak_mb` is appended.
FIELDS = ("label", "wall_s", "peak_mb", "stamp_epoch", "user_s", "sys_s", "cg_peak_mb")

# The fewest fields a row may carry and still be read: an older row predates the CPU probe.
_MIN_FIELDS = 4

# The index of `peak_mb`, the one column the origin's module ledger and this one agree on.
_PEAK_FIELD = FIELDS.index("peak_mb")

# The p90 index rule, as the origin computes it — pinned exactly rather than "a percentile".
_P90 = 0.9

_PERCENT = 100


def bucket(mb: float) -> int:
    """Return the power-of-two cap that holds `mb`, never below the floor.

    ⚑ ONE FUNCTION FOR THE REPORT AND THE LEASE, so the `suggested` column and the size a lease
    actually takes cannot disagree.

    Returns:
        the smallest power of two >= `mb`, and at least `BUCKET_FLOOR_MB`.

    """
    size = BUCKET_FLOOR_MB
    while size < mb:
        size *= 2
    return size


def _num(field: str) -> float | None:
    """Return a field as a number, or None when it is empty or not a number.

    ⚑ EMPTY IS NOT ZERO: a run whose probe gave nothing has no peak, and reading that as 0 would
    make it the smallest observation in the history.

    Returns:
        the value, or None.

    """
    try:
        return float(field) if field else None
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Row:
    """One successful run: its key, wall time, the two peaks, its stamp, and its CPU."""

    label: str
    wall_s: float
    peak_mb: float | None
    stamp_epoch: int
    user_s: float | None = None
    sys_s: float | None = None
    cg_peak_mb: float | None = None

    def line(self) -> str:
        """Render this row as its TSV line, an absent value as an EMPTY field.

        Returns:
            the line, without a newline.

        """
        cells = (
            self.label,
            _fmt(self.wall_s),
            _fmt(self.peak_mb),
            str(self.stamp_epoch),
            _fmt(self.user_s),
            _fmt(self.sys_s),
            _fmt(self.cg_peak_mb),
        )
        return "\t".join(cells)


def _fmt(value: float | None) -> str:
    """Render a number compactly, and None as the empty field.

    Returns:
        the field's text.

    """
    return "" if value is None else f"{value:g}"


def parse(text: str) -> list[Row]:
    """Read ledger rows; a malformed or truncated row is skipped and the rest survive.

    ⚑ THE LEDGER IS APPENDED CONCURRENTLY, so a partial last line is a real state, not corruption.

    Returns:
        the readable rows, in file order.

    """
    rows: list[Row] = []
    for raw in text.splitlines():
        cells = raw.split("\t")
        if len(cells) < _MIN_FIELDS:
            continue
        cells += [""] * (len(FIELDS) - len(cells))
        wall = _num(cells[1])
        stamp = _num(cells[3])
        if not cells[0] or wall is None or stamp is None:
            continue
        rows.append(
            Row(
                cells[0],
                wall,
                _num(cells[2]),
                int(stamp),
                _num(cells[4]),
                _num(cells[5]),
                _num(cells[6]),
            )
        )
    return rows


def key_peaks(text: str, key: str) -> list[float]:
    """Return the `peak_mb` column of every row keyed `key`, reading the origin's 3-field rows too.

    ⚑⚑ BASH'S MODULE LEDGER (`.agda-times.tsv`) WRITES `name, wall, peak` — THREE FIELDS, no stamp
    — which `parse` skips as truncated. Reading it through `parse` would size every module from NO
    history while its history sat in the file. Fence-written rows share the first three columns, so
    one reader serves both writers. ⚑ A ROW WITH NO PEAK IS SKIPPED, never read as 0.

    Returns:
        the peaks, in file order.

    """
    peaks: list[float] = []
    for raw in text.splitlines():
        cells = raw.split("\t")
        if len(cells) <= _PEAK_FIELD or cells[0] != key:
            continue
        peak = _num(cells[_PEAK_FIELD])
        if peak is not None:
            peaks.append(peak)
    return peaks


@dataclass(frozen=True, slots=True)
class Peaks:
    """The report for one label: enough observations to size a cap, not one."""

    label: str
    runs: int
    max_mb: float | None
    median_mb: float | None
    p90_mb: float | None
    max_s: float
    cpu_percent: float | None
    suggested_mb: int | None


def p90(values: Sequence[float]) -> float:
    """Return the origin's p90: sorted `a[max(1, int(0.9*m))]`, `a` 0-indexed, capped at the last.

    ⚑ PINNED, NOT "A PERCENTILE": over (40, 188, 90) it is 188, where interpolating methods differ.
    ⚑ THE INDEX IS 0-BASED, and the letter's own example is what settles it: read 1-based, the same
    rule gives 90. The cap matters only for one observation, where `max(1, 0)` would run off the
    end.

    Returns:
        the p90 observation.

    """
    ordered = sorted(values)
    return ordered[min(max(1, int(_P90 * len(ordered))), len(ordered) - 1)]


def report(rows: Iterable[Row], prefix: str = "") -> list[Peaks]:
    """Summarise every label starting with `prefix`, in label order.

    ⚑ A SINGLE OBSERVATION CANNOT SIZE A CAP: max alone is one bad run from over-sizing, median
    alone under-sizes the tail — so both are reported, with p90 between them.
    ⚑ cpu% IS OVER THE ROWS THAT CARRY CPU ONLY, and None when none do — never 0 for "unmeasured".

    Returns:
        one summary per matching label.

    """
    by_label: dict[str, list[Row]] = {}
    for row in rows:
        if row.label.startswith(prefix):
            by_label.setdefault(row.label, []).append(row)
    out: list[Peaks] = []
    for label in sorted(by_label):
        group = by_label[label]
        peaks = [row.peak_mb for row in group if row.peak_mb is not None]
        timed = [row for row in group if row.user_s is not None and row.sys_s is not None]
        wall = sum(row.wall_s for row in timed)
        cpu = sum((row.user_s or 0) + (row.sys_s or 0) for row in timed)
        top = max(peaks) if peaks else None
        out.append(
            Peaks(
                label=label,
                runs=len(group),
                max_mb=top,
                median_mb=statistics.median_low(peaks) if peaks else None,
                p90_mb=p90(peaks) if peaks else None,
                max_s=max(row.wall_s for row in group),
                cpu_percent=_PERCENT * cpu / wall if timed and wall > 0 else None,
                suggested_mb=bucket(top) if top is not None else None,
            )
        )
    return out


_KB_PER_MB = 1024
_BYTES_PER_MB = 1024 * 1024


def row_of(label: str, result: Result, stamp_epoch: int) -> Row | None:
    """Return the ledger row a run earns, or None when it earns none.

    ⚑ ONLY A CLEAN EXIT IS RECORDED: a killed run's peak is the CAP it hit, not the size it needed,
    and folding it into the history would size the next cap from the last one's limit.
    ⚑ WALL IS THE RUN'S OWN `duration_s`, measured by `run_once` after admission, so time spent
    waiting for a lease never reads as time spent working.
    ⚑⚑ PEAKS ARE WHOLE MEGABYTES, ROUNDED UP. Substrate's label reader accepts only integer peaks,
    so during the overlap a fractional one read there as NO HISTORY and the label fell back to its
    default (measured by the label-lease port study, 2026-09-22). Rounded UP, never down: a floored
    peak under-sizes the next lease by up to a megabyte, the one direction a cap must not err.

    Returns:
        the row, or None for a run that did not exit 0.

    """
    if result.exit_code != 0:
        return None
    return Row(
        label=label,
        wall_s=result.duration_s,
        peak_mb=None if result.maxrss_kb is None else _whole_mb(result.maxrss_kb, _KB_PER_MB),
        stamp_epoch=stamp_epoch,
        user_s=result.user_s,
        sys_s=result.sys_s,
        cg_peak_mb=(
            None
            if result.memory_peak_bytes is None
            else _whole_mb(result.memory_peak_bytes, _BYTES_PER_MB)
        ),
    )


def _whole_mb(amount: int, per_mb: int) -> float:
    """Return `amount` in whole megabytes, rounded UP.

    Returns:
        the ceiling of `amount / per_mb`, as a float the row carries.

    """
    return float(-(-amount // per_mb))


def record(path: Path, label: str, result: Result) -> bool:
    """Append the row `result` earns to the ledger at `path`, best-effort.

    ⚑ NEVER RAISES AND NEVER CHANGES THE PAYLOAD'S OUTCOME: the ledger is history about a run, and a
    run whose history could not be written still happened. An unwritable ledger returns False.

    Returns:
        whether a row was written.

    """
    row = row_of(label, result, int(time.time()))
    if row is None:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(row.line() + "\n")
    except OSError:
        return False
    return True

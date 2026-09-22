# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The run ledger's rows and the peaks report: empty is not zero, and one run cannot size a cap.

⚑ THE RECORD ARMS USE A CONSTRUCTED `Result`, so they need no cgroup. The one arm about the probe
itself — that a fenced run carries its own rusage from `wait4` — needs a real run, and skips with
the host's own reason where fencing is unavailable.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import pytest

from mikemol.fence import core, ledger
from mikemol.fence.cgroup import FenceUnavailableError, parent_with_controllers

if TYPE_CHECKING:
    from pathlib import Path


def _unfenceable() -> str:
    """Return why this host cannot fence, or the empty string when it can — as test_fence does.

    Returns:
        the reason, or "".

    """
    try:
        parent_with_controllers(["memory", "pids"])
    except FenceUnavailableError as e:
        return f"cannot fence here: {e}"
    return ""


_WHY = _unfenceable()
needs_cgroup = pytest.mark.skipif(bool(_WHY), reason=_WHY or "host can fence")

# The letter's three observations, for the pinned median and p90.
_THREE = (40.0, 188.0, 90.0)

# One observation, for the p90 index at the end of a one-element list.
_ONLY = 42.0

# user+sys equal to wall: a fully compute-bound run.
_ALL_CPU = 100

# The empty FIELD, named — `not x` would also accept None, which is the distinction under test.
_EMPTY = ""


def _row(label: str, peak: float | None, *, wall: float = 1.0, user: float | None = None,
         sys: float | None = None) -> ledger.Row:
    """Return a row with the fields an arm does not care about defaulted.

    Returns:
        the row.

    """
    return ledger.Row(label, wall, peak, 0, user, sys)


@pytest.mark.parametrize(("mb", "want"), [(65, 128), (128, 128), (129, 256), (200, 256),
                                          (257, 512), (3, 64)])
def test_the_bucket_is_the_next_power_of_two_above_a_floor(mb: int, want: int) -> None:
    """65→128, 128→128, 129→256, 200→256, 257→512, 3→64 — never below the peak, never under 64."""
    assert ledger.bucket(mb) == want


def test_a_row_round_trips_through_its_line() -> None:
    """Rendering then parsing yields the same row, with all seven fields."""
    row = ledger.Row("gate:a", 2.5, 100.0, 7, 1.0, 0.5, 120.0)
    assert ledger.parse(row.line()) == [row]


def test_an_absent_value_is_an_empty_field_not_zero() -> None:
    """A run with no probe writes empty peak and CPU fields, and reads them back as None.

    ⚑ THE CONTROL: a measured zero stays a zero.
    """
    line = ledger.Row("gate:a", 1.0, None, 7).line()
    assert line.split("\t")[2] == _EMPTY
    assert ledger.parse(line)[0].peak_mb is None
    assert ledger.parse(ledger.Row("gate:a", 1.0, 0.0, 7).line())[0].peak_mb == 0


def test_a_truncated_row_is_skipped_and_the_rest_survive() -> None:
    """A partial last line — a concurrent append — is skipped; the whole row before it is kept."""
    whole = ledger.Row("gate:a", 1.0, 10.0, 7).line()
    assert [row.label for row in ledger.parse(f"{whole}\ngate:b\t1")] == ["gate:a"]


def test_an_older_four_field_row_is_still_read() -> None:
    """A row from before the CPU probe (four fields) reads, with no CPU."""
    rows = ledger.parse("gate:a\t1.5\t10\t7")
    assert [(row.wall_s, row.user_s) for row in rows] == [(1.5, None)]


def test_the_report_selects_by_label_prefix() -> None:
    """`selftest:` includes `selftest:a` and excludes `gate:a`."""
    labels = [p.label for p in ledger.report([_row("selftest:a", 1), _row("gate:a", 1)],
                                             "selftest:")]
    assert labels == ["selftest:a"]


def test_median_and_p90_follow_the_origins_index_rule() -> None:
    """Over (40, 188, 90): median 90, p90 188 — the origin's rule, not an interpolated one."""
    [peaks] = ledger.report([_row("gate:a", mb) for mb in _THREE])
    assert (peaks.median_mb, peaks.p90_mb, peaks.max_mb) == (90, 188, 188)


def test_one_observation_has_a_p90() -> None:
    """A single run's p90 is that run — the index rule does not run off the end."""
    assert ledger.p90([_ONLY]) == _ONLY


def test_cpu_percent_is_unmeasured_when_no_row_carries_cpu() -> None:
    """Rows with no CPU give None, not 0. ⚑ THE CONTROL: rows that carry it give a number."""
    [bare] = ledger.report([_row("gate:a", 1)])
    [timed] = ledger.report([_row("gate:a", 1, wall=2.0, user=1.5, sys=0.5)])
    assert bare.cpu_percent is None
    assert timed.cpu_percent == _ALL_CPU


def test_the_suggested_size_is_the_leases_bucket_of_the_max() -> None:
    """`suggested` is exactly `bucket(max)` — one function, so column and lease cannot disagree."""
    [peaks] = ledger.report([_row("gate:a", mb) for mb in _THREE])
    assert peaks.suggested_mb == ledger.bucket(188)


def test_a_label_with_no_peak_suggests_nothing() -> None:
    """Only probe-less rows: no max and no suggestion, rather than a floor-sized guess."""
    [peaks] = ledger.report([_row("gate:a", None)])
    assert (peaks.runs, peaks.max_mb, peaks.suggested_mb) == (1, None, None)


# --- recording a run ---

_MB = 1024 * 1024


def _result(exit_code: int | None, *, maxrss_kb: int | None = 2048) -> core.Result:
    """Return a finished run's result without running anything.

    Returns:
        the result.

    """
    return core.Result(cmd=("payload",), caps=core.Caps(), duration_s=1.5, exit_code=exit_code,
                       memory_peak_bytes=3 * _MB, maxrss_kb=maxrss_kb, user_s=1.0, sys_s=0.25)


def test_a_clean_run_appends_exactly_one_seven_field_row(tmp_path: Path) -> None:
    """Exit 0 appends one row: maxRSS as peak_mb, the cgroup peak as cg_peak_mb, the run's wall."""
    path = tmp_path / "labels.tsv"
    assert ledger.record(path, "gate:a", _result(0))
    [row] = ledger.parse(path.read_text(encoding="utf-8"))
    assert (row.label, row.wall_s, row.peak_mb, row.cg_peak_mb) == ("gate:a", 1.5, 2, 3)
    assert len(path.read_text(encoding="utf-8").rstrip("\n").split("\t")) == len(ledger.FIELDS)


@pytest.mark.parametrize("exit_code", [1, 137, None])
def test_a_failed_or_killed_run_appends_nothing(tmp_path: Path, exit_code: int | None) -> None:
    """rc!=0 — a failure, an OOM kill (137), a run never reaped — writes no row.

    ⚑ THE CONTROL IS THE ARM ABOVE: the same call with exit 0 writes one.
    """
    path = tmp_path / "labels.tsv"
    assert not ledger.record(path, "gate:a", _result(exit_code))
    assert not path.exists()


def test_a_run_with_no_rusage_records_an_empty_peak(tmp_path: Path) -> None:
    """No probe value → an empty peak field, not 0."""
    path = tmp_path / "labels.tsv"
    ledger.record(path, "gate:a", _result(0, maxrss_kb=None))
    [row] = ledger.parse(path.read_text(encoding="utf-8"))
    assert row.peak_mb is None


def test_an_unwritable_ledger_is_not_an_error(tmp_path: Path) -> None:
    """A read-only ledger directory returns False and raises nothing — the run still happened.

    ⚑ THE CONTROL: the same record into a writable directory returns True.
    """
    locked = tmp_path / "ro"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        assert not ledger.record(locked / "labels.tsv", "gate:a", _result(0))
    finally:
        locked.chmod(0o700)
    assert ledger.record(tmp_path / "labels.tsv", "gate:a", _result(0))


@needs_cgroup
def test_a_fenced_run_carries_its_own_rusage() -> None:
    """A real fenced run reports its payload's maxRSS and CPU from `wait4`, not None."""
    result = core.run_once(["true"])
    assert result.maxrss_kb is not None
    assert result.maxrss_kb > 0
    assert result.user_s is not None


@needs_cgroup
def test_a_fence_name_taken_in_the_same_second_does_not_collide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cgroup already named `.mikemol-fence.<pid>.<second>` does not stop the next run.

    ⚑ THE GATE'S COLLISION, MADE DETERMINISTIC: two Bazel sandboxes each saw their test process as
    pid 12 and fenced in the same second. Here the second is pinned and that name pre-created.
    """
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.0)
    parent = parent_with_controllers(["memory", "pids"])
    squatter = parent / f".mikemol-fence.{os.getpid()}.1700000000"
    squatter.mkdir()
    try:
        assert core.run_once(["true"]).exit_code == 0
    finally:
        squatter.rmdir()

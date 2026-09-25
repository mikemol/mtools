# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Label leases: a memory lease and a wall hang guard, each sized from one label's history.

⚑ THE FIXTURES ARE TEMP LEDGERS OR ROWS, BY DESIGN (the origin's letter): an arm reading live
history would go red when a suite got cheaper, reporting an improvement as a defect. Every arm is
pure; none needs a cgroup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.fence import autosize, label_lease, ledger

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_LABEL = "agda:Mod"
_SIBLING = "agda:Other"
_STAMP = 1_758_000_000

# The origin's substrate-tuned numbers, used as fixtures only.
_DEFAULT_MB = 192
_CEILING_MB = 384
_DEFAULT_S = 600
_WALL = 1.0

# Memory fixtures and what they lease.
_PEAKS = (40.0, 188.0, 90.0)
_TOP_PEAK = 188.0
_WANT = 256
_UNROUNDED = (65.0, 128.0, 129.0, 200.0, 257.0)
_EXACT = 128
_TINY = 3.0
_FLOOR_MB = ledger.BUCKET_FLOOR_MB
_LIGHT = (16.0, 15.0, 17.0)
_LONE = 16.0
_HUGE = 900.0
_RAISED_DEFAULT_MB = 1024
_FRACTIONAL = 187.53

# Time fixtures and the guards they budget.
_WALLS = (30.0, 511.0, 200.0)
_WALL_GUARD = 1080
_QUICK = 5.0
_FLOOR_S = label_lease.FLOOR_S
_SLOW = 3000.0
_CEILING_S = label_lease.CEILING_S
_CPU_WALL = 100.0
_USER = 300.0
_SYS = 100.0
_CPU = 400.0
_CPU_GUARD = 1620
_LOW_CEILING_S = 300
_LOW_DEFAULT_S = 60
_OVER_LOW = 1000.0


def _row(
    label: str,
    *,
    wall: float = _WALL,
    peak: float | None = None,
    cpu: tuple[float | None, float | None] = (None, None),
) -> ledger.Row:
    """Return one ledger row for `label`.

    Returns:
        the row.

    """
    return ledger.Row(label, wall, peak, _STAMP, cpu[0], cpu[1])


def _peaked(label: str, peaks: tuple[float, ...]) -> list[ledger.Row]:
    """Return one row per peak, all for `label`.

    Returns:
        the rows.

    """
    return [_row(label, peak=peak) for peak in peaks]


def _lease(rows: list[ledger.Row], default_mb: int = _DEFAULT_MB) -> autosize.Sizing:
    """Return `_LABEL`'s lease over `rows` under the fixture ceiling.

    Returns:
        the sizing.

    """
    return label_lease.lease(rows, _LABEL, default_mb=default_mb, ceiling_mb=_CEILING_MB)


def _write(tmp_path: Path, lines: list[str]) -> Path:
    """Write `lines` as a ledger file.

    Returns:
        its path.

    """
    path = tmp_path / "labels.tsv"
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


# --- memory ---


def test_the_largest_peak_drives_the_lease() -> None:
    """(40, 188, 90) leases 256, and the reported peak is 188."""
    rows = _peaked(_LABEL, _PEAKS)
    assert _lease(rows) == autosize.Sizing(_WANT)
    assert max(label_lease.peaks_of(rows, _LABEL)) == _TOP_PEAK


def test_rounding_goes_up_to_a_power_of_two_never_below_the_peak() -> None:
    """Each of 65, 128, 129, 200, 257 leases a power of two at least the peak; 128 is exact."""
    for peak in _UNROUNDED:
        got = label_lease.lease(
            _peaked(_LABEL, (peak,)), _LABEL, default_mb=_DEFAULT_MB, ceiling_mb=_RAISED_DEFAULT_MB
        ).mb
        assert got >= peak
        assert got & (got - 1) == 0
    assert _lease(_peaked(_LABEL, (float(_EXACT),))).mb == _EXACT


def test_a_small_peak_takes_the_floor() -> None:
    """A 3 MB peak leases the 64 MB floor."""
    assert _lease(_peaked(_LABEL, (_TINY,))).mb == _FLOOR_MB


def test_a_light_label_sizes_below_the_default() -> None:
    """(16, 15, 17) leases under the default of 192 — the concurrency point."""
    assert _lease(_peaked(_LABEL, _LIGHT)).mb < _DEFAULT_MB


def test_an_unmeasured_label_takes_the_default() -> None:
    """A sibling's rows do not size an unmeasured label; the control: they size the sibling."""
    rows = _peaked(_SIBLING, _PEAKS)
    assert _lease(rows) == autosize.Sizing(_DEFAULT_MB)
    sibling = label_lease.lease(rows, _SIBLING, default_mb=_DEFAULT_MB, ceiling_mb=_CEILING_MB)
    assert sibling == autosize.Sizing(_WANT)


def test_a_missing_ledger_takes_the_default(tmp_path: Path) -> None:
    """A ledger that does not exist is no history, so the lease is the default."""
    rows = label_lease.read_rows(tmp_path / "absent.tsv")
    assert rows == []
    assert _lease(rows) == autosize.Sizing(_DEFAULT_MB)


def test_another_labels_rows_are_not_read() -> None:
    """A lone 16 beside a sibling's 900 leases the floor, not the sibling's size."""
    rows = [_row(_LABEL, peak=_LONE), _row(_SIBLING, peak=_HUGE)]
    assert _lease(rows) == autosize.Sizing(_FLOOR_MB)


def test_a_peak_above_the_ceiling_clamps() -> None:
    """A 900 peak under a 384 ceiling leases 384, clamped from 900."""
    assert _lease(_peaked(_LABEL, (_HUGE,))) == autosize.Sizing(_CEILING_MB, clamped_from=_HUGE)


def test_the_clamp_message_names_the_override_and_says_below() -> None:
    """A clamped lease's warning says BELOW and names `ceiling` (needs the autosize amendment)."""
    warning = autosize.clamp_warning(_LABEL, _lease(_peaked(_LABEL, (_HUGE,))), _CEILING_MB)
    assert warning is not None
    assert "ceiling" in warning
    assert "BELOW" in warning


def test_an_unclamped_sizing_says_nothing() -> None:
    """A lease under the cap owes no warning."""
    assert autosize.clamp_warning(_LABEL, _lease(_peaked(_LABEL, _PEAKS)), _CEILING_MB) is None


def test_an_explicit_default_raises_the_ceiling() -> None:
    """Default 1024 with a 900 peak leases at least 900, unclamped."""
    got = _lease(_peaked(_LABEL, (_HUGE,)), default_mb=_RAISED_DEFAULT_MB)
    assert got.mb >= _HUGE
    assert got.clamped_from is None


def test_malformed_rows_are_skipped(tmp_path: Path) -> None:
    """A truncated line and a non-numeric peak are skipped; the valid 188 leases 256."""
    lines = [_row(_LABEL, peak=_TOP_PEAK).line(), f"{_LABEL}\t1\tlots\t{_STAMP}", f"{_LABEL}\t1"]
    rows = label_lease.read_rows(_write(tmp_path, lines))
    assert label_lease.peaks_of(rows, _LABEL) == [_TOP_PEAK]
    assert _lease(rows) == autosize.Sizing(_WANT)


def test_a_fence_written_fractional_peak_is_read(tmp_path: Path) -> None:
    """A fence-written 187.53 peak leases 256 — the origin's integer reader saw no history."""
    rows = label_lease.read_rows(_write(tmp_path, [_row(_LABEL, peak=_FRACTIONAL).line()]))
    assert _lease(rows) == autosize.Sizing(_WANT)


# --- time ---


def _deadline(
    rows: list[ledger.Row], guard: label_lease.Guard | None = None
) -> label_lease.Deadline:
    """Return `_LABEL`'s deadline over `rows`, under the fixture default when no guard is given.

    Returns:
        the deadline.

    """
    return label_lease.deadline(rows, _LABEL, guard or label_lease.Guard(_DEFAULT_S))


def _walled(walls: tuple[float, ...]) -> list[ledger.Row]:
    """Return one untimed-CPU row per wall time, all for `_LABEL`.

    Returns:
        the rows.

    """
    return [_row(_LABEL, wall=wall) for wall in walls]


def test_the_slowest_run_drives_the_guard() -> None:
    """(30, 511, 200) budgets 1080 — 2 * 511 up to the minute — and owes no warning."""
    got = _deadline(_walled(_WALLS))
    assert got.timeout_s == _WALL_GUARD
    assert label_lease.deadline_warning(_LABEL, got) is None


def test_a_quick_label_takes_the_floor() -> None:
    """A 5 s run budgets the 120 s floor."""
    assert _deadline(_walled((_QUICK,))).timeout_s == _FLOOR_S


def test_an_untimed_label_takes_the_default() -> None:
    """No history budgets the default, unclamped, with no slowest run."""
    got = _deadline([])
    assert got.timeout_s == _DEFAULT_S
    assert got.slowest_s is None
    assert not got.clamped


def test_a_guard_above_the_ceiling_clamps_loudly() -> None:
    """A 3000 s run clamps to 3600, and the warning names the label and the risk."""
    got = _deadline(_walled((_SLOW,)))
    warning = label_lease.deadline_warning(_LABEL, got)
    assert got.timeout_s == _CEILING_S
    assert got.clamped
    assert warning is not None
    assert _LABEL in warning
    assert "may kill an honest run" in warning


def test_the_slowest_cpu_drives_the_guard_when_it_outranks_wall() -> None:
    """Wall 100 with CPU 300 + 100 budgets 1620 from 4 * 400, and reports cpu_s 400."""
    got = _deadline([_row(_LABEL, wall=_CPU_WALL, cpu=(_USER, _SYS))])
    assert got.timeout_s == _CPU_GUARD
    assert got.cpu_s == _CPU


def test_a_row_without_cpu_is_not_read_as_zero() -> None:
    """No CPU columns: cpu_s is None and the guard is the floor; the control carries CPU."""
    bare = _deadline([_row(_LABEL, wall=_QUICK)])
    assert bare.cpu_s is None
    assert bare.timeout_s == _FLOOR_S
    assert _deadline([_row(_LABEL, wall=_QUICK, cpu=(_USER, _SYS))]).cpu_s is not None


def test_the_clamp_message_reports_the_effective_cap() -> None:
    """Under ceiling_s=300 a 1000 s run's warning names 300, not the module's 3600."""
    guard = label_lease.Guard(_LOW_DEFAULT_S, ceiling_s=_LOW_CEILING_S)
    warning = label_lease.deadline_warning(_LABEL, _deadline(_walled((_OVER_LOW,)), guard))
    assert warning is not None
    assert f"{_LOW_CEILING_S}s" in warning
    assert str(_CEILING_S) not in warning


def test_one_half_of_cpu_is_no_cpu() -> None:
    """A row with user but no sys (or sys but no user) counts as no CPU, not half of it."""
    assert label_lease.cpu_of(_row(_LABEL, cpu=(_USER, None))) is None
    assert label_lease.cpu_of(_row(_LABEL, cpu=(None, _SYS))) is None
    assert label_lease.cpu_of(_row(_LABEL, cpu=(_USER, _SYS))) == _CPU


# --- the CLI ---


def test_the_cli_prints_the_number_and_warns_only_when_clamped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`lease` prints the MB on stdout; stderr is empty unclamped, and warns when clamped."""
    path = _write(
        tmp_path, [_row(_LABEL, peak=_TOP_PEAK).line(), _row(_SIBLING, peak=_HUGE).line()]
    )
    assert label_lease.main(["lease", str(path), _LABEL, str(_DEFAULT_MB), str(_CEILING_MB)]) == 0
    calm = capsys.readouterr()
    assert calm.out == f"{_WANT}\n"
    assert not calm.err
    assert label_lease.main(["lease", str(path), _SIBLING, str(_DEFAULT_MB), str(_CEILING_MB)]) == 0
    loud = capsys.readouterr()
    assert loud.out == f"{_CEILING_MB}\n"
    assert _SIBLING in loud.err


def test_the_cli_deadline_mode_prints_seconds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`deadline` prints the guard in seconds on stdout, with nothing on stderr."""
    path = _write(tmp_path, [row.line() for row in _walled(_WALLS)])
    assert label_lease.main(["deadline", str(path), _LABEL, str(_DEFAULT_S), str(_CEILING_S)]) == 0
    got = capsys.readouterr()
    assert got.out == f"{_WALL_GUARD}\n"
    assert not got.err


def test_the_cli_refuses_a_bad_invocation(capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown mode, a short argv and a non-integer size each exit 2 with usage on stderr."""
    usage_error = 2
    for argv in (["size", "l", _LABEL, "1", "2"], ["lease"], ["lease", "l", _LABEL, "x", "2"]):
        assert label_lease.main(argv) == usage_error
        assert "usage" in capsys.readouterr().err

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `buildpulse`: progress, windowed rate, and each terminal state named."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import buildpulse
from mikemol.buildtel.buildpulse import Sample

if TYPE_CHECKING:
    from collections.abc import Sequence

_T0 = 1_000_000.0
_MINUTE = 60.0
_PER_MINUTE = 10
_SPAN_MINUTES = 10
_DONE_BEFORE = 42
_TOTAL = 1000
_SELFTEST_CASES = 15
_TAIL_BYTES = 40
_FIRST_LOG_LINE = "[1,234 / 5,678] first\n"
_EXIT_NO_LOG = 2
_SAMPLES_AFTER = 2


def _write_log(tmp_path: Path, text: str) -> Path:
    """Plant a build log.

    Returns:
        the log's path.

    """
    log = tmp_path / "hook.output"
    log.write_text(text, encoding="utf-8")
    return log


def _run(
    log: Path,
    *,
    alive: bool,
    clock: float,
    extra: Sequence[str] = (),
) -> int:
    """Run `buildpulse.main` over `log` with a fixed liveness and clock.

    Returns:
        main's exit status.

    """
    return buildpulse.main(["--log", str(log), *extra], is_alive=lambda: alive, clock=lambda: clock)


def test_read_progress_takes_the_last_counter_and_strips_the_commas(tmp_path: Path) -> None:
    """The newest `[done / total]` wins, and `1,234` reads as 1234."""
    log = _write_log(tmp_path, f"{_FIRST_LOG_LINE}[39,547 / 116,688] later\nplain line\n")
    assert buildpulse.read_progress(log) == (39547, 116688)


def test_read_progress_is_zero_without_a_counter(tmp_path: Path) -> None:
    """A log with no counter is `(0, 0)`, not an error."""
    assert buildpulse.read_progress(_write_log(tmp_path, "nothing here\n")) == (0, 0)


def test_read_progress_looks_only_at_the_tail(tmp_path: Path) -> None:
    """A counter older than the tail window is not read: only the end of the file is."""
    log = _write_log(tmp_path, _FIRST_LOG_LINE + "x" * (_TAIL_BYTES * 3))
    assert buildpulse.read_progress(log, tail_bytes=_TAIL_BYTES) == (0, 0)
    assert buildpulse.read_progress(log) == (1234, 5678)


@pytest.mark.parametrize(
    "line",
    [
        "FAIL: @@x//:y (Exit 1)",
        "FAILED: thing",
        "ERROR: Build did NOT complete successfully",
        "java.lang.OutOfMemoryError: Java heap space",
        "Traceback (most recent call last):",
        "err: input dependency modified during execution",
    ],
)
def test_read_trouble_names_each_failure_signature(tmp_path: Path, line: str) -> None:
    """Every signature in the vocabulary is returned, and the clean lines before it are not."""
    log = _write_log(tmp_path, f"[1 / 2] fine\n{line}\n")
    assert buildpulse.read_trouble(log) == line


def test_read_trouble_is_empty_for_a_clean_tail_and_clips_a_long_line(tmp_path: Path) -> None:
    """No signature gives `""`; the newest matching line is clipped to 160 characters."""
    assert not buildpulse.read_trouble(_write_log(tmp_path, "[1 / 2] fine\n"))
    long = "ERROR: " + "x" * 300
    log = _write_log(tmp_path, f"ERROR: older\n{long}\nclean\n")
    assert buildpulse.read_trouble(log) == long[: buildpulse.TROUBLE_MAX]


def test_read_trouble_ignores_a_signature_beyond_the_tail(tmp_path: Path) -> None:
    """A failure older than the tail window is out of sight."""
    log = _write_log(tmp_path, "ERROR: old\n" + "fine\n" * _TAIL_BYTES)
    assert not buildpulse.read_trouble(log, tail_bytes=_TAIL_BYTES)


def test_build_alive_asks_pgrep_for_the_executable_by_exact_name() -> None:
    """The probe is `pgrep -x bazel` (never `-f`, which would match the watcher itself)."""
    asked: list[Sequence[str]] = []

    def run(argv: Sequence[str]) -> tuple[int, str, str]:
        asked.append(list(argv))
        return 0, "", ""

    assert buildpulse.build_alive(run) is True
    assert asked == [["pgrep", "-x", "bazel"]]


def test_build_alive_is_false_when_pgrep_finds_nothing() -> None:
    """Exit 1 from pgrep is a build that is gone."""
    assert buildpulse.build_alive(lambda _argv: (1, "", "")) is False


def test_samples_round_trip_through_the_state_file(tmp_path: Path) -> None:
    """What `append` writes, `load` reads back, in order."""
    state = tmp_path / "s.pulse"
    samples = [Sample(at=_T0, done=1, total=2), Sample(at=_T0 + 1, done=3, total=4)]
    for s in samples:
        buildpulse.append(state, s)
    assert buildpulse.load(state) == samples


def test_load_skips_every_line_that_is_not_a_sample(tmp_path: Path) -> None:
    """Blank lines, broken JSON, non-objects, ints and missing keys are skipped, not fatal."""
    state = tmp_path / "s.pulse"
    fields: dict[str, float] = {"at": _T0, "done": 5.0, "total": 9.0}
    good = json.dumps(fields)
    state.write_text(
        f'\n   \n{{not json\n[1]\n{{"at": 1, "done": 2, "total": 3}}\n{{"at": 1.0}}\n{good}\n',
        encoding="utf-8",
    )
    assert buildpulse.load(state) == [Sample(at=_T0, done=5, total=9)]


def test_load_of_a_missing_state_is_empty(tmp_path: Path) -> None:
    """No state file is no history."""
    assert buildpulse.load(tmp_path / "none.pulse") == []


def test_rate_is_actions_per_minute_against_the_oldest_sample_in_the_window() -> None:
    """100 actions over 10 minutes is 10/min over a 10-minute span."""
    past = [Sample(at=_T0, done=_DONE_BEFORE, total=_TOTAL)]
    now = Sample(at=_T0 + _SPAN_MINUTES * _MINUTE, done=_DONE_BEFORE + 100, total=_TOTAL)
    per_min, span = buildpulse.rate(now, past, buildpulse.DEFAULT_WINDOW)
    assert per_min == pytest.approx(_PER_MINUTE)
    assert span == pytest.approx(_SPAN_MINUTES)


def test_rate_ignores_samples_older_than_the_window_and_uses_the_oldest_inside() -> None:
    """A sample outside the window is no reference; the first one inside it is."""
    now = Sample(at=_T0 + 1000, done=200, total=_TOTAL)
    outside = Sample(at=_T0, done=0, total=_TOTAL)
    inside = Sample(at=_T0 + 400, done=100, total=_TOTAL)
    newer = Sample(at=_T0 + 700, done=150, total=_TOTAL)
    window = 700.0
    assert buildpulse.rate(now, [outside], window) == (0.0, 0.0)
    per_min, span = buildpulse.rate(now, [outside, inside, newer], window)
    assert per_min == pytest.approx(100 / (600 / _MINUTE))
    assert span == pytest.approx(10.0)


def test_rate_is_withheld_with_no_earlier_sample_or_a_sample_from_the_future() -> None:
    """No history, or a reference not before now, is `(0, 0)`: not yet known, never a false zero."""
    now = Sample(at=_T0, done=5, total=_TOTAL)
    assert buildpulse.rate(now, [], buildpulse.DEFAULT_WINDOW) == (0.0, 0.0)
    same_instant = [Sample(at=_T0, done=1, total=_TOTAL)]
    assert buildpulse.rate(now, same_instant, buildpulse.DEFAULT_WINDOW) == (0.0, 0.0)


def test_stalled_reports_minutes_frozen_once_past_the_threshold() -> None:
    """A counter unmoved for 40 minutes, with a 30-minute threshold, is 40 minutes frozen."""
    now = Sample(at=_T0 + 40 * _MINUTE, done=_DONE_BEFORE, total=_TOTAL)
    past = [Sample(at=_T0, done=_DONE_BEFORE, total=_TOTAL)]
    assert buildpulse.stalled(now, past, buildpulse.DEFAULT_STALL) == pytest.approx(40.0)


def test_stalled_is_zero_below_the_threshold_and_with_no_history() -> None:
    """Ten frozen minutes is not yet a stall at 30; nothing to compare is not a stall."""
    now = Sample(at=_T0 + 10 * _MINUTE, done=_DONE_BEFORE, total=_TOTAL)
    past = [Sample(at=_T0, done=_DONE_BEFORE, total=_TOTAL)]
    assert not buildpulse.stalled(now, past, buildpulse.DEFAULT_STALL)
    assert not buildpulse.stalled(now, [], buildpulse.DEFAULT_STALL)


def test_stalled_is_cleared_by_one_action_and_counts_from_the_last_move() -> None:
    """One action of progress clears it; a freeze is measured from after the counter last moved."""
    day = float(buildpulse.DAY_S)
    frozen = [Sample(at=_T0, done=_DONE_BEFORE, total=_TOTAL)]
    now = Sample(at=_T0 + day, done=_DONE_BEFORE, total=_TOTAL)
    assert buildpulse.stalled(now, frozen, buildpulse.DEFAULT_STALL) == pytest.approx(day / _MINUTE)
    moved = Sample(at=_T0 + day, done=_DONE_BEFORE + 1, total=_TOTAL)
    assert not buildpulse.stalled(moved, frozen, buildpulse.DEFAULT_STALL)
    detour = [*frozen, Sample(at=_T0 + day - 40 * _MINUTE, done=_DONE_BEFORE - 1, total=_TOTAL)]
    assert not buildpulse.stalled(now, detour, buildpulse.DEFAULT_STALL)


def test_eta_is_minutes_hours_or_nothing() -> None:
    """Under an hour renders minutes, over an hour hours; no rate or no work remaining is blank."""
    now = Sample(at=_T0, done=100, total=1000)
    assert buildpulse.eta(now, 100.0) == " · ~9m left at this rate (linear est.)"
    assert buildpulse.eta(now, _PER_MINUTE) == " · ~1.5h left at this rate (linear est.)"
    assert not buildpulse.eta(now, 0.0)
    assert not buildpulse.eta(Sample(at=_T0, done=1000, total=1000), 5.0)


def test_parse_args_defaults_the_state_beside_the_log() -> None:
    """With no flags: no log, the default window and stall threshold, no selftest."""
    assert buildpulse.parse_args([]) == (
        Path(),
        Path(".pulse"),
        buildpulse.DEFAULT_WINDOW,
        buildpulse.DEFAULT_STALL,
        False,
    )
    log, state, _window, _stall, _selftest = buildpulse.parse_args(["--log", "a/b.out"])
    assert (log, state) == (Path("a/b.out"), Path("a/b.out.pulse"))


def test_parse_args_reads_every_flag() -> None:
    """`--state`, `--window`, `--stall-after` and `--selftest` are each honoured."""
    got = buildpulse.parse_args(
        ["--log", "l", "--state", "s", "--window", "5", "--stall-after", "7", "--selftest"]
    )
    assert got == (Path("l"), Path("s"), 5.0, 7.0, True)


def test_parse_args_refuses_an_unknown_flag() -> None:
    """An unknown flag is argparse's usage error (exit 2), not a silent default."""
    with pytest.raises(SystemExit) as caught:
        buildpulse.parse_args(["--bogus"])
    assert caught.value.code == _EXIT_NO_LOG


def test_selftest_passes_every_case_and_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    """Every arm fires on its synthetic input: exit 0, no `XX`, a full tally."""
    assert buildpulse.selftest() == 0
    out = capsys.readouterr().out
    assert "XX" not in out
    assert out.endswith(f"buildpulse selftest: {_SELFTEST_CASES}/{_SELFTEST_CASES}\n")


def test_selftest_fails_loudly_when_an_arm_cannot_fire(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With the stall predicate disabled, the selftest names the case it can no longer see."""

    def never_stalled(_now: Sample, _past: list[Sample], _after: float) -> float:
        return 0.0

    monkeypatch.setattr(buildpulse, "stalled", never_stalled)
    assert buildpulse.selftest() == 1
    out = capsys.readouterr().out
    assert "  XX F - a frozen counter is reported as a stall\n" in out
    assert out.endswith(f"buildpulse selftest: {_SELFTEST_CASES - 2}/{_SELFTEST_CASES}\n")


def test_main_runs_the_selftest_on_request(capsys: pytest.CaptureFixture[str]) -> None:
    """`--selftest` is the selftest, with no log needed."""
    assert buildpulse.main(["--selftest"]) == 0
    assert "buildpulse selftest:" in capsys.readouterr().out


def test_main_without_a_log_says_so_with_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing log, or no `--log` at all, is exit 2 naming where it looked."""
    missing = tmp_path / "nope.output"
    assert _run(missing, alive=True, clock=_T0) == _EXIT_NO_LOG
    assert capsys.readouterr().out == f"pulse: no log at {missing}\n"
    assert buildpulse.main([]) == _EXIT_NO_LOG


def test_main_first_sample_reports_progress_and_records_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first call prints counter and percentage, says the rate is unknown, writes state."""
    log = _write_log(tmp_path, "[42,387 / 120,269] eval\n")
    assert _run(log, alive=True, clock=_T0) == 0
    assert capsys.readouterr().out == "pulse: 42,387/120,269 (35.2%) · rate: first sample\n"
    assert buildpulse.load(Path(str(log) + ".pulse")) == [Sample(at=_T0, done=42387, total=120269)]


def test_main_reports_the_windowed_rate_and_an_eta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Against a sample 10 minutes old, 100 more actions reads as 10/min, with a linear ETA."""
    log = _write_log(tmp_path, "[142 / 1,000] eval\n")
    state = tmp_path / "custom.pulse"
    buildpulse.append(state, Sample(at=_T0, done=_DONE_BEFORE, total=_TOTAL))
    clock = _T0 + _SPAN_MINUTES * _MINUTE
    assert _run(log, alive=True, clock=clock, extra=["--state", str(state)]) == 0
    assert capsys.readouterr().out == (
        "pulse: 142/1,000 (14.2%) · 10 actions/min over 10m"
        " · ~1.4h left at this rate (linear est.)\n"
    )
    assert len(buildpulse.load(state)) == _SAMPLES_AFTER


def test_main_names_a_failure_signature_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failure line in the tail is reported first, even while the build is alive."""
    log = _write_log(tmp_path, "[1 / 2] fine\nERROR: Build did NOT complete successfully\n")
    assert _run(log, alive=True, clock=_T0) == 1
    assert "  ⚑ FAILURE SIGNATURE in the log tail: ERROR: Build did NOT complete" in (
        capsys.readouterr().out
    )


def test_main_names_a_gone_build_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A clean tail with no build process left is `GONE`, never a silent success."""
    log = _write_log(tmp_path, "[1 / 2] fine\n")
    assert _run(log, alive=False, clock=_T0) == 1
    assert "the //:hook build process is GONE" in capsys.readouterr().out


def test_main_names_a_stall_and_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An alive build whose counter has not moved for the threshold is a `STALL`, in minutes."""
    log = _write_log(tmp_path, "[42 / 100] eval\n")
    state = Path(str(log) + ".pulse")
    buildpulse.append(state, Sample(at=_T0, done=_DONE_BEFORE, total=100))
    assert _run(log, alive=True, clock=_T0 + 40 * _MINUTE) == 1
    assert "  ⚑ STALL: the action counter has not moved in 40m (still 42)." in (
        capsys.readouterr().out
    )


def test_main_exits_0_for_an_alive_moving_build(tmp_path: Path) -> None:
    """A counter that moved since the last sample, alive, with a clean tail, is exit 0."""
    log = _write_log(tmp_path, "[43 / 100] eval\n")
    buildpulse.append(Path(str(log) + ".pulse"), Sample(at=_T0, done=_DONE_BEFORE, total=100))
    assert _run(log, alive=True, clock=_T0 + 40 * _MINUTE) == 0

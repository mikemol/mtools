# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the zram admission gate (W837): a start waits while zram is too full."""

from __future__ import annotations

from pathlib import Path

import pytest

from mikemol.fence import admit, membudget_cli

_TOTAL = 512
_CEILING = 0.85
_HALF = 0.5
_FULL = 0.95
_TIMEOUT_S = 30.0
_POLL_S = 10.0


def _store(tmp_path: Path) -> admit.Store:
    """Return a ledger under `tmp_path` declaring a total.

    Returns:
        the store.

    """
    store = admit.Store(tmp_path / "ledger")
    admit.init(store, _TOTAL)
    return store


class _Run:
    """One acquire on virtual time: the clock moves only when the loop sleeps."""

    def __init__(self, readings: list[float | None]) -> None:
        self.now = 0.0
        self.said: list[str] = []
        self.slept: list[float] = []
        self.reads = 0
        self._readings = readings

    def read(self, stat: Path) -> float | None:
        """Answer the next reading, repeating the last, and count the call.

        Returns:
            the fraction, or None for an unreadable device.

        """
        del stat
        self.reads += 1
        return self._readings.pop(0) if len(self._readings) > 1 else self._readings[0]

    def sleep(self, seconds: float) -> None:
        """Advance virtual time by `seconds`."""
        self.slept.append(seconds)
        self.now += seconds

    def host(self) -> admit.Host:
        """Build the injected host: no load, virtual time, this reader, this announcer.

        Returns:
            the host.

        """
        return admit.Host(
            loadavg=lambda: (0.0, 0.0, 0.0),
            clock=lambda: self.now,
            sleep=self.sleep,
            announce=self.said.append,
            read_zram=self.read,
        )


def _write_stat(path: Path, text: str) -> Path:
    """Write an mm_stat stand-in.

    Returns:
        its path.

    """
    path.write_text(text, encoding="utf-8")
    return path


def test_the_fraction_is_used_over_limit_taken_from_the_right_fields(tmp_path: Path) -> None:
    """Fields 3 and 4 (used, limit) decide it: distinct numbers show no other pair would do."""
    stat = _write_stat(tmp_path / "mm_stat", "7 11 300 1000 9 9 9\n")
    assert admit.zram_fraction(stat) == pytest.approx(0.3)


def test_a_reading_that_cannot_be_trusted_is_none_never_a_fraction(tmp_path: Path) -> None:
    """Missing, short, non-numeric, and a zero or negative limit each read as no reading."""
    assert admit.zram_fraction(tmp_path / "absent") is None
    assert admit.zram_fraction(_write_stat(tmp_path / "short", "1 2 3\n")) is None
    assert admit.zram_fraction(_write_stat(tmp_path / "words", "1 2 x 4\n")) is None
    assert admit.zram_fraction(_write_stat(tmp_path / "nolimit", "1 2 300 0\n")) is None
    assert admit.zram_fraction(_write_stat(tmp_path / "neg", "1 2 300 -5\n")) is None


def test_zram_admits_strictly_below_the_ceiling_and_a_disabled_gate_admits_all() -> None:
    """At the ceiling is refused; below passes; None or non-positive ceiling or reading admits."""
    assert admit.zram_fits(_HALF, _CEILING)
    assert not admit.zram_fits(_CEILING, _CEILING)
    assert not admit.zram_fits(_FULL, _CEILING)
    assert admit.zram_fits(_FULL, None)
    assert admit.zram_fits(_FULL, 0.0)
    assert admit.zram_fits(_FULL, -1.0)
    assert admit.zram_fits(None, _CEILING)


def test_with_the_gate_off_zram_is_never_read(tmp_path: Path) -> None:
    """A caller that never set the ceiling never touches /sys: the reader is not called."""
    run = _Run([_FULL])
    with admit.admit(_store(tmp_path), admit.Request(1), host=run.host()):
        pass
    assert run.reads == 0


def test_with_headroom_a_start_is_admitted_at_once_without_sleeping(tmp_path: Path) -> None:
    """Below the ceiling nothing waits and nothing is said."""
    run = _Run([_HALF])
    waiting = admit.Waiting(zram_max=_CEILING)
    with admit.admit(_store(tmp_path), admit.Request(1), waiting, host=run.host()):
        pass
    assert not run.slept
    assert not run.said


def test_a_full_zram_makes_a_start_wait_until_it_drains_and_says_why_once(tmp_path: Path) -> None:
    """The start sleeps while zram is at 95%, is admitted on the first reading below 85%."""
    run = _Run([_FULL, _FULL, _HALF])
    waiting = admit.Waiting(zram_max=_CEILING, poll_start_s=_POLL_S, poll_max_s=_POLL_S)
    with admit.admit(_store(tmp_path), admit.Request(1), waiting, host=run.host()):
        pass
    assert run.slept == [_POLL_S, _POLL_S]
    assert len(run.said) == 1
    assert "ZRAM" in run.said[0]
    assert "zram 95%" in run.said[0]
    assert "admits below 85%" in run.said[0]


def test_a_zram_that_stays_full_refuses_after_the_timeout_and_never_takes_a_place_in_line(
    tmp_path: Path,
) -> None:
    """Exit 3 once the wait is spent, and the ledger shows no waiter while it waited."""
    store = _store(tmp_path)
    run = _Run([_FULL])
    waiting = admit.Waiting(
        zram_max=_CEILING, timeout_s=_TIMEOUT_S, poll_start_s=_POLL_S, poll_max_s=_POLL_S
    )
    waiters_seen: list[int] = []

    def watching(seconds: float) -> None:
        waiters_seen.append(len(store.read().waiters))
        run.sleep(seconds)

    host = admit.Host(
        loadavg=lambda: (0.0, 0.0, 0.0),
        clock=lambda: run.now,
        sleep=watching,
        announce=run.said.append,
        read_zram=run.read,
    )
    with pytest.raises(admit.RefusedError) as err:
        admit.acquire(store, admit.Request(1), waiting, host=host)
    assert err.value.code == admit.EXIT_REFUSED
    assert "gave up" in str(err.value)
    assert _TIMEOUT_S <= run.now <= _TIMEOUT_S + _POLL_S
    assert waiters_seen
    assert set(waiters_seen) == {0}


def test_an_unreadable_zram_admits_even_with_the_gate_on(tmp_path: Path) -> None:
    """What cannot be read blocks nothing: the reader answers None and the start proceeds."""
    run = _Run([None])
    waiting = admit.Waiting(zram_max=_CEILING)
    with admit.admit(_store(tmp_path), admit.Request(1), waiting, host=run.host()):
        pass
    assert run.reads == 1
    assert not run.slept


def test_the_environment_sets_the_ceiling_and_the_stat_file() -> None:
    """MEMBUDGET_ZRAM_MAX and MEMBUDGET_ZRAM_STAT reach the waiting policy; unset is off."""
    waiting = membudget_cli.waiting_of(
        {membudget_cli.ENV_ZRAM_MAX: "0.85", membudget_cli.ENV_ZRAM_STAT: "/x/mm_stat"}
    )
    assert waiting.zram_max == pytest.approx(_CEILING)
    assert waiting.zram_stat == Path("/x/mm_stat")
    unset = membudget_cli.waiting_of({})
    assert unset.zram_max is None
    assert unset.zram_stat == admit.ZRAM_STAT
    assert membudget_cli.waiting_of({membudget_cli.ENV_ZRAM_MAX: "0"}).zram_max is None


def test_the_capabilities_verb_names_the_zram_gate_so_a_caller_can_ask_before_relying(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An older membudget has no such verb: asking is how 'too old' is told from 'supported'."""
    assert membudget_cli.main(["capabilities"]) == 0
    assert capsys.readouterr().out.split() == ["zram-gate"]


def test_a_ceiling_that_is_not_a_number_is_a_usage_error() -> None:
    """A typo in the ceiling is refused by name, never read as off."""
    with pytest.raises(membudget_cli.UsageError, match="MEMBUDGET_ZRAM_MAX"):
        membudget_cli.waiting_of({membudget_cli.ENV_ZRAM_MAX: "lots"})

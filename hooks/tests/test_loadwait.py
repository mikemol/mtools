# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the commit's load wait, with an injected load reader and sleeper (no clock).

W982. ⚑ THE WAIT THAT ENDS WHEN THE LOAD FALLS IS THE POSITIVE CONTROL for the unset, the already
low and the gave-up cases: each is the same loop with a different reading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import loadwait

if TYPE_CHECKING:
    from collections.abc import Iterator

LIMIT = "40"
_HIGH = 120.0
_LOW = 10.0


class _Host:
    """A host whose load follows a script, and a sleeper that records how long it was asked."""

    def __init__(self, readings: list[float]) -> None:
        self._readings: Iterator[float] = iter(readings)
        self._last = readings[-1]
        self.slept: list[float] = []

    def read(self) -> float:
        self._last = next(self._readings, self._last)
        return self._last

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


def test_a_commit_waits_until_the_load_falls_and_says_how_long() -> None:
    """The control: two high readings then a low one is two polls and a line saying so."""
    host = _Host([_HIGH, _HIGH, _LOW])
    line = loadwait.wait_for_load({loadwait.LOAD_ENV: LIMIT}, host.read, host.sleep)
    assert host.slept == [loadwait.POLL_S, loadwait.POLL_S]
    assert line is not None
    assert "waited 40s" in line
    assert "load fell" in line


def test_nothing_is_asked_so_nothing_waits() -> None:
    """Unset or zero is off: no reading is even taken."""
    host = _Host([_HIGH])
    assert loadwait.wait_for_load({}, host.read, host.sleep) is None
    assert loadwait.wait_for_load({loadwait.LOAD_ENV: "0"}, host.read, host.sleep) is None
    assert loadwait.wait_for_load({loadwait.LOAD_ENV: "soon"}, host.read, host.sleep) is None
    assert host.slept == []


def test_a_load_already_under_the_limit_does_not_wait() -> None:
    """A quiet host is not delayed and prints nothing."""
    host = _Host([_LOW])
    assert loadwait.wait_for_load({loadwait.LOAD_ENV: LIMIT}, host.read, host.sleep) is None
    assert host.slept == []


def test_the_wait_is_bounded_and_the_commit_goes_ahead_saying_so() -> None:
    """A load that never falls costs the bound and no more; the line says it went ahead."""
    host = _Host([_HIGH])
    env = {loadwait.LOAD_ENV: LIMIT, loadwait.WAIT_ENV: "60"}
    line = loadwait.wait_for_load(env, host.read, host.sleep)
    assert len(host.slept) == 60 // loadwait.POLL_S
    assert line is not None
    assert "going ahead anyway" in line

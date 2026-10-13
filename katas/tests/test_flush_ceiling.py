# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `fleet.ceiling`: a flush commit's limit comes from its own repo's measured gate.

W1106. ⚑ THE UNMEASURED REPO IS THE POSITIVE CONTROL: the same function, a repo with no passing
flush yet, returns the bounded default, so the measured ones are scaled by their own reading and not
by a constant. No git runs here; the measure is the `.seconds` file a waiter leaves beside a log.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.katas import detach, fleet, waiter

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

_MEASURED = "400.0\n"


def _host(tmp_path: Path) -> fleet.Fleet:
    return fleet.Fleet(tmp_path / "hosts", tmp_path / "logs")


def _measure(host: fleet.Fleet, repo: str, text: str) -> None:
    path = waiter.seconds_of(fleet.log_of(host, repo))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _is(value: float, expected: float) -> bool:
    return math.isclose(value, expected)


def test_an_unmeasured_repo_gets_the_bounded_default(tmp_path: Path) -> None:
    """No `.seconds` file: the default, which is below the cap."""
    assert _is(fleet.ceiling(_host(tmp_path), "new"), fleet.UNMEASURED_S)
    assert fleet.UNMEASURED_S < fleet.CEILING_CAP_S


def test_a_measured_repo_gets_its_seconds_times_the_stretch(tmp_path: Path) -> None:
    """A 400 s gate is allowed 400 times the stretch, between the floor and the cap."""
    host = _host(tmp_path)
    _measure(host, "mid", _MEASURED)
    assert _is(fleet.ceiling(host, "mid"), 400.0 * fleet.STRETCH)


def test_a_fast_gate_is_held_to_the_floor_and_a_slow_one_to_the_cap(tmp_path: Path) -> None:
    """Two seconds is lifted to the floor; a day is cut to the cap."""
    host = _host(tmp_path)
    _measure(host, "fast", "2.0\n")
    _measure(host, "slow", "86400.0\n")
    assert _is(fleet.ceiling(host, "fast"), fleet.CEILING_FLOOR_S)
    assert _is(fleet.ceiling(host, "slow"), fleet.CEILING_CAP_S)


def test_a_garbled_measure_reads_as_unmeasured(tmp_path: Path) -> None:
    """Text that is not a number is no measure, and never raises."""
    host = _host(tmp_path)
    _measure(host, "odd", "soon\n")
    assert _is(fleet.ceiling(host, "odd"), fleet.UNMEASURED_S)


def test_the_waiter_argv_carries_the_limit_before_the_removals() -> None:
    """A limit becomes a `--timeout` pair right after the log; none leaves the argv unchanged."""
    cmd = ["c"]
    bare = detach.waiter_argv(Path("l.log"), cmd, [Path("x")])
    limited = detach.waiter_argv(Path("l.log"), cmd, [Path("x")], 90.0)
    at = limited.index("l.log")
    assert limited[at + 1 : at + 3] == ["--timeout", "90"]
    assert "--timeout" not in bare


def test_flush_starts_each_commit_under_its_repos_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The detached start is handed the repo's derived ceiling, not left to the default limit."""
    host = _host(tmp_path)
    _measure(host, "mid", _MEASURED)
    seen: list[float | None] = []

    def only_mid(_fleet: fleet.Fleet, _skip: Sequence[str] = ()) -> list[str]:
        return ["mid"]

    def record(
        _log: Path,
        _argv: Sequence[str],
        _removals: Sequence[Path] = (),
        timeout: float | None = None,
    ) -> None:
        seen.append(timeout)

    monkeypatch.setattr(fleet, "flush_targets", only_mid)
    monkeypatch.setattr(detach, "start", record)
    assert fleet.flush(host, Path("commit")) == ["mid"]
    assert [_is(value, 400.0 * fleet.STRETCH) for value in seen if value is not None] == [True]
    assert len(seen) == 1

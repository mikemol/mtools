# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Autosizing: size from the max, one cap for size and climb, a counter trigger — then the climb.

⚑ THE CLIMB ARMS RUN REAL PAYLOADS IN A REAL FENCE — 64→128→256→384, a nested retry re-parented to
the outer lease, history converging after a success — and skip with the host's reason where fencing
is unavailable. Each payload touches its memory with a bytes product; a zero-filled bytearray would
never register against the cap.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from mikemol.fence import admit, autosize, core, ledger
from mikemol.fence.cgroup import FenceUnavailableError, parent_with_controllers

if TYPE_CHECKING:
    from pathlib import Path

# The origin's substrate-tuned numbers, used as fixtures only: this module ships no default.
_CEILING = 384
_DEFAULT = 192
_RAISED_DEFAULT = 1024

# The origin's measured module: it peaked near 600MB.
_BIG_PEAK = 600

# One climb step above the bare ceiling, allowed only by the raised cap.
_PAST_CEILING = 2 * _CEILING

# SIGKILL's exit status, as fence reports it (128 + 9).
_SIGKILLED = 137

# A payload that fits after one climb from 64, for the arms that only need a short ladder.
_HOG_SMALL = 100


def _killed(*verdicts: str) -> core.Result:
    """Return a finished run whose `bound_by` is `verdicts`.

    Returns:
        the result.

    """
    return core.Result(
        cmd=("payload",),
        caps=core.Caps(),
        duration_s=1.0,
        exit_code=137,
        memory_peak_bytes=None,
        bound_by=verdicts,
    )


def test_the_lease_is_the_bucket_of_the_max_not_the_median() -> None:
    """(40, 188, 90) leases 256: the bucket of 188, where the median's bucket would be 128."""
    got = autosize.size([40.0, 188.0, 90.0], default=_DEFAULT, ceiling=_CEILING)
    assert got == autosize.Sizing(ledger.bucket(188))


def test_no_history_leases_the_default() -> None:
    """With no recorded peak the lease is the default, unclamped."""
    assert autosize.size([], default=_DEFAULT, ceiling=_CEILING) == autosize.Sizing(_DEFAULT)


def test_a_peak_over_the_cap_is_clamped_and_says_so() -> None:
    """Peak 600, ceiling 384: the lease is 384 and a warning names the key, peak and cap.

    ⚑ THE CONTROL: a peak under the cap yields no warning.
    """
    clamped = autosize.size([600.0], default=_DEFAULT, ceiling=_CEILING)
    warning = autosize.clamp_warning("agda:Big", clamped, _CEILING)
    assert clamped == autosize.Sizing(_CEILING, clamped_from=600.0)
    assert warning is not None
    assert "agda:Big" in warning
    assert "600" in warning
    assert autosize.clamp_warning("agda:Small", autosize.Sizing(_DEFAULT), _CEILING) is None


def test_an_explicit_default_above_the_ceiling_raises_the_cap() -> None:
    """DEFAULT=1024 with a 600 peak leases at least 600 — the origin's silent clamp to 384."""
    got = autosize.size([float(_BIG_PEAK)], default=_RAISED_DEFAULT, ceiling=_CEILING)
    assert got.mb >= _BIG_PEAK
    assert got.clamped_from is None


def test_the_climb_obeys_the_same_raised_cap() -> None:
    """DEFAULT=1024, a 384 lease killed: the climb may pass 384 — the origin's retry could not."""
    cap = autosize.cap_of(_CEILING, _RAISED_DEFAULT)
    assert autosize.next_rung(_CEILING, cap) == _PAST_CEILING


def test_the_climb_doubles_and_stops_at_the_cap() -> None:
    """64→128→256→384 under a 384 cap, then None: bounded, never a loop."""
    rungs = [64]
    while (nxt := autosize.next_rung(rungs[-1], _CEILING)) is not None:
        rungs.append(nxt)
    assert rungs == [64, 128, 256, 384]


def test_only_a_memory_kill_triggers_a_climb() -> None:
    """`MEMORY, KILLED` climbs; a throttle, a pids trip and a bare SIGKILL do not.

    ⚑ THE BARE 137 IS THE ARM THE ORIGIN'S EXIT-CODE TRIGGER FAILS: `kill -9 $$` with no cap breach
    has an empty `bound_by` and must not climb.
    """
    assert autosize.killed_by_cap(_killed("MEMORY, KILLED (memory.events oom_kill=1 max_hits=3)"))
    assert not autosize.killed_by_cap(_killed("MEMORY, THROTTLED (memory.events max_hits=40)"))
    assert not autosize.killed_by_cap(_killed("PIDS (pids.events max=1)"))
    assert not autosize.killed_by_cap(_killed())


# --- the climb, over a real fence ---


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

# A pool comfortably above every ladder here, so admission never blocks a rung.
_POOL_MB = 4096

# The start of every climb here, and the rungs it doubles through to the fixture ceiling.
_START = 64
_LADDER = [64, 128, 256, 384]


def _hog(mb: int) -> list[str]:
    """Return a command that really touches `mb` MB — a bytes product writes every page.

    ⚑ NOT `bytearray(n)`: that is calloc-backed and zero pages are never touched, so it would not
    register against the cap at all.

    Returns:
        the argv.

    """
    return [sys.executable, "-c", f"s = b'x' * ({mb} * 1024 * 1024)"]


def _store(tmp_path: Path) -> admit.Store:
    """Return a ledger with a pool large enough that no rung waits.

    Returns:
        the store.

    """
    store = admit.Store(tmp_path / "ledger")
    admit.init(store, _POOL_MB)
    return store


@needs_cgroup
def test_a_climb_doubles_until_the_payload_fits(tmp_path: Path) -> None:
    """A ~300MB payload from 64 climbs 64→128→256→384 and completes at 384."""
    plan = autosize.Plan(_START, _CEILING, retry=True)
    results = autosize.climb(_store(tmp_path), _hog(300), plan)
    assert [r.caps.mem for r in results] == [f"{mb}M" for mb in _LADDER]
    assert results[-1].exit_code == 0
    assert all(autosize.killed_by_cap(r) for r in results[:-1])


@needs_cgroup
def test_without_retry_one_rung_runs_and_its_kill_is_the_result(tmp_path: Path) -> None:
    """Retry off: one rung, killed by the cap, and nothing more."""
    plan = autosize.Plan(_START, _CEILING, retry=False)
    [result] = autosize.climb(_store(tmp_path), _hog(300), plan)
    assert autosize.killed_by_cap(result)


@needs_cgroup
def test_a_payload_bigger_than_the_cap_stops_at_the_cap_killed(tmp_path: Path) -> None:
    """A 600MB payload under a 384 cap climbs to 384, is killed there, and stops — bounded."""
    plan = autosize.Plan(_START, _CEILING, retry=True)
    results = autosize.climb(_store(tmp_path), _hog(_BIG_PEAK), plan)
    assert [r.caps.mem for r in results] == [f"{mb}M" for mb in _LADDER]
    assert autosize.killed_by_cap(results[-1])


@needs_cgroup
def test_a_self_inflicted_sigkill_does_not_climb(tmp_path: Path) -> None:
    """A payload that `kill -9`s itself exits 137 with no cap breach, and the climb stops.

    ⚑ THE ARM THE ORIGIN'S EXIT-CODE TRIGGER FAILS; the control is the climbing arm above.
    """
    plan = autosize.Plan(_START, _CEILING, retry=True)
    [result] = autosize.climb(_store(tmp_path), ["sh", "-c", "kill -9 $$"], plan)
    assert result.exit_code == _SIGKILLED
    assert not autosize.killed_by_cap(result)


@needs_cgroup
def test_a_nested_climb_re_admits_under_the_outer_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inside an outer lease, every rung of an inner climb names the OUTER lease as its parent.

    ⚑ NEVER THE LEASE IT JUST RELEASED — that retry would be a child of a corpse, and cascade-gc
    would remove it.
    """
    store = _store(tmp_path)
    seen: list[admit.Request] = []
    real = admit.acquire

    def spy(
        store: admit.Store,
        request: admit.Request,
        waiting: admit.Waiting = admit.WAIT,
        host: admit.Host = admit.HOST,
    ) -> admit.Lease:
        seen.append(request)
        return real(store, request, waiting, host)

    # Top-level by spelling: a bare `Request` inherits `$MEMBUDGET_PARENT`, absent from this ledger.
    with admit.admit(store, admit.Request(_START, parent=admit.NO_PARENT)) as outer:
        monkeypatch.setattr(admit, "acquire", spy)
        plan = autosize.Plan(
            _START, _CEILING, retry=True, request=admit.Request(0, parent=outer.lease_id)
        )
        results = autosize.climb(store, _hog(_HOG_SMALL), plan)
    assert len(results) > 1
    assert {request.parent for request in seen} == {outer.lease_id}


@needs_cgroup
def test_a_success_records_a_peak_the_next_size_is_taken_from(tmp_path: Path) -> None:
    """After a climb succeeds, its recorded peak sizes the next lease — history converges."""
    plan = autosize.Plan(_START, _CEILING, retry=True)
    last = autosize.climb(_store(tmp_path), _hog(_HOG_SMALL), plan)[-1]
    path = tmp_path / "labels.tsv"
    assert ledger.record(path, "item:hog", last)
    peaks = [
        row.peak_mb
        for row in ledger.parse(path.read_text(encoding="utf-8"))
        if row.peak_mb is not None
    ]
    next_size = autosize.size(peaks, default=_DEFAULT, ceiling=_CEILING)
    assert next_size.mb == ledger.bucket(max(peaks))
    assert next_size.mb >= _HOG_SMALL

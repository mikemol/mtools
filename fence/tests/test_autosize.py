# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Autosizing's pure half: size from the max, one cap for size and climb, and a counter trigger.

⚑ THE CLIMB ITSELF — 64→128→256→384 over a real payload, a nested retry re-parented to the outer
lease, history converging after a success — needs `admit` and a real fence, and lands with it.
"""

from __future__ import annotations

from mikemol.fence import autosize, core, ledger

# The origin's substrate-tuned numbers, used as fixtures only: this module ships no default.
_CEILING = 384
_DEFAULT = 192
_RAISED_DEFAULT = 1024

# The origin's measured module: it peaked near 600MB.
_BIG_PEAK = 600

# One climb step above the bare ceiling, allowed only by the raised cap.
_PAST_CEILING = 2 * _CEILING


def _killed(*verdicts: str) -> core.Result:
    """Return a finished run whose `bound_by` is `verdicts`.

    Returns:
        the result.

    """
    return core.Result(cmd=("payload",), caps=core.Caps(), duration_s=1.0, exit_code=137,
                       memory_peak_bytes=None, bound_by=verdicts)


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

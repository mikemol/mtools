# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Integration: a real cgroup, a real payload, a real reading.

⚑⚑ THESE SKIP RATHER THAN PASS WHEN THE HOST CANNOT FENCE. A test that silently succeeds without
ever creating a cgroup is the exact defect this tool argues against — "nothing tripped" is
meaningful only if something could have. The skip names the missing capability.
"""

from __future__ import annotations

import pytest

from mikemol.fence import core
from mikemol.fence.cgroup import FenceUnavailableError, parent_with_controllers
from mikemol.fence.core import Caps

pytestmark = pytest.mark.needs_cgroup

# A payload that allocates far more than the tight cap below, and prints so a silent no-op fails.
HOG = ["python3", "-c", "x = bytearray(256*1024*1024); print(len(x))"]


def _unfenceable() -> str:
    """Return why this host cannot fence, or the empty string if it can.

    ⚑⚑⚑ THE REASON IS THE MEASUREMENT, NOT A GUESS ABOUT IT. This returned `bool` and threw the
    exception away, so the skip line could only ever carry a HARDCODED cause — and it said *no
    delegated cgroup v2 memory+pids subtree on this host* on a k3s executor where cassian
    measured that subtree POPULATED with memory and pids. The refusal was real; the stated cause
    was invented, and no reading of the skip could tell.

    ⚑⚑ IT ALSO SURVIVED THE FIX THAT WAS SUPPOSED TO REPAIR IT. `parent_with_controllers` was
    corrected to refuse at the cgroup root by its own name; the remote run still printed the old
    sentence, because this `reason=` string is a SECOND HOME for the same false claim and is what
    a reader actually sees. A message repaired at the raise site is not repaired at the report
    site.

    ⚑ SO THE EXCEPTION'S OWN TEXT IS CARRIED THROUGH. The skip then names the requirement that
    failed — a non-root cgroup, an undelegated controller, no v2 membership — and a reader can
    act on it instead of chasing the one cause this string used to assert.
    """
    try:
        parent_with_controllers(["memory", "pids"])
    except FenceUnavailableError as e:
        return f"cannot fence here: {e}"
    return ""


_WHY = _unfenceable()

needs_cgroup = pytest.mark.skipif(bool(_WHY), reason=_WHY or "host can fence")


@needs_cgroup
class TestObserveOnlyRun:
    """⚑ THE HEADLINE PROPERTY: a complete measurement with nothing capped."""

    def test_measures_without_capping(self) -> None:
        """A no-caps run completes, is marked observe-only, and binds nothing."""
        r = core.run_once(["/usr/bin/env", "true"])
        assert r.caps.observe_only
        assert r.exit_code == 0
        assert r.bound_by == ()
        assert r.completed_within_caps

    def test_peak_is_read_and_is_not_zero(self) -> None:
        """Charge real pages to the fence, or report None.

        A 0 here would mean the reading missed the scope — the wrong-cgroup defect this
        package's docstring cites, where a 35MB cell reported 4.7MB.
        """
        r = core.run_once(["/usr/bin/env", "true"])
        assert r.memory_peak_bytes is None or r.memory_peak_bytes > 0

    def test_events_are_present_and_clean(self) -> None:
        """An uncapped run kills nothing."""
        r = core.run_once(["/usr/bin/env", "true"])
        assert r.memory_events.get("oom_kill", 0) == 0


@needs_cgroup
class TestExitCodes:
    """The payload's own result reaches the caller unchanged."""

    def test_nonzero_propagates(self) -> None:
        """A failing payload's code is the fence's code."""
        assert core.run_once(["/usr/bin/env", "false"]).exit_code == 1

    def test_missing_command(self) -> None:
        """A command that does not exist is 127, the shell's own spelling."""
        r = core.run_once(["definitely-not-a-real-binary-xyzzy"])
        assert r.exit_code == core.EXIT_NOT_FOUND

    def test_a_failed_payload_is_still_measured(self) -> None:
        """Measure the runs most worth measuring.

        ⚑ THE READING IS IN `finally`, so a payload that failed does not also lose its
        measurement — which would drop exactly the cases a caller is investigating.
        """
        r = core.run_once(["/usr/bin/env", "false"])
        assert r.exit_code == 1
        assert r.memory_events != {} or r.memory_peak_bytes is not None


@needs_cgroup
class TestCapBinds:
    """⚑ THE F-ARM. A cap that never binds proves nothing, so one must actually trip."""

    def test_a_tight_memory_cap_binds(self) -> None:
        """A 256MB allocation under an 8MB cap trips the memory cap and says so."""
        r = core.run_once(HOG, Caps(mem="8M", swap="0"))
        assert r.bound_by, "a 256MB allocation under an 8MB cap must trip the memory cap"
        assert r.bound_by[0].startswith("MEMORY")
        assert not r.completed_within_caps

    def test_the_same_payload_passes_uncapped(self) -> None:
        """The T-arm: the identical command completes uncapped.

        Without this, the F-arm above cannot distinguish a working cap from a broken payload.
        """
        r = core.run_once(HOG)
        assert r.exit_code == 0
        assert r.bound_by == ()

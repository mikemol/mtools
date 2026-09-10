# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Cap semantics and byte parsing — the pure half, no cgroup required."""

from __future__ import annotations

import pytest

from mikemol.fence.cgroup import CG_ROOT, bound_by, cgroup_of_line, human_to_bytes
from mikemol.fence.core import Caps

BOTH_CAPS_BOUND = 2


class TestCgroupOfLine:
    """⚑⚑⚑ THE PATH ARITHMETIC THAT DECIDES RUN-VS-SKIP, AND IT HAD NO TEST.

    `own_cgroup()` was only ever exercised through the integration guard, which SKIPS on failure
    — so the one expression separating "this host can fence" from "it cannot" was checked by a
    mechanism whose failure mode is silence.

    ⚑⚑ THE ARITHMETIC, reproduced here from this module's own source rather than from a peer's
    trace:

        /proc/self/cgroup = "0::/"  ->  split("::",1)[1] = "/"  ->  lstrip("/") = ""
        CG_ROOT / ""                =  /sys/fs/cgroup
        .parent                     =  /sys/fs              <- OUTSIDE THE HIERARCHY
        parent/"cgroup.subtree_control" = /sys/fs/cgroup.subtree_control   (does not exist)

    ⚑ THESE ARMS PIN THE ARITHMETIC, NOT A VERDICT ABOUT ANY HOST. That distinction was paid for:
    a refusal built on this expression was added and withdrawn the same day, because what `0::/`
    MEANS depends on the mount. At containerd's default bind it names the pod's own slice — a
    real, writable, controller-delegated cgroup — and only a `hostPath` that escapes the pod's
    cgroup namespace makes it name the machine's root. The path computation below is a fact about
    `PurePath`; whether reaching it indicates a broken host is a fact about `/proc/self/mountinfo`
    and is NOT asserted here. See the withdrawal note in `cgroup.py:parent_with_controllers`.
    """

    def test_a_root_cgroup_line_is_the_hierarchy_root(self) -> None:
        """`0::/` names the root itself, not a child of it."""
        assert cgroup_of_line("0::/") == CG_ROOT

    def test_the_root_has_no_parent_inside_the_hierarchy(self) -> None:
        """⚑ AT THE ROOT, `.parent` ESCAPES THE CGROUP TREE — a property of the path, not a host.

        Whether a caller ever legitimately sits here is the separate question the withdrawn
        refusal got wrong; this arm asserts only what the arithmetic does.
        """
        assert not cgroup_of_line("0::/").parent.is_relative_to(CG_ROOT)

    def test_a_nested_cgroup_line_keeps_its_parent_inside(self) -> None:
        """⚑ THE POSITIVE CONTROL: a normal pod path has a parent that IS a cgroup directory.

        Without this arm the assertion above would pass against a `is_relative_to` that always
        returned False, and the test would report a defect the code does not have.
        """
        own = cgroup_of_line("0::/kubepods/besteffort/podXYZ")
        assert own.parent.is_relative_to(CG_ROOT)
        assert own.parent == CG_ROOT / "kubepods/besteffort"


class TestObserveOnly:
    """⚑ THE PROPERTY THIS PACKAGE EXISTS TO MAKE DEPENDABLE.

    The origin script separated measurement from actuation by construction and never said so, so
    a reader could not tell whether the no-caps case was supported or degenerate. These pin it.
    """

    def test_no_caps_is_observe_only(self) -> None:
        """An empty `Caps` imposes nothing."""
        assert Caps().observe_only

    @pytest.mark.parametrize("caps", [
        Caps(mem="1G"),
        Caps(swap="0"),
        Caps(pids=64),
        Caps(io="259:0 wbps=1048576"),
    ])
    def test_any_cap_is_not_observe_only(self, caps: Caps) -> None:
        """Any single cap set takes the run out of observe-only."""
        assert not caps.observe_only

    def test_swap_zero_is_a_cap_not_an_absence(self) -> None:
        """Reject the falsy reading of `swap="0"`.

        ⚑ "0" IS A VALUE, NOT AN ABSENCE. It forbids swap, which is what turns `memory.max` from
        a reclaim threshold into a kill boundary on a zram host — so a falsy check that read it
        as unset would silently disarm the fence.
        """
        assert not Caps(swap="0").observe_only

    def test_observe_only_still_needs_controllers(self) -> None:
        """Require memory+pids even when nothing is capped.

        The controller set is a property of what is READ, not only of what is capped:
        `memory.peak` does not exist in a cgroup whose memory controller was never enabled.
        """
        assert Caps().controllers() == ["memory", "pids"]

    def test_io_cap_adds_its_controller(self) -> None:
        """An io cap pulls the io controller into the requirement."""
        assert "io" in Caps(io="259:0 wbps=1048576").controllers()


class TestHumanToBytes:
    """The kernel's own spellings, including the one that is not a number."""

    @pytest.mark.parametrize(("given", "want"), [
        ("512", "512"),
        ("1K", "1024"),
        ("2M", "2097152"),
        ("1G", "1073741824"),
        ("1T", "1099511627776"),
        ("1g", "1073741824"),
    ])
    def test_sizes(self, given: str, want: str) -> None:
        """Each suffix multiplies, and a bare integer passes through."""
        assert human_to_bytes(given) == want

    def test_max_passes_through(self) -> None:
        """`max` is the kernel's spelling for no-limit and must not become a number."""
        assert human_to_bytes("max") == "max"


class TestBoundBy:
    """⚑ WHICH CAP BOUND, FROM THE COUNTERS — never inferred from an exit code."""

    def test_nothing_bound(self) -> None:
        """Clean counters name no binding cap."""
        assert bound_by({"oom_kill": 0, "max": 0}, {"max": 0}) == []

    def test_memory_oom_kill(self) -> None:
        """An oom_kill names the memory cap."""
        out = bound_by({"oom_kill": 1, "max": 3}, {"max": 0})
        assert len(out) == 1
        assert out[0].startswith("MEMORY")

    def test_memory_throttle_without_kill_still_counts(self) -> None:
        """Count limit hits without a kill as the memory cap binding.

        ⚑ THE THROTTLE-INTO-RECLAIM CASE, measured on a zram host as 261 limit hits and zero
        kills. Reporting only `oom_kill` would call that run unbounded.
        """
        out = bound_by({"oom_kill": 0, "max": 261}, {"max": 0})
        assert out
        assert out[0].startswith("MEMORY")

    def test_a_throttle_and_a_kill_do_not_render_the_same_verdict(self) -> None:
        """⚑⚑⚑ ONE LABEL OVER TWO OUTCOMES, ON A SWAP-BACKED HOST.

        `bound_by` branched on `oom_kill > 0 OR max > 0` — two distinct conditions, one string.
        So a payload THROTTLED into compressed swap and a payload KILLED both rendered as
        `BOUND BY MEMORY`.

        ⚑⚑ MEASURED, both arms, 2026-09-10, `--mem 8M` against a deliberate 256MB allocation
        (reported by cassian-observability-11 and reproduced here independently):

            --mem 8M           payload COMPLETED, printed 268435456 bytes
                               rc=0   oom_kill=0  max_hits=1424  peak=8400896
            --mem 8M --swap 0  payload KILLED
                               rc=137 oom_kill=1  max_hits=35    peak=8388608

        ⚑ ARM A ALLOCATED THE FULL 256MB AND LIVED. The cap held the RESIDENT SET to 8MB and let
        the rest spill to zram; the enclosing `memory.swap.max` reads `max` on this host. A reader
        seeing `BOUND BY MEMORY` with rc=0 concludes the cap held the workload down. It did not.

        ⚑⚑ AND IT INVERTS BY SUBSTRATE, which is what makes the collapse expensive rather than
        untidy: k8s sets `memory.swap.max=0` on a Guaranteed pod cgroup, so the SAME declared cap
        is a hard ceiling in a pod and a throttle on this host. The verdict string was the only
        place a caller could have learned which.

        ⚑ THE OPERANDS WERE ALWAYS PRINTED — `oom_kill=` and `max_hits=` are both in the string.
        Only the LEAD LABEL collapsed them, which is why nothing looked wrong: this module's own
        `--swap` help already says *0 = no swap, so mem is a kill boundary not a throttle*. The
        knowledge was in the tool and absent from the verdict.
        """
        throttled = bound_by({"oom_kill": 0, "max": 1424}, {"max": 0})
        killed = bound_by({"oom_kill": 1, "max": 35}, {"max": 0})
        assert throttled
        assert killed
        assert throttled[0] != killed[0], (
            "a payload that completed in swap and one the kernel killed must not render the "
            "same verdict; the distinction is oom_kill, and it is already in the counters"
        )

    def test_a_throttle_names_itself_a_throttle(self) -> None:
        """⚑ THE READER'S QUESTION IS `was my workload held down`, and only this answers it."""
        assert "THROTTLED" in bound_by({"oom_kill": 0, "max": 1424}, {"max": 0})[0]

    def test_a_kill_names_itself_a_kill(self) -> None:
        """⚑ THE POSITIVE CONTROL: renaming the throttle must not rename the kill."""
        assert "KILLED" in bound_by({"oom_kill": 1, "max": 35}, {"max": 0})[0]

    def test_pids(self) -> None:
        """A pids.events max hit names the pids cap."""
        out = bound_by({}, {"max": 7})
        assert len(out) == 1
        assert out[0].startswith("PIDS")

    def test_both(self) -> None:
        """Two caps binding are reported as two findings, not one."""
        assert len(bound_by({"oom_kill": 1}, {"max": 2})) == BOTH_CAPS_BOUND

    def test_unreadable_counters_bind_nothing(self) -> None:
        """An empty dict means the question could not be asked, which must not read as a trip."""
        assert bound_by({}, {}) == []

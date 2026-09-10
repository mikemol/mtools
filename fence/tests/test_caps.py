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

    ⚑⚑ MEASURED ON THE k3s EXECUTOR, 2026-09-10, reported by cassian-observability-11 and
    reproduced here from this module's own source rather than from their trace:

        /proc/self/cgroup = "0::/"  ->  split("::",1)[1] = "/"  ->  lstrip("/") = ""
        CG_ROOT / ""                =  /sys/fs/cgroup
        .parent                     =  /sys/fs              <- OUTSIDE THE HIERARCHY
        parent/"cgroup.subtree_control" = /sys/fs/cgroup.subtree_control   (does not exist)

    ⚑ SO THE GUARD READ A SIBLING OF THE CGROUP TREE AND CALLED THE OSError A DELEGATION
    FAILURE. Its message said *no delegated cgroup v2 memory+pids subtree on this host* while
    cassian measured that subtree POPULATED with memory and pids — a true refusal asserting a
    cause it never tested, which is the class this distribution's BUILD file documents one level
    up.
    """

    def test_a_root_cgroup_line_is_the_hierarchy_root(self) -> None:
        """`0::/` names the root itself, not a child of it."""
        assert cgroup_of_line("0::/") == CG_ROOT

    def test_the_root_has_no_parent_inside_the_hierarchy(self) -> None:
        """⚑ THE DEFECT, PINNED: at the root, `.parent` escapes the cgroup tree entirely."""
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

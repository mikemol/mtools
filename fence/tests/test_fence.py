# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Integration: a real cgroup, a real payload, a real reading.

⚑⚑ THESE SKIP RATHER THAN PASS WHEN THE HOST CANNOT FENCE. A test that silently succeeds without
ever creating a cgroup is the exact defect this tool argues against — "nothing tripped" is
meaningful only if something could have. The skip names the missing capability.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from mikemol.fence import core
from mikemol.fence.cgroup import FenceUnavailableError, parent_with_controllers
from mikemol.fence.core import Caps

pytestmark = pytest.mark.needs_cgroup

# A payload that allocates far more than the tight cap below, and prints so a silent no-op fails.
HOG = ["python3", "-c", "x = bytearray(256*1024*1024); print(len(x))"]

# A `--pids` value carried through a ratchet's base caps. ⚑ NAMED rather than written inline
# twice: the arm sets it and asserts it, and two spellings of one fixture value is the drift this
# tree keeps measuring in larger objects.
PIDS_CARRIED = 8


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

    Returns:
        The exception's own message when this host cannot fence, or the EMPTY STRING when it can.
        ⚑⚑ A STRING RATHER THAN A BOOL, AND THAT IS THE REPAIR THIS DOCSTRING IS ABOUT: the bool
        version threw the cause away, so the skip line could only carry a hardcoded guess — and
        the guess was measured WRONG on a k3s executor. Emptiness carries the boolean meaning at
        no cost, and the non-empty case carries the only thing a reader can act on.

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


class TestRatchetSweep:
    """The cap ladder itself, which a mutation sweep found unexercised.

    ⚑⚑⚑ MEASURED 2026-09-12: replacing `core.ratchet`'s body with `raise` changed NO test verdict,
    the only survivor in 50-plus sites across `fence` and `hooks`. The arms that exist test
    `cli._report_ratchet` — the REPORTER — with hand-built `Result` objects, so the function that
    actually walks the ladder was never called. That is the same shape as the finding one layer
    over in `mdstruct`, where five modes were registered, documented, gate-checked and never run.

    ⚑⚑ AND IT IS THE FUNCTION `cassian-observability-6a`'s WHOLE REPORT WAS ABOUT. They
    reconstructed a descending ladder out of kernel OOM records because this tool's summary never
    reached their journal; the sweep they were reading is produced here, and nothing asserted it
    stops where it says it stops.

    ⚑ NO CGROUP IS NEEDED FOR ANY OF THIS. Every contract below is about the LOOP — which steps
    run, in what order, carrying which base caps — and injecting the runner is what separates that
    question from the delegated-subtree question `TestObserveOnlyRun` already answers. An arm that
    needed a real fence would be unrunnable in the sandbox where the suite runs, which is how a
    contract goes untested for as long as this one did.

    ⚑⚑ SO THE MODULE'S `needs_cgroup` MARKER IS OVERRIDDEN HERE, DELIBERATELY. Inheriting it would
    attach a requirement that is FALSE of these arms — and a marker is a declaration a reader and a
    runner both act on, so a false one is the mis-declared-population defect wearing a pytest hat.
    The sibling classes keep it because they genuinely fence.
    """

    pytestmark: ClassVar[list[pytest.MarkDecorator]] = []

    @staticmethod
    def _recording(binds_at: str | None = None) -> tuple[list[Caps], object]:
        """Return `(seen, runner)` — a fake `run_once` recording the caps it was handed.

        Returns:
            The list it appends to, and the runner itself. ⚑ The list is returned rather than
            read back off the function, so an arm asserts against the ACTUAL call sequence
            instead of a reconstruction of it.

        """
        seen: list[Caps] = []

        def runner(cmd: tuple[str, ...], caps: Caps) -> core.Result:
            seen.append(caps)
            bound = ("MEMORY",) if caps.mem == binds_at else ()
            return core.Result(cmd=cmd, caps=caps, duration_s=0.0, exit_code=0,
                               memory_peak_bytes=1, bound_by=bound)

        return seen, runner

    def test_the_sweep_stops_at_the_first_cap_that_binds(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        """⚑⚑⚑ THE STOPPING RULE, which is the whole point of a ratchet.

        A sweep that ran every step would report the TIGHTEST cap as binding rather than the
        FIRST, and those are different answers: the first is the scale of the resource the command
        needs, the tightest is only the end of the list the caller happened to type.
        """
        seen, runner = self._recording(binds_at="32M")
        monkeypatch.setattr(core, "run_once", runner)
        out = core.ratchet(("true",), ["64M", "32M", "16M", "8M"])
        assert [c.mem for c in seen] == ["64M", "32M"], (
            f"the sweep did not stop at the binding cap; it ran {[c.mem for c in seen]}"
        )
        assert [r.caps.mem for r in out] == ["64M", "32M"], (
            f"the returned sequence does not match what ran: {[r.caps.mem for r in out]}"
        )
        assert out[-1].bound_by, "the last result is not the binding one"

    def test_the_sweep_returns_every_step_not_only_the_verdict(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        """⚑⚑ THE CAPS THAT DID NOT BIND ESTABLISH THAT THE BINDING ONE IS A BOUNDARY.

        The function's own docstring states it: a caller handed only the last result cannot tell
        *it bound at 32M* from *it fails at every cap*. Nothing asserted the sequence survived
        until now, and `cli._sweep_payload` publishes it to consumers as `rungs`.
        """
        _seen, runner = self._recording(binds_at="16M")
        monkeypatch.setattr(core, "run_once", runner)
        out = core.ratchet(("true",), ["64M", "32M", "16M"])
        assert [r.caps.mem for r in out] == ["64M", "32M", "16M"], (
            f"the non-binding steps were dropped from the sequence: {[r.caps.mem for r in out]}"
        )
        # ⚑ ONE ASSERTION PER STEP, because a composite reports which CONJUNCTION failed and not
        # which STEP — and the whole subject here is that a particular step is misreported.
        unbound = [r.caps.mem for r in out if not r.bound_by]
        assert unbound == ["64M", "32M"], (
            f"a step that did not bind is reported as binding; unbound steps were {unbound}"
        )

    def test_a_sweep_that_never_binds_runs_every_step(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        """⚑ THE CONTROL, without which the stopping arm is satisfied by a loop that always stops.

        A sweep breaking after the first step would pass an arm asserting *it stopped*; this pins
        that it stops only when something BINDS. It is also the honest-negative case the reporter
        renders as *completed within ALL caps* — a frugal command, or a mechanism that is not the
        resource the caller ratcheted.
        """
        seen, runner = self._recording(binds_at=None)
        monkeypatch.setattr(core, "run_once", runner)
        out = core.ratchet(("true",), ["64M", "32M", "16M"])
        assert [c.mem for c in seen] == ["64M", "32M", "16M"], (
            f"a sweep with no binding cap did not run every step: {[c.mem for c in seen]}"
        )
        assert not any(r.bound_by for r in out), "a step bound when the runner never binds"

    def test_the_base_caps_carry_through_every_step(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        """⚑⚑ ONLY `mem` RATCHETS; THE OTHER CAPS ARE THE INVARIANT the sweep measures against.

        A ladder that dropped `--swap 0` between steps would change what a memory cap MEANS
        halfway down — a throttle at one rung and a kill boundary at the next — so the binding cap
        it reported would not be a measurement of one thing. The tool's own advice tells callers to
        add `--swap 0` to make the cap a kill boundary, which is only sound if it survives.
        """
        seen, runner = self._recording(binds_at="16M")
        monkeypatch.setattr(core, "run_once", runner)
        core.ratchet(("true",), ["64M", "32M", "16M"], base=Caps(swap="0", pids=8))
        assert seen, "no step ran — the assertions below would hold over nothing"
        assert all(c.swap == "0" and c.pids == PIDS_CARRIED for c in seen), (
            f"the base caps did not survive the ladder: "
            f"{[(c.mem, c.swap, c.pids) for c in seen]}"
        )

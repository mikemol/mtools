# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run one command inside a transient cgroup and return what it consumed.

⚑⚑⚑ MEASUREMENT AND ACTUATION ARE SEPARATE, AND THAT IS NOW DECLARED RATHER THAN INCIDENTAL.
Every cap in `Caps` is optional; the reading in `finally` is unconditional. So `Caps()` with
nothing set is a COMPLETE OBSERVE-ONLY RUN: a cgroup is created, the payload is charged to it,
its peak/duration/events are read, and nothing is ever capped or killed.

This was true of the original tool by construction and undocumented, which made it true by
accident from a reader's point of view — a caller could not tell whether the no-caps case was a
supported mode or a degenerate one, so nobody could depend on it. `Caps.observe_only` names it,
and the test suite exercises it, so it is now a property rather than a coincidence.

⚑⚑ WHY THE SEPARATION IS WORTH NAMING. A workspace census found this to be the ONLY tool in ten
repositories that returns structured timing and memory for a child command without also having
the power to kill it. The alternatives measure by killing (an OOM ladder whose kill IS the
reading) or measure the wrong scope entirely (reading `/proc/self/cgroup` from a shell while the
work runs in a child scope, under-reporting a 35MB cell as 4.7MB). An observer that cannot
actuate can be pointed at anything; a fused one cannot.

⚑ THE PARENT READS, NOT THE CHILD. The reading happens after `waitpid` in the parent, before the
cgroup is removed — so it survives a payload that was killed, crashed, or exec-failed. A design
that read from inside the payload would lose exactly the runs worth measuring.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mikemol.fence import cgroup

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

POLL = 0.2

# ⚑ THE RESULT'S JSON SHAPE, NAMED. `dict[str, object]` is honest but propagates: a list
# comprehension over it types as `list[Any]`, which under `disallow_any_expr` is an error at the
# CALLER rather than here — so the fix belongs at the definition, where the shape is known.
type ResultJSON = dict[str, object]

# Exit codes for conditions that are NOT the payload's own result.  They follow the shell's
# convention (126 = found but not executable, 127 = not found) so a caller's existing handling
# already means the right thing; 125 is "the harness itself could not run", which is the
# cannot-run verdict this workspace keeps distinct from a failure everywhere else.
EXIT_HARNESS = 125
EXIT_NOT_EXECUTABLE = 126
EXIT_NOT_FOUND = 127


@dataclass(frozen=True)
class Caps:
    """The caps to impose. Every field optional; all-unset is a valid observe-only run.

    ⚑ `swap` IS `str | None` AND NOT `bool`, because "0" is a MEANINGFUL VALUE distinct from
    unset. `swap="0"` forbids swap — which is what makes `mem` a kill boundary instead of a
    reclaim threshold on a host with zram — while `swap=None` leaves the kernel's default. A
    boolean could not say "0", and a plain falsy check would read "0" as absent.
    """

    mem: str | None = None
    swap: str | None = None
    pids: int | None = None
    io: str | None = None

    @property
    def observe_only(self) -> bool:
        """Whether this run imposes no cap at all — measurement fully separated from actuation."""
        return self.mem is None and self.swap is None and self.pids is None and self.io is None

    def controllers(self) -> list[str]:
        """Name the controllers the parent must delegate for this run.

        ⚑ `memory` AND `pids` ARE ALWAYS REQUESTED, EVEN OBSERVE-ONLY, because the measurement
        needs them: `memory.peak` and `pids.events` do not exist in a cgroup whose controllers
        were never enabled. The controller set is a property of what is being READ, not only of
        what is being capped — which is why an observe-only run is not a zero-requirement run.

        Returns:
            The controller names, always including `memory` and `pids`. ⚑ NEVER EMPTY, and the
            paragraph above is why: an empty set would be the honest answer to *what must be
            capped* and the wrong answer to *what must be delegated*, and this function answers
            the second. A run that delegated nothing would report a peak of `None` and no events
            — measurement silently absent, in the tool whose product is measurement.

        """
        want = ["memory", "pids"]
        if self.io is not None:
            want.append("io")
        return want


@dataclass(frozen=True)
class Result:
    """What one fenced run consumed, and which cap (if any) bound it."""

    cmd: tuple[str, ...]
    caps: Caps
    duration_s: float
    exit_code: int | None
    memory_peak_bytes: int | None
    memory_events: dict[str, int] = field(default_factory=dict)
    pids_events: dict[str, int] = field(default_factory=dict)
    bound_by: tuple[str, ...] = ()

    @property
    def completed_within_caps(self) -> bool:
        """Whether the payload finished cleanly with no cap binding it."""
        return not self.bound_by and self.exit_code == 0

    def as_dict(self) -> ResultJSON:
        """Render for `--json`, in the shape the original tool emitted.

        Returns:
            A plain dict matching `ResultJSON`. ⚑ THE SHAPE IS THE ORIGIN TOOL'S, DELIBERATELY:
            this package was extracted from a script consumers already parse, so changing field
            names here would break every one of them to gain nothing. The tuples become lists
            because JSON has no tuple, which is a serialisation fact rather than a design one.

        """
        return {
            "cmd": list(self.cmd),
            "caps": {"mem": self.caps.mem, "swap": self.caps.swap,
                     "pids": self.caps.pids, "io": self.caps.io},
            "duration_s": self.duration_s,
            "exit_code": self.exit_code,
            "memory_peak_bytes": self.memory_peak_bytes,
            "memory_events": self.memory_events,
            "pids_events": self.pids_events,
            "bound_by": list(self.bound_by),
            "completed_within_caps": self.completed_within_caps,
        }


def _apply(cg: Path, caps: Caps) -> None:
    """Write the caps BEFORE the payload runs, so a breach is a genuine cap-trip.

    ⚑ ORDER IS LOAD-BEARING: a cap applied after the payload starts cannot bind what already
    happened, so a run capped late reports a clean pass for work that exceeded the bound.
    """
    if caps.mem is not None:
        cgroup.write_interface(cg, "memory.max", cgroup.human_to_bytes(caps.mem))
    if caps.swap is not None:
        cgroup.write_interface(cg, "memory.swap.max", cgroup.human_to_bytes(caps.swap))
    if caps.pids is not None:
        cgroup.write_interface(cg, "pids.max", str(caps.pids))
    if caps.io is not None:
        cgroup.write_interface(cg, "io.max", caps.io)


def _child(cg: Path, cmd: Sequence[str]) -> None:
    """Join the fence, then exec. Never returns.

    ⚑ THE CHILD JOINS BEFORE IT EXECS, so the payload and every descendant it spawns are charged
    to the fence. Joining after exec would leave a window in which the payload runs uncharged,
    and a short payload could finish inside it.
    """
    try:
        with (cg / "cgroup.procs").open("w") as f:
            f.write(str(os.getpid()))
    except OSError as e:  # pragma: no cover — the child never returns to the test process
        # ⚑ `sys.stderr.write`, NOT `print`: after fork there is no caller to raise to, and an
        # unbuffered direct write is the only report available between fork and exec.
        sys.stderr.write(f"mikemol-fence: child could not join fence: {e}\n")
        os._exit(EXIT_HARNESS)
    try:
        # ⚑ `execvp` WITH AN ARGV LIST IS THE SAFETY PROPERTY, not a risk to be waived: it is
        # precisely what avoids a shell. Routing the payload through one would add an
        # interpreter that re-splits arguments the caller already separated.
        os.execvp(cmd[0], list(cmd))  # ruff: ignore[start-process-with-no-shell] — no shell IS the intent; see above
    except FileNotFoundError:
        os._exit(EXIT_NOT_FOUND)
    except PermissionError:
        os._exit(EXIT_NOT_EXECUTABLE)


def run_once(cmd: Sequence[str], caps: Caps | None = None) -> Result:
    """Run `cmd` in a transient fence cgroup and return what it consumed.

    With `caps=None` (or an all-unset `Caps`) this imposes nothing and only measures.

    Returns:
        A `Result` carrying the payload's exit code, wall duration, peak memory and the counters
        — plus `bound_by`, naming which cap bound if any did. ⚑ THE PAYLOAD'S OWN FAILURE IS A
        RESULT, NOT AN EXCEPTION: a command that exits 1 or is OOM-killed has been measured
        successfully, and that is exactly what this function was asked to do.

    Raises:
        cgroup.FenceUnavailableError: when the HOST cannot provide the cgroup — no v2 membership,
            an undelegated controller, an unwritable interface file, a `mkdir` that fails. ⚑ THE
            SEPARATION IS THE CONTRACT: *I could not fence* raises and *your command failed*
            returns, so a caller never has to guess which of the two a nonzero means. The prose
            above stated both facts already; only their form has changed.

    """
    caps = caps or Caps()
    parent = cgroup.parent_with_controllers(caps.controllers())
    cg = parent / f".mikemol-fence.{os.getpid()}.{int(time.time())}"
    try:
        cg.mkdir()
    except OSError as e:
        msg = f"cannot create fence cgroup {cg}: {e}"
        raise cgroup.FenceUnavailableError(msg) from e

    _apply(cg, caps)

    t0 = time.time()
    child = os.fork()
    if child == 0:
        _child(cg, cmd)

    rc: int | None = None
    try:
        while True:
            pid, status = os.waitpid(child, os.WNOHANG)
            if pid == child:
                rc = (os.WEXITSTATUS(status) if os.WIFEXITED(status)
                      else 128 + os.WTERMSIG(status))
                break
            time.sleep(POLL)
    finally:
        # ⚑⚑ THE READING IS IN `finally` AND IS UNCONDITIONAL. This is the separation: no branch
        # here consults `caps`. A run that was killed, crashed, or never exec'd still yields its
        # peak and its events — those are the runs a caller most needs measured.
        duration = round(time.time() - t0, 2)
        mem_ev = cgroup.read_events(cg, "memory.events")
        pid_ev = cgroup.read_events(cg, "pids.events")
        peak = cgroup.read_peak(cg)
        cgroup.cleanup(cg)

    return Result(
        cmd=tuple(cmd), caps=caps, duration_s=duration, exit_code=rc,
        memory_peak_bytes=peak, memory_events=mem_ev, pids_events=pid_ev,
        bound_by=tuple(cgroup.bound_by(mem_ev, pid_ev)),
    )


def ratchet(cmd: Sequence[str], steps: Sequence[str],
            base: Caps | None = None) -> list[Result]:
    """Tighten `mem` through `steps` until one binds; return every run made.

    ⚑ THE BINDING CONSTRAINT IS THE MEASUREMENT. A cap above the payload's legitimate peak
    proves nothing — "nothing tripped" under a generous cap is not evidence of frugality. So the
    caps descend until one BINDS, and the step that binds names the scale of the resource the
    command actually needs.

    ⚑⚑ THIS IS THE ONE ACTUATING MODE, AND IT IS DELIBERATE. `run_once` may observe without
    capping; a ratchet cannot, because its reading IS the trip. Callers wanting a measurement
    without a kill want `run_once`, and the two are separate functions so the choice is explicit
    at the call site rather than implied by which flags were passed.

    Returns:
        Every run made, in the order tried — STOPPING at the first that binds, so the last entry
        is either the binding cap or the tightest step that did not bind.
        ⚑⚑ THE WHOLE SEQUENCE, NOT JUST THE VERDICT, and that is the same argument the sibling
        `mdstruct.roundtrip.fixpoint` makes about its deltas: the caps that did NOT bind are what
        establish the binding one is a boundary rather than an isolated failure. A caller handed
        only the last result cannot tell *it bound at 32M* from *it fails at every cap*.
        ⚑ NEVER EMPTY WHEN `steps` IS NON-EMPTY: the first step always runs, so a caller reading
        `results[-1]` has something to read. An empty `steps` yields an empty list — the caller
        asking for no measurement rather than a measurement that failed — and `cli._report_ratchet`
        indexes `[-1]`, so a LIBRARY caller passing no steps must not hand the result there.
        MEASURED that the CLI cannot reach it: `--ratchet ""` is falsey and takes the `run_once`
        path, so the empty list is a library contract rather than a live hazard.

    """
    base = base or Caps()
    out: list[Result] = []
    for step in steps:
        r = run_once(cmd, Caps(mem=step, swap=base.swap, pids=base.pids, io=base.io))
        out.append(r)
        if r.bound_by:
            break
    return out

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""cgroup v2 plumbing: find a delegable parent, create a transient sibling, read its counters.

⚑⚑⚑ THE FENCE IS ON THE CGROUP, NEVER ON THE PROCESS. Learned the hard way (substrate-c6): a
child process (`git stash create`) ESCAPES a per-process cap and is still charged to the cgroup.
So every cap and every reading here addresses the cgroup, and the payload joins it before exec —
which is what makes ALL DESCENDANTS accountable rather than just the process we spawned.

⚑⚑ A SIBLING, NOT A CHILD, because of cgroup v2's no-internal-process rule: a cgroup that HOLDS
processes cannot also enable controllers for its children. Our own cgroup holds us, so the fence
is created beside us under the same parent, and the parent is what must have the controllers
delegated. This is `cputimeout`'s proven pattern, reused rather than re-derived.

⚑ FAILS LOUD WHEN IT CANNOT ENFORCE. A fence that silently does not enforce is worse than no
fence: the caller reads "nothing tripped" as evidence the payload was well-behaved, when it is
evidence of nothing at all. Every refusal here names the controller and the path.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

CG_ROOT = Path("/sys/fs/cgroup")

# The unit suffixes accepted anywhere a byte count is given.  `max` is the kernel's own spelling
# for "no limit" and is passed through untouched rather than translated to a number.
_UNITS = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}

# A `key value` counter line, by the format of memory.events / pids.events.
_EVENT_FIELDS = 2


class FenceUnavailableError(RuntimeError):
    """The host cannot provide the fence this tool exists to build.

    ⚑ A DISTINCT TYPE, NOT A BARE RuntimeError, because "the fence could not be built" and "the
    payload misbehaved" are the two readings a caller must never conflate — the same
    cannot-run-vs-failed split every gate in this workspace maintains. The CLI maps this to
    exit 125, which is neither a payload exit code nor a cap trip.
    """


def human_to_bytes(value: str) -> str:
    """Render a human byte size as the kernel's own spelling.

    Accepts `max` (passed through), a bare integer, or an integer with a K/M/G/T suffix.
    Returns a string because that is what a cgroup interface file takes.
    """
    v = value.strip()
    if v == "max":
        return v
    mult = _UNITS.get(v[-1:].upper())
    if mult is None:
        return str(int(v))
    return str(int(v[:-1]) * mult)


def cgroup_of_line(line: str) -> Path:
    """Map one `0::`-prefixed /proc/self/cgroup line to its cgroup path.

    ⚑ EXTRACTED SO IT CAN BE TESTED. Inlined in `own_cgroup()` this arithmetic was reachable
    only by reading `/proc/self/cgroup`, so the one expression deciding whether a host can fence
    was exercised solely through a guard that SKIPS on failure — checked by a mechanism whose
    failure mode is silence.
    """
    return CG_ROOT / line.strip().split("::", 1)[1].lstrip("/")


def own_cgroup() -> Path:
    """Return this process's own cgroup v2 path.

    ⚑ THE `0::` PREFIX IS THE v2 LINE. A hybrid host lists v1 controllers on other lines, and
    picking the first line would silently address a v1 hierarchy where none of these interface
    files exist.
    """
    try:
        text = Path("/proc/self/cgroup").read_text(encoding="utf-8")
    except OSError as e:
        msg = f"cannot read /proc/self/cgroup: {e}"
        raise FenceUnavailableError(msg) from e
    for line in text.splitlines():
        if line.startswith("0::"):
            return cgroup_of_line(line)
    msg = "no cgroup v2 membership (is this a cgroup v2 host?)"
    raise FenceUnavailableError(msg)


def parent_with_controllers(want: Iterable[str]) -> Path:
    """Return the sibling-cgroup parent, with `want` delegated in its subtree_control.

    Enables each controller if it is not already enabled; refuses if it cannot.
    """
    own = own_cgroup()
    # ⚑⚑⚑ A REFUSAL HERE ON `own == CG_ROOT` WAS ADDED AND WITHDRAWN THE SAME DAY, AND THE
    # WITHDRAWAL IS THE FINDING. It read: *this process is at the cgroup v2 ROOT, which has no
    # parent inside the hierarchy... the fence needs a NON-ROOT cgroup; on Kubernetes that is a
    # pod placement question.* Every measurement behind that sentence was real and its premise
    # was manufactured.
    #
    # ⚑⚑ WHAT `0::/` MEANS DEPENDS ON THE MOUNT, AND NEITHER PARTY HAD READ THE MOUNT.
    # cassian-observability-11 applied a `hostPath` at /sys/fs/cgroup to make the bind writable;
    # a hostPath ESCAPES THE POD'S CGROUP NAMESPACE. `/proc/self/mountinfo` in that pod showed the
    # mount ROOT as `/../../..` — three levels up, the MACHINE's root — so `kubepods.slice`,
    # `system.slice` and `init.scope` were all visible from inside. THAT root is 0555, and that is
    # the "third wall" reported to me and recorded here as a host property. It was an artifact of
    # the bind. Post-revert the same executor reads mount root `/`, and the pod's own
    # `kubepods-pod<uid>.slice` is 0755 with memory and pids already in its subtree_control — the
    # writable, delegated parent this function wants existed the whole time.
    #
    # ⚑⚑⚑ SO AT CONTAINERD'S DEFAULT BIND, `0::/` IS CORRECT, NOT DEFECTIVE: it means *the pod's
    # own slice*, mapped onto /sys/fs/cgroup by the namespace. The refusal would have rejected a
    # correctly-placed pod. Removed rather than reworded.
    #
    # ⚑ AND IT PASSED THE BAR WHILE BEING WRONG, because no host here reaches it: this machine's
    # `/proc/self/cgroup` is a deep `user.slice/...` path, so the branch was never executed by any
    # green run. A guard whose only true arm lives on a substrate I cannot reach is one I cannot
    # test — which is why the replacement is NOT a mountinfo predicate. cassian proposes
    # distinguishing the cases by mountinfo's mount-ROOT field (`/` vs `/../../..`), and that is
    # plausibly right: measured here, this host reads root `/` on a single unambiguous line. But
    # the ESCAPED arm exists only in a pod that has now been reverted, so I would be shipping a
    # two-case predicate having exercised one case. That is the one-armed test this repository
    # refuses everywhere else.
    #
    # ⚑ WHAT WOULD SETTLE IT, and it is reachable: a run on a pod at the DEFAULT bind. If
    # `parent_with_controllers` succeeds there, `0::/` needs no special case at all and the
    # ENOENT-on-`/sys/fs/cgroup.subtree_control` path is unreachable in practice. If it fails,
    # the failure names its own cause now (see `_unfenceable` in tests/test_fence.py), which is
    # the repair that survives this reversal.
    #
    # ⚑⚑⚑ THE SETTLER RAN (cassian-observability-11, default bind, `2 remote`) AND `0::/` APPEARS
    # THERE TOO. So the escaped arm is the ORDINARY LIVE STATE of a k3s pod here, not an artifact
    # of the reverted hostPath: that bind changed WHAT THE MOUNT POINTED AT, never the
    # `/proc/self/cgroup` reading. The arithmetic above is load-bearing on this substrate after
    # all, and the withdrawal's stated premise was wrong in the other direction.
    #
    # ⚑⚑⚑ AND THE WITHDRAWN REFUSAL IS STILL NOT REINSTATED, BECAUSE IT NAMED THE WRONG CAUSE.
    # It said *the fence needs the caller to occupy a NON-ROOT cgroup; on Kubernetes that is a pod
    # placement question.* Measured post-revert: the pod's own slice is 0755 with memory+pids
    # already delegated, the container is uid 0, AND `/proc/self/cgroup` reads `0::/` — all at
    # once, because a cgroup NAMESPACE presents the slice the pod occupies AS the root. The pod is
    # correctly placed. `own_cgroup()` resolving to CG_ROOT is CORRECT. What fails is that this
    # module wants a SIBLING, and a namespaced pod has no sibling — only a child.
    #
    # ⚑⚑ A CHILD STRATEGY DOES NOT RESCUE IT, AND THAT IS MEASURED HERE RATHER THAN REASONED.
    # Two arms on this host, in a real delegated cgroup holding 75 processes:
    #   enable `+memory` in a cgroup that HOLDS processes  -> EBUSY (Device or resource busy)
    #   same write into a FRESH EMPTY child                -> ENOENT (parent never enabled memory)
    # The first IS the no-internal-process rule this module's own header cites; the second is its
    # consequence one level down. A pod cgroup holds the executor's processes, so descending into
    # it hits EBUSY exactly as creating a sibling beside it hits the namespace root.
    #
    # ⚑⚑⚑ AND THE POSITIVE HALF, WHICH THE TWO REFUSALS ABOVE DO NOT SUPPLY: what makes the
    # sibling strategy work where it works. Measured on this host, same probe shape:
    #   own    = .../app-org.kde.konsole-NNN.scope/tab(NNN).scope  holds 75 processes
    #   parent = .../app-org.kde.konsole-NNN.scope                 holds ZERO processes;
    #                                                              subtree_control: cpu memory pids
    #   mkdir a sibling under that parent -> OK, and `memory.max` is writable in it.
    # ⚑⚑ SO THE REQUIREMENT IS A PROCESS-FREE PARENT, not merely a delegated one. This host
    # supplies one because systemd interposes a scope above the leaf; that is a property of the
    # arrangement, not something this module arranges.
    # ⚑ WHICH SETTLES A COUNTERFACTUAL RATHER THAN LEAVING IT ASSERTED. A writable bind at the
    # POD'S OWN SLICE would make that slice the parent — and the pod's slice HOLDS the executor's
    # processes, so `+memory` there is the EBUSY arm above. The bind was never the missing piece;
    # it would have moved the refusal from the namespace root to the no-internal-process rule.
    # Raised by cassian-observability-11 as a conclusion; recorded here because it is entailed by
    # the two arms rather than by either alone, and neither of us had measured a working parent.
    #
    # ⚑ SO THE SIBLING PATTERN IS FORCED, NOT PREFERRED, and the honest statement is that the
    # fence cannot run in a cgroup namespace whose root holds processes — a property of the
    # substrate, not a misconfiguration and not a bug in this module. Nothing is guessed into the
    # code for it: no refusal is reinstated, no predicate is invented. The refusal below still
    # fires, and since `_unfenceable` now carries the exception's own text, what a reader sees is
    # the ENOENT on `/sys/fs/cgroup.subtree_control` — true, specific, and pointing at the path
    # that was actually read.
    parent = own.parent
    sub = parent / "cgroup.subtree_control"
    try:
        enabled = sub.read_text(encoding="utf-8").split()
    except OSError as e:
        msg = f"cannot read {sub}: {e}"
        raise FenceUnavailableError(msg) from e
    for c in want:
        if c in enabled:
            continue
        try:
            with sub.open("w") as f:
                f.write(f"+{c}")
        except OSError as e:
            msg = (f"the {c!r} controller is not delegated to your cgroup subtree — the fence "
                   f"cannot enforce {c} here (need a delegated cgroup v2 {c} controller)")
            raise FenceUnavailableError(msg) from e
    return parent


def write_interface(cg: Path, name: str, value: str) -> None:
    """Write one cgroup interface file, naming the file if the write is refused."""
    try:
        with (cg / name).open("w") as f:
            f.write(value)
    except OSError as e:
        msg = f"cannot write {name} in {cg}: {e}"
        raise FenceUnavailableError(msg) from e


def read_events(cg: Path, name: str) -> dict[str, int]:
    """Read a flat `key value` counter file (memory.events, pids.events) as a dict.

    ⚑ AN UNREADABLE COUNTER YIELDS `{}`, AND THE CALLER MUST NOT READ THAT AS ZERO. An empty
    dict means the question could not be asked; `{"oom_kill": 0}` means it was asked and the
    answer was none. `bound_by` therefore tests `.get(k, 0) > 0`, which is false in both cases —
    correct here only because an unreadable counter accompanies a cgroup that never existed.
    """
    try:
        text = (cg / name).read_text(encoding="utf-8")
    except OSError:
        return {}
    out: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == _EVENT_FIELDS:
            out[parts[0]] = int(parts[1])
    return out


def read_peak(cg: Path) -> int | None:
    """Return `memory.peak` for the fence, or None where the kernel does not carry it.

    ⚑ None IS NOT ZERO. `memory.peak` arrived in 5.19; on an older kernel the file is absent and
    the honest answer is "not measured", which a 0 would misreport as "measured, nothing used".

    ⚑⚑ THE VALUE IS A LIFETIME WATERMARK OF *THIS* CGROUP, which is exactly right here because
    the cgroup is created per run and destroyed after. Reading the same file on a long-lived
    cgroup answers a different question, and the two are not commensurable.
    """
    try:
        return int((cg / "memory.peak").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def cleanup(cg: Path) -> None:
    """Remove the transient fence cgroup, tolerating an already-gone directory.

    Best-effort by design: a failure to reap must never mask the payload's own result, which is
    the finding the run exists to produce.
    """
    with contextlib.suppress(OSError):
        cg.rmdir()


def bound_by(mem_ev: Mapping[str, int], pid_ev: Mapping[str, int]) -> list[str]:
    """Name WHICH cap bound, from the cgroup's own counters.

    ⚑⚑⚑ NEVER INFERRED FROM THE EXIT CODE. rc=137 is any SIGKILL — the OOM killer, an operator,
    a parent's timeout — so an exit code cannot distinguish "the fence bound it" from "something
    else killed it". The counters can, and that distinction is this tool's whole product: a bare
    pass/fail would leave the caller to guess the mechanism.
    """
    out: list[str] = []
    # ⚑⚑⚑ THIS WAS ONE BRANCH — `oom_kill > 0 OR max > 0` — AND IT RENDERED TWO OUTCOMES AS ONE
    # VERDICT. On a swap-backed host a memory cap does not necessarily stop a workload: it caps
    # the RESIDENT SET and the remainder spills to compressed swap. MEASURED here, `--mem 8M`
    # against a deliberate 256MB allocation (reported by cassian-observability-11, reproduced
    # independently on this host, whose enclosing `memory.swap.max` reads `max`):
    #     --mem 8M           payload COMPLETED, printed 268435456 bytes
    #                        rc=0   oom_kill=0  max_hits=1424  peak=8400896
    #     --mem 8M --swap 0  payload KILLED
    #                        rc=137 oom_kill=1  max_hits=35    peak=8388608
    # Both said `BOUND BY MEMORY`. The first is TRUE and reads as the second.
    # ⚑⚑ AND IT INVERTS BY SUBSTRATE: k8s sets `memory.swap.max=0` on a Guaranteed pod cgroup, so
    # the SAME declared cap is a hard ceiling in a pod and a throttle on a host like this one. The
    # verdict string was the only place a caller could have learned which — and it did not say.
    # ⚑ THE OPERANDS WERE ALWAYS PRINTED; only the LEAD LABEL collapsed them, which is why nothing
    # looked wrong. This module's `--swap` help already draws the distinction — *0 = no swap, so
    # mem is a kill boundary not a throttle* — so the knowledge was in the tool and absent from
    # the finding. Same class as a skip whose stated reason was never the measured one.
    if mem_ev.get("oom_kill", 0) > 0:
        out.append(f"MEMORY, KILLED (memory.events oom_kill={mem_ev['oom_kill']} "
                   f"max_hits={mem_ev.get('max', 0)}) — the cap was a ceiling")
    elif mem_ev.get("max", 0) > 0:
        out.append(f"MEMORY, THROTTLED (memory.events oom_kill=0 "
                   f"max_hits={mem_ev['max']}) — the cap bound the RESIDENT SET and the payload "
                   f"was not killed; on a swap-backed host it may have completed in swap. "
                   f"Add `--swap 0` to make the cap a kill boundary")
    if pid_ev.get("max", 0) > 0:
        out.append(f"PIDS (pids.events max={pid_ev['max']} — fork/spawn pressure hit pids.max)")
    return out

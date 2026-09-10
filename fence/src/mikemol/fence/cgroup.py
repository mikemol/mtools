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
    # ⚑⚑⚑ REFUSE AT THE ROOT BY ITS OWN NAME, BECAUSE `.parent` ESCAPES THE HIERARCHY THERE.
    # `/proc/self/cgroup` reading `0::/` means this process sits at the cgroup ROOT; `.parent` is
    # then `/sys/fs`, and `parent/"cgroup.subtree_control"` is `/sys/fs/cgroup.subtree_control` —
    # a sibling of the tree, not a file in it. The read failed with ENOENT and the OSError below
    # reported it as a DELEGATION failure.
    # ⚑⚑ MEASURED ON THE k3s EXECUTOR (cassian-observability-11, 2026-09-10): mount `rw`,
    # `cgroup.subtree_control` carrying `memory` and `pids` — both preconditions satisfied — and
    # this function still refused, saying *no delegated cgroup v2 memory+pids subtree on this
    # host*. A TRUE REFUSAL ASSERTING A CAUSE IT NEVER TESTED.
    # ⚑ AND THE ROOT IS 0555 (`dr-xr-xr-x`), so even at the correct path there is no writable
    # directory to create a sibling in — the kernel exposes the root that way regardless of the
    # mount being `rw`. Fixing the path alone would move the refusal, not remove it, so the
    # refusal names the real requirement instead: a NON-ROOT cgroup.
    if own == CG_ROOT:
        msg = ("this process is at the cgroup v2 ROOT (/proc/self/cgroup reads '0::/'), which has "
               "no parent inside the hierarchy to create a sibling fence in — and the root is "
               "mode 0555, unwritable even by uid 0. The fence needs the caller to occupy a "
               "NON-ROOT cgroup; on Kubernetes that is a pod placement question, not a mount one")
        raise FenceUnavailableError(msg)
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
    if mem_ev.get("oom_kill", 0) > 0 or mem_ev.get("max", 0) > 0:
        out.append(f"MEMORY (memory.events oom_kill={mem_ev.get('oom_kill', 0)} "
                   f"max_hits={mem_ev.get('max', 0)})")
    if pid_ev.get("max", 0) > 0:
        out.append(f"PIDS (pids.events max={pid_ev['max']} — fork/spawn pressure hit pids.max)")
    return out

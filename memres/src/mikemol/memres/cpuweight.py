# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Put the build's OWN cgroup under a proportional CPU weight.

Ported from paperkit's `tools/cpuweight.py` (paperkit:W142). Behaviour unchanged; the cgroup and
proc roots are a `Host` parameter (default: the real `/sys/fs/cgroup` and `/proc`) so a test can
plant a fake host, and `--exec` takes an injectable `execvp`. paperkit's `_self_cgroup` (defined,
never called anywhere) is not ported.

THE PROBLEM. Bazel's local scheduler admits actions against RAM and its own job count. It has NO
view of the box: another repo's test suite running concurrently is invisible to it, so two
individually-reasonable builds oversubscribe together (measured 4.7-5.4 runnable/core on 10 cores
with procs_blocked=0: pure CPU contention, not an I/O wedge).

WHY A WEIGHT AND NOT A CAP, AND WHY THIS IS THE ONLY LEVER. SCHED_BATCH is vestigial post-EEVDF;
nice 19 and the 100ms slice fight the weight downward instead of complementing it. A hard wall
(CPUQuota, a --jobs cap) cannot lend idle capacity. cpu.weight is PROPORTIONAL: it yields under
contention and takes ALL spare CPU at idle, which is what a background build should do on an
interactive machine, and a weighted task keeps a small nonzero share so a cell holding a lock
never fully deschedules.

WHY THIS CGROUP. The weight must sit on the cgroup that CONTAINS THE WORK. So do not inspect a
cgroup, MAKE one: cgroup-v2 is a hierarchy and `cpu` is delegated to the user session, so mkdir
our own node under app.slice and move the build into it. Membership is then true by CONSTRUCTION.
The Bazel SERVER forks the cells, so it is moved too, or every cell lands in the terminal's
cgroup while the build scope sits empty.

Best-effort by construction: on a machine without cgroup-v2, without `cpu` delegated to the user
hierarchy, or with the file unwritable, this is a no-op and the build proceeds unweighted. A QoL
lever must never be able to fail a build.

    mikemol-cpuweight [--weight N] [--report] [--verify] [--exec CMD...]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

CGROUP_ROOT = Path("/sys/fs/cgroup")
PROC_ROOT = Path("/proc")
DEFAULT_WEIGHT = 20  # cassian's postgres figure: yields hard under contention, all spare at idle
_BUILD_SCOPE = "paperkit-build.scope"
_APP_SLICE = "/app.slice"
_EXEC_NEEDS_COMMAND = 2


class Host(NamedTuple):
    """The two roots this module reads and writes: the cgroup-v2 mount and the proc mount."""

    cgroup_root: Path
    proc: Path


HOST = Host(CGROUP_ROOT, PROC_ROOT)

# The cell predicate, named so a test exercises THIS function rather than restating the rule.
# Matches on COMM (the executable's own name), never on argv: a /proc/*/cmdline substring test
# matches the checking process and any shell running `pgrep -f linux-sandbox` beside it.
_CELL_COMMS = ("linux-sandbox", "process-wrapper")


def _read(path: Path) -> str | None:
    """Read a proc file as text, NULs turned to spaces (the cmdline separator).

    Returns:
        The text, or None when the file cannot be read.

    """
    try:
        return path.read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
    except OSError:
        return None


def _cgroup_of(pid: str | int, host: Host = HOST) -> str | None:
    """Find the cgroup-v2 path of a pid; the line format is `0::/the/path`.

    Returns:
        The path on the unified hierarchy, or None when it has none or cannot be read.

    """
    text = _read(host.proc / str(pid) / "cgroup")
    for line in (text or "").splitlines():
        hid, ctrl, path = line.split(":", 2)
        if hid == "0" and not ctrl:
            return path
    return None


def _writable_weight_file(cg: str, host: Host = HOST) -> Path | None:
    """Find `cpu.weight` for a cgroup path, if it exists and we may write it.

    `cpu` must be enabled in the parent's subtree_control for the file to exist at all; the file's
    presence IS the delegation, and os.access answers the ownership question directly.

    Returns:
        The file's path, or None when it is absent or not writable.

    """
    weight_file = host.cgroup_root / cg.lstrip("/") / "cpu.weight"
    return weight_file if weight_file.is_file() and os.access(weight_file, os.W_OK) else None


def _app_slice(host: Host = HOST) -> str:
    """Find the user's app.slice, the parent under which we create the build's cgroup.

    Derived from OUR OWN cgroup rather than hardcoded: everything up to and including `app.slice`
    is the user's session hierarchy, and that is where transient scopes live.

    Returns:
        Our cgroup path cut after `/app.slice`; the whole path when it has none; "" when we have
        no cgroup.

    """
    cg = _cgroup_of("self", host) or ""
    at = cg.find(_APP_SLICE)
    return cg[: at + len(_APP_SLICE)] if at >= 0 else cg


def build_cgroup(name: str = _BUILD_SCOPE, host: Host = HOST) -> tuple[str | None, str]:
    """CREATE (or reuse) a cgroup that holds the build, and nothing else.

    Do not inspect a cgroup, MAKE one: under a bare `bazel` the cells inherit the CALLER's
    cgroup (the operator's terminal, beside their editor and browser), and weighting that would
    throttle the machine to make a build slower. Membership is true by CONSTRUCTION.

    Returns:
        `(path, path)` on success; `(None, reason)` when there is no cgroup-v2 hierarchy, the
        node cannot be created, or `cpu` is not delegated (no weight file in a cgroup we own).

    """
    parent = _app_slice(host)
    if not parent:
        return None, "no cgroup-v2 hierarchy - unweighted"
    node = host.cgroup_root / parent.lstrip("/") / name
    try:
        node.mkdir(exist_ok=True)
    except OSError as err:
        return None, f"cannot create {node} ({err}) - unweighted"
    if not (node / "cpu.weight").is_file():
        return None, (
            f"`cpu` not delegated to {parent} - the weight file does not exist in a "
            "cgroup we own; unweighted"
        )
    return f"{parent}/{name}", f"{parent}/{name}"


def join(cg: str, pid: str | int = "self", host: Host = HOST) -> tuple[bool, str]:
    """Move a process into `cg`; its FUTURE children inherit the cgroup.

    Returns:
        `(True, cg)` on success, `(False, reason)` when `cgroup.procs` cannot be written.

    """
    try:
        (host.cgroup_root / cg.lstrip("/") / "cgroup.procs").write_text(
            f"{os.getpid() if pid == 'self' else pid}\n",
            encoding="utf-8",
        )
    except OSError as err:
        return False, f"cannot join {cg} ({err})"
    return True, cg


def build_servers(host: Host = HOST) -> list[str]:
    """List every long-lived Bazel SERVER JVM, the processes that actually fork this build's cells.

    Joining the launcher is NOT enough: Bazel's client hands the request to a persistent server
    that survives between invocations, cells are forked by THAT process, and a client that joins
    a fresh scope moves only itself. The server announces itself as `bazel(<workspace>)`; the
    client does not.

    Returns:
        The pids (as strings) whose command line contains `bazel(`.

    """
    out: list[str] = []
    for entry in host.proc.iterdir():
        if not entry.name.isdigit():
            continue
        argv = _read(entry / "cmdline")
        if argv is not None and "bazel(" in argv:
            out.append(entry.name)
    return out


def is_cell(comm: str) -> bool:
    """Say whether a process COMM is one of this build's cells.

    Returns:
        True for `linux-sandbox` and `process-wrapper`.

    """
    return comm in _CELL_COMMS


def verify(cg: str, host: Host = HOST) -> tuple[bool, str]:
    """Check whether this build's CELLS are actually in `cg`.

    That is the property that matters, versus that a cgroup was created and the caller joined it.
    Cells are matched on COMM, never on argv, so the checker does not count itself.

    Returns:
        `(True, ...)` when no cells run or all are inside; `(False, ...)` when some are outside.

    """
    inside = outside = 0
    for entry in host.proc.iterdir():
        if not entry.name.isdigit():
            continue
        comm = _read(entry / "comm")
        if comm is None or not is_cell(comm.strip()):
            continue
        if _cgroup_of(entry.name, host) == cg:
            inside += 1
        else:
            outside += 1
    if inside == 0 and outside == 0:
        return True, "no cells running yet - nothing to verify"
    if outside:
        return False, f"{outside} cell(s) OUTSIDE {cg} ({inside} inside) - the weight is inert"
    return True, f"all {inside} cell(s) inside {cg}"


def apply(
    weight: int = DEFAULT_WEIGHT,
    pid: str | int | None = None,
    host: Host = HOST,
) -> tuple[bool, str]:
    """Set cpu.weight on the BUILD's cgroup (or `pid`'s, when given explicitly).

    Returns:
        `(True, "<before> -> <weight> (<cg>)")` when it wrote; `(False, reason)` when there is no
        cgroup, the file is not writable, the weight is already set, or the write failed.

    """
    if pid is not None:
        cg = _cgroup_of(pid, host)
    else:
        cg, why = build_cgroup(host=host)
        if cg is None:
            return False, why
    if cg is None:
        return False, "no cgroup-v2 entry (not a cgroup-v2 machine?) - unweighted"
    weight_file = _writable_weight_file(cg, host)
    if weight_file is None:
        return False, f"cpu.weight not writable for {cg} (cpu not delegated?) - unweighted"
    try:
        before = weight_file.read_text(encoding="utf-8").strip()
        if before == str(weight):
            return False, f"already at {weight} ({cg})"
        weight_file.write_text(f"{weight}\n", encoding="utf-8")
    except OSError as err:
        return False, f"cpu.weight write failed ({err}) - unweighted"
    return True, f"{before} -> {weight} ({cg})"


def runnable_ratio(host: Host = HOST) -> tuple[float, int]:
    """Read the box's CPU-contention reading: procs_running per core, and procs_blocked.

    procs_running counts tasks that want CPU NOW. It is NOT loadavg: the 1-minute average is
    decayed and counts D-state as runnable, so it cannot tell a CPU-saturated box from an
    I/O-wedged one. procs_blocked carries the I/O half, so the PAIR discriminates.

    Returns:
        `(procs_running / cores, procs_blocked)`.

    """
    running = blocked = 0
    for line in (host.proc / "stat").read_text(encoding="utf-8").splitlines():
        if line.startswith("procs_running"):
            running = int(line.split()[1])
        elif line.startswith("procs_blocked"):
            blocked = int(line.split()[1])
    return running / (os.cpu_count() or 1), blocked


def _weight_of(argv: Sequence[str]) -> int:
    """Read `--weight N` or `--weight=N` from `argv`.

    Returns:
        The last weight given, else `DEFAULT_WEIGHT`.

    """
    weight = DEFAULT_WEIGHT
    for i, arg in enumerate(argv):
        if arg == "--weight" and i + 1 < len(argv):
            weight = int(argv[i + 1])
        elif arg.startswith("--weight="):
            weight = int(arg.split("=", 1)[1])
    return weight


def _weigh_and_join(weight: int, host: Host) -> None:
    """Create and weight the build cgroup, join it, move the Bazel servers in, and report.

    The report goes to stderr; a missing cgroup is reported as `cpu.weight: <reason>`.
    """
    cg, why = build_cgroup(host=host)
    if cg is None:
        sys.stderr.write(f"cpu.weight: {why}\n")
        return
    _, why = apply(weight, host=host)
    joined, _ = join(cg, host=host)
    moved = [pid for pid in build_servers(host) if join(cg, pid, host)[0]]
    ratio, blocked = runnable_ratio(host)
    sys.stderr.write(
        f"cpu.weight: {why}; joined={joined}; servers_moved={len(moved)}; "
        f"box runnable/core={ratio:.2f} blocked={blocked}\n",
    )


def main(
    argv: Sequence[str] | None = None,
    host: Host = HOST,
    execvp: Callable[[str, list[str]], object] = os.execvp,
) -> int:
    """Create and weight the build cgroup; `--report` reads the box, `--exec` execs a command in it.

    Bare invocation just creates and weights. `--verify` asks whether the cells are inside.
    `--exec CMD...` puts THIS process in the weighted cgroup and execs CMD, so every child of the
    build inherits it. Best-effort: never fail the build.

    Returns:
        0 normally (also when unweighted); 1 when `--verify` finds cells outside the scope; 2
        when `--exec` has no command.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if "--report" in args:
        ratio, blocked = runnable_ratio(host)
        sys.stdout.write(f"runnable/core={ratio:.2f} blocked={blocked} cores={os.cpu_count()}\n")
        return 0
    _weigh_and_join(_weight_of(args), host)
    if "--verify" in args:
        cg, _ = build_cgroup(host=host)
        ok, why = verify(cg, host) if cg else (False, "no build cgroup")
        sys.stderr.write(f"cpuweight verify: {why}\n")
        return 0 if ok else 1
    if "--exec" in args:
        cmd = args[args.index("--exec") + 1 :]
        if not cmd:
            sys.stderr.write("cpuweight: --exec needs a command\n")
            return _EXEC_NEEDS_COMMAND
        execvp(cmd[0], cmd)  # inherits the cgroup we just joined
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

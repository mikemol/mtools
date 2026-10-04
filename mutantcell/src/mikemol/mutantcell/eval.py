# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run a claim's check against a mutated engine and report whether it FLIPS: one def-sweep cell.

Ported from paperkit's `tools/eval.py` (paperkit:W142). The engine runs off its .pyc BUILD
ARTIFACTS with ONE module's bytecode swapped for its mutant; the empty-set baseline swaps a
module's identity .pyc, a no-op.

The file was split three ways once ruff's C901 + PLR0915 named its 127-line `main()` for doing
five jobs, each part to a module with ONE subject:

    cellargs     what the cell was ASKED to do (a typed record, not a Namespace)
    cellstage    what the check SEES (bytecode placement, the four counterfactual kinds)
    cellcgroup   what the cell COST (its own cgroup: peak memory, OOM events)

What remains is the cell's actual job: run the check, decide what its exit meant, record it.

Idempotency: invoke by an ABSOLUTE interpreter path so `sys.executable` is populated: the check is
re-spawned as `[sys.executable, check, claim]` (the history of the '' spurious-flip bug).

Differences from paperkit, and why: `main` takes `cgroup` and `caps` keywords (defaults are the
real cgroup and the real, irreversible CPU and address-space caps) so a test can plant a cgroup and
decline the caps instead of capping the test runner; `descendants` takes the `/proc` directory;
the siblings are imported as `mikemol.mutantcell.*`, not `tools`.
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import os
import pathlib
import resource
import signal
import subprocess
import sys
from typing import TYPE_CHECKING, cast

from mikemol.mutantcell import cellargs, cellcgroup, cellstage

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

CANNOT_RUN = 3
WHY_CHARS = 300
BASELINE = "0"

_MIB = 1024 * 1024
DEFAULT_CPU_S = 60
# 2048MB: an order of magnitude above the 28 MB a real witness peaks at, and well under the
# 4096MB rung that a runaway allocation blew through.
DEFAULT_MEM_MB = 2048
DEFAULT_WALL_S = 600
_PROC = pathlib.Path("/proc")
_KILL_SWEEPS = 50
_REAP_WAIT_S = 5
# 90%, not >=: the kernel kills AT the limit and the reaped child's accounted time lands just
# under it (measured: a 2s cap reported <2.0). An OOM kill (-9 too) burns far less, so the
# margin still separates the two.
_CAP_FRACTION = 0.9

# THE BOUND ON THE TREE, WITHOUT A CGROUP. A fork-bomb mutant (flipping `config.positionals` makes
# the gate spawn gates recursively) is not bounded by any per-process rlimit, and in a REMOTE
# EXECUTOR with isolation `none` there is no per-action cgroup, so the tree grew until the whole
# executor pod OOM-killed (measured 2026-09-23: pids.peak 15,491 against a normal 219). Counting
# descendants between communicate() slices and killing the tree past TREE_MAX turns the runaway
# into a FLIP with its reason, the same fold this file makes for a hang. TREE_MAX is a TRIGGER, not
# a hard cap: the recursion keeps forking for up to one TREE_POLL_S and during the kill sweeps
# (measured: harness counted 279 at the poll that fired, pids.peak was 562).
TREE_MAX = 256
# 0.2s, NOT 0.05s: at 50ms the harness's OWN /proc scans, made costlier by the growing tree,
# tripped the RLIMIT_CPU that `cap_cpu` sets on THIS process, killing it before it could write a
# verdict. The bound fires early, while the tree is still small, so a slower poll costs little.
TREE_POLL_S = 0.2

# BY ANCESTRY, NOT BY PROCESS GROUP. Recursing gates run their own checks with process_group=0, so
# every level starts a NEW group: a pgrp count stayed tiny and killpg on one group orphaned the
# rest. Count every DESCENDANT by walking ppid, and register this process as a CHILD SUBREAPER so
# an orphaned descendant reparents to US (not the pod's init), stays countable and killable.
_PR_SET_CHILD_SUBREAPER = 36


def cap_cpu(cpu: int) -> None:
    """Cap CPU time for this process and everything it forks.

    A flip mutant can make the check NON-TERMINATING, and a mutant that never answers HAS flipped
    the check: a real behavioural change the sweep must see. Measuring CPU rather than wall keeps
    a lease-queued cell from a false flip.

    NOT A `preexec_fn`, which runs between fork and exec where a THREADED parent has only the
    calling thread while other threads' locks stay held forever. Setting the limit on the parent
    lets the child inherit it across fork+exec, with no callback in the unsafe window.

    SOFT == HARD. With soft < hard the kernel sends SIGXCPU at the soft limit, whose default
    action is a core dump: each mutant this cap stopped (the EXPECTED outcome) reached
    systemd-coredump as a crash record. With soft == hard the first action is SIGKILL, so a
    coredump means a real crash. RLIMIT_CORE is zeroed for the same reason: the kill is the
    signal, the dump is only I/O.
    """
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def cap_mem(mb: int) -> None:
    """Cap ADDRESS SPACE for this process and everything it forks: the memory twin of `cap_cpu`.

    KEPT, BUT IT DID NOT FIX THE CASE IT WAS BUILT FOR. The theory was that a flip mutant looping
    WHILE APPENDING burns memory rather than CPU. Proven to BIND in isolation (a runaway
    allocation raises MemoryError under it) and REFUTED against the live cell: the runaway there
    is PROCESS RECURSION, and neither a per-process RLIMIT nor a per-process CPU cap bounds a tree
    that grows by forking. The tree bound is `wait_for_check`'s. This cap stays because it is
    correct for the case it names: a single process that allocates without bound is still worth
    stopping.

    RLIMIT_AS rather than RLIMIT_DATA: it bounds mmap too, which is where a large list's realloc
    actually lands. Set on the parent so the child inherits it across fork+exec.
    """
    b = mb * _MIB
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


def become_subreaper() -> None:
    """Make orphaned descendants reparent to this process (Linux prctl), so none escape the count.

    Best-effort: on a kernel or libc without it, orphans reparent to init and would escape. The
    count then still covers every descendant whose parent is alive, which is the recursion's shape.
    """
    with contextlib.suppress(OSError, AttributeError):
        libc = ctypes.CDLL(None, use_errno=True)
        prctl = cast("Callable[[int, int, int, int, int], int]", libc.prctl)
        prctl(_PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)


def descendants(root: int, proc: pathlib.Path = _PROC) -> list[int]:
    """List every live descendant pid of `root`, from one /proc scan: no cgroup needed.

    A process that exits between listing and reading is simply not counted: vanished is gone.
    ZOMBIES ARE NOT COUNTED. As subreaper we inherit orphans, and one that exits becomes a zombie
    under us until reaped, still a /proc entry. Counting them would let a LEGITIMATE check whose
    grandchildren outlive their parents creep toward TREE_MAX. And they are NOT reaped while the
    check runs: waitpid(-1) could reap the check itself out from under communicate(), which would
    then report a wrong exit code. Reaping happens in `kill_tree`.

    Returns:
        The descendants' pids, breadth first; empty when `proc` cannot be listed.

    """
    children: dict[int, list[tuple[int, bool]]] = {}
    try:
        entries = list(proc.iterdir())
    except OSError:
        return []
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_bytes()
        except OSError:
            continue
        # fields after the comm's closing ')': state ppid ...  (comm may contain spaces/parens)
        rest = raw.rsplit(b")", 1)[-1].split()
        if len(rest) > 1:
            children.setdefault(int(rest[1]), []).append((int(entry.name), rest[0] == b"Z"))
    out: list[int] = []
    frontier = [root]
    while frontier:
        nxt: list[int] = []
        for pid in frontier:
            for c, zombie in children.get(pid, ()):
                if not zombie:
                    out.append(c)
                nxt.append(c)
        frontier = nxt
    return out


def kill_tree(p: subprocess.Popen[bytes]) -> None:
    """SIGKILL every descendant of this process until none survive, then reap them all.

    Repeated because a fork bomb can create members between one sweep and the next; reaped
    because, as subreaper, orphans are OUR children and would otherwise linger as zombies.
    """
    me = os.getpid()
    for _ in range(_KILL_SWEEPS):
        victims = descendants(me)
        if not victims:
            break
        for pid in victims:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGKILL)
        with contextlib.suppress(ChildProcessError):
            while os.waitpid(-1, os.WNOHANG)[0] > 0:
                pass
    with contextlib.suppress(Exception):
        p.wait(timeout=_REAP_WAIT_S)


def last_line(raw: bytes | None) -> str:
    """Name the final non-empty output line: the check's own account of what happened.

    Returns:
        That line cut to `WHY_CHARS`; empty when there was no output.

    """
    if not raw:
        return ""
    lines = [ln for ln in raw.decode("utf-8", "replace").strip().splitlines() if ln.strip()]
    return lines[-1][:WHY_CHARS] if lines else ""


def env_int(name: str, default: int) -> int:
    """Read a positive integer knob from the environment.

    Returns:
        The variable's integer value; `default` when it is unset, empty or not an integer.

    """
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def wait_for_check(p: subprocess.Popen[bytes], wall: int) -> tuple[bytes | None, str]:
    """Wait for the check, counting its process tree between short communicate() slices.

    communicate(), NEVER wait(): a PIPE nothing drains DEADLOCKS the child the moment it writes
    past the 64KB buffer. communicate() drains and waits in one call, and may be re-called after a
    TimeoutExpired without losing output, so it is called in slices.

    Returns:
        `(output, "")` when the check ended on its own; `(None, reason)`, with the tree killed,
        when the tree grew past its bound or the check outlived `wall` seconds.

    """
    tree_max = env_int("PAPERKIT_CHECK_TREE", TREE_MAX)
    waited = 0.0
    while True:
        try:
            return cast("bytes | None", p.communicate(timeout=TREE_POLL_S)[0]), ""
        except subprocess.TimeoutExpired:
            waited += TREE_POLL_S
        size = len(descendants(os.getpid()))
        if size > tree_max:
            kill_tree(p)
            return None, (
                f"process tree reached {size} > {tree_max} (killed) \N{EM DASH} the mutation "
                "recursed by forking, which is a flip"
            )
        if waited >= wall:
            kill_tree(p)
            return (
                None,
                f"did not terminate within {wall}s (killed) \N{EM DASH} the mutation flipped it",
            )


def cap_note(rc: int) -> str:
    """Say so when a child was killed at the CPU cap.

    A child killed at the CPU cap (SIGKILL now that soft == hard; SIGXCPU before) left only its
    last output line, which says nothing about why it died. The verdict is unchanged (any nonzero
    rc is a flip); only the RECORDED reason gains the cause.

    Returns:
        The reason sentence when `rc` is a cap kill that burned at least 90% of the cap; else "".

    """
    if rc not in {-signal.SIGKILL, -signal.SIGXCPU}:
        return ""
    cap = resource.getrlimit(resource.RLIMIT_CPU)[1]
    used = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_s = used.ru_utime + used.ru_stime
    if cap != resource.RLIM_INFINITY and cpu_s >= _CAP_FRACTION * cap:
        return (
            f"exceeded its {cap}s CPU cap ({cpu_s:.1f}s used; killed by "
            f"{signal.Signals(-rc).name}) \N{EM DASH} the mutation made it spin, which is a flip"
        )
    return ""


def run(check: str, claim: str, wall: int) -> tuple[bool, str]:
    """Run one check; decide whether it flipped.

    EVERY CELL KEEPS ITS LAST LINE. "It went red" is not evidence; "it went red HERE, saying
    THIS" is: a mutation the check genuinely CAUGHT and a mutation that broke the witness so it
    raised BEFORE the check ran are both `rc != 0`, and one bit cannot separate them where one
    line can. This RECORDS a reason; it does not GATE on one. Both streams are merged because a
    check may report its diagnosis on STDOUT.

    A FORK THAT CANNOT HAPPEN IS A FLIP. The pids bound stops a mutant that recurses by forking,
    but the budget is exhausted by the CHECK's own recursion, so the next process that cannot
    fork is this one, a frame above: the harness would die before writing its record, a HARNESS
    verdict. A mutant that exhausts the process budget has flipped the check too.

    Returns:
        `(flipped, why)`: whether the check went red (or hung, forked away, or spun), and the
        last output line or the reason it was stopped.

    """
    become_subreaper()  # orphaned descendants must stay countable and killable
    try:
        p = subprocess.Popen(
            [sys.executable, check, claim],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            process_group=0,
        )
    except OSError as e:
        return True, (
            f"could not spawn the check ({e.__class__.__name__}: {e}) \N{EM DASH} the mutation "
            "exhausted the cell's process budget, which is a flip"
        )
    out, reason = wait_for_check(p, wall)
    if reason:
        return True, reason
    # `Popen.returncode` is `int | Any` in typeshed (None before the child exits): narrowed at the
    # read. After communicate() it is always an int.
    rc = cast("int", p.returncode)
    note = cap_note(rc)
    if note:
        return True, note
    return rc != 0, last_line(out)


def apply_caps() -> None:
    """Cap this process's CPU time and address space; the children inherit both."""
    cap_cpu(env_int("PAPERKIT_CHECK_CPU", DEFAULT_CPU_S))
    cap_mem(env_int("PAPERKIT_CHECK_MEM_MB", DEFAULT_MEM_MB))


def main(
    argv: Sequence[str] | None = None,
    *,
    cgroup: cellcgroup.Cgroup = cellcgroup.SELF,
    caps: Callable[[], None] = apply_caps,
) -> int:
    """Stage the counterfactual, run the check, and record whether it flipped and why.

    An OOM is NOT a flip. `rc != 0` is right for a HANG (a mutant that never answers HAS changed
    behaviour) and wrong for a cell the kernel killed for memory: that is a verdict about the
    HARNESS (measured: cap <=32MB read "flipped", >=64MB did not, so one claim graded `broken` or
    `behavioral` by its memory ladder alone). Exiting `CANNOT_RUN` hands the signal back to the
    layer that OWNS the retry (cgroup-scope retries on a nonzero PAYLOAD exit, and this process IS
    the payload), and writes no record.

    Returns:
        0 after writing the `{claim, site, flipped, why}` record to `--out`; `CANNOT_RUN` when the
        flip coincided with an OOM in `cgroup` (the peak is still written).

    """
    a = cellargs.parse(sys.argv[1:] if argv is None else argv)
    tag = cellstage.cache_tag()
    cellstage.place_engine(a.engine_dir, tag)
    cellstage.deliver(
        cellstage.Site(
            a.site,
            a.module,
            a.mutant_py,
            a.mutant_pyc,
            a.content_path,
            a.content_textfile,
        ),
        tag,
    )

    caps()
    before = cellcgroup.oom_counts(cgroup)
    flipped, why = run(a.check, a.claim, env_int("PAPERKIT_CHECK_TIMEOUT", DEFAULT_WALL_S))

    if a.site == BASELINE and flipped:
        # the empty-set cell is the canary: sens FAILS LOUD on it rather than emitting a
        # plausible-but-wrong sens set, and it must say WHY on the spot.
        sys.stderr.write(
            "eval: BASELINE FLIPPED (the identity mutation broke the check) \N{EM DASH} "
            f"{why or 'no output'}\n"
        )

    if flipped and cellcgroup.oom_happened(before, cellcgroup.oom_counts(cgroup)):
        sys.stderr.write(
            "eval: OOM-KILLED at this cell's cap (not a flip) \N{EM DASH} deferring to the climb\n"
        )
        cellcgroup.write_peak(a.peak, cgroup)
        return CANNOT_RUN

    cellcgroup.write_peak(a.peak, cgroup)
    rec: dict[str, object] = {"claim": a.claim, "site": a.site, "flipped": flipped, "why": why}
    pathlib.Path(a.out).write_text(json.dumps(rec) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

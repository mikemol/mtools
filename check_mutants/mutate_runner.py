# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Mutate every def-site in a distribution's sources and report what its suite NOTICES.

⚑⚑⚑ THE QUESTION IS NOT *DOES THE SUITE PASS* BUT *WOULD IT NOTICE*. A green suite over code
nothing exercises is the defect this repository measures most, and no checker here answers it:
ruff and mypy read the sources, pytest reads its own assertions, and none of them can say whether
removing a function's body would change a verdict. This can, at def-site granularity.

⚑⚑ AND IT CATCHES ONE OF THE FOUR VACUITY SHAPES, WHICH `paperkit-82` ESTABLISHED AGAINST THEIR
OWN FRAMEWORK BEFORE I ASKED. Their phrasing, kept because it bounds the claim: *mutation testing
at this granularity tests whether your test EXERCISES code, not whether it MEASURES anything.*
Three of the four shapes are POPULATION defects — a set never populated, a set filtered empty by a
false premise — and no def-site mutation can express *return a differently ordered list*. This is
one instrument among several, and saying so is what keeps a green here from reading as coverage.

⚑ AST REWRITE INTO A TEMP TREE, NOT A CACHED BYTECODE ARTIFACT, AND THE COST WAS MEASURED BEFORE
THE ARCHITECTURE WAS CHOSEN. paperkit builds each mutant as a content-addressed `.pyc` because
their grid is 223 claims wide and the caching pays for the per-module build targets and declared
import DAG it requires. Measured here, per cell:

    ratchet  0.2s      hooks  0.4s      fence  0.5s      mdstruct  1.4s

158 def-sites across four distributions is **under four minutes whole-tree**, and `-x` means a
KILLED cell stops at the first failing test — only SURVIVORS pay a full suite. That is the
opposite of the cost profile a caching layer is built for, so importing one would buy nothing and
cost the build-graph surgery paperkit named as its price.
"""

from __future__ import annotations

import ast
import atexit
import concurrent.futures
import contextlib
import contextvars
import ctypes
import dataclasses
import fnmatch
import functools
import json
import os
import pathlib
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from select import select as wait_readable
from typing import TYPE_CHECKING, Protocol, cast

# ⚑⚑ THE FENCE SIBLING EDGE (mtools:W619, ruled A+B 2026-10-04). This runs under each
# distribution's own `.venv`, and only fence's carries `mikemol.fence`, so `mutate_check.sh` names
# the sibling's source root in `MUTATE_FENCE_SRC` (staged by each `:mutants` target's
# `//fence:fence` data) and it goes on THIS interpreter's path only; a suite receives the variable
# inert. `sys.path.extend` is the one statement an import may follow.
#
# ⚑⚑ THE MUTATION SIBLING EDGE (mtools:W629), THE SAME MECHANISM: the declared-defect path reads and
# plants through `mikemol.mutation.declarations`, its source root named in `MUTATE_MUTATION_SRC` and
# staged by each `:mutants` target's `//mutation:mutation` data. Standard library only, so it adds
# nothing to a distribution's own environment.
sys.path.extend(
    p
    for var in ("MUTATE_FENCE_SRC", "MUTATE_MUTATION_SRC")
    for p in os.environ.get(var, "").split(os.pathsep)
    if p
)

from mikemol.fence.git_env import clean_env
from mikemol.mutation.declarations import DECLARATION_FILE, Declared, plant, read_declarations
from mikemol.mutation.sitewalk import GRID, FuncNode, Site, walk

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

CORE_LABEL = "mutants-core"
"""The prefix of the label claims that stand for cores (W1765): `mutants-core:<k>`."""

_FNV_OFFSET = 2166136261
_FNV_PRIME = 16777619
_FNV_MASK = 0xFFFFFFFF

_NO_TESTS_COLLECTED = 5
"""pytest's exit code for a run that collected nothing: the control could not name its test."""

_CONTROLS: dict[str, bool] = {}
"""Whether a test fails on the UNMUTATED module, by test id (W2340): asked once per test."""

_PRIVATE_PYTHON: dict[str, str] = {}
"""The private venv interpreter built for a real site-packages directory, per process."""


def shard_spec(raw: str) -> tuple[int, int] | None:
    """Read `MUTATE_SHARD`, `i/N`: this run's share of the grid, none when unset.

    ⚑ A TARGET THAT TIMES OUT UNDER LOAD IS SPLIT, NOT GIVEN MORE TIME (operator 2026-10-10,
    mtools:W970). Each shard runs only the sites whose stable hash falls in its share.

    Returns:
        `(index, count)`, or None for the whole grid.

    Raises:
        ValueError: when `raw` is not `i/N` with `0 <= i < N`.

    """
    if not raw:
        return None
    index, _, count = raw.partition("/")
    if not (index.isdigit() and count.isdigit()) or int(count) < 1 or int(index) >= int(count):
        msg = f"MUTATE_SHARD must be i/N with 0 <= i < N, got {raw!r}"
        raise ValueError(msg)
    return int(index), int(count)


def in_shard(key: str, shard: tuple[int, int] | None) -> bool:
    """Say whether a site or declared defect belongs to this shard.

    ⚑ A HASH THAT IS THE SAME ON EVERY RUN AND EVERY HOST (FNV-1a over the key's bytes), not
    `hash()`, which is randomised per process: every key lands in exactly one of the N shards, so
    the union of the shards is the whole grid with no overlap.

    Returns:
        True for the whole grid, else whether the key's hash falls in this shard's share.

    """
    if shard is None:
        return True
    digest = _FNV_OFFSET
    for byte in key.encode():
        digest = ((digest ^ byte) * _FNV_PRIME) & _FNV_MASK
    return digest % shard[1] == shard[0]


@dataclasses.dataclass(frozen=True)
class Selection:
    """What this run runs: one named site, or this run's share of the grid.

    ⚑ ONE TARGET PER SITE NEEDS A WAY TO NAME THE SITE (mtools:W1881, W1833). `site` is a site's
    own key as the report prints it (`src/pkg/mod.py::func`, or a declared defect's
    `src/pkg/mod.py::label`), and the run is exactly that one cell.
    """

    shard: tuple[int, int] | None = None
    site: str = ""

    def keep(self, key: str) -> bool:
        """Say whether a site or declared defect is in this run.

        Returns:
            equality with the named site when one is set, else membership in the shard.

        """
        return key == self.site if self.site else in_shard(key, self.shard)

    @property
    def share(self) -> int:
        """Say how many runs split the machine.

        Returns:
            the shard count, one for a whole grid or a single site.

        """
        return 1 if self.shard is None else self.shard[1]

    def label(self, dist: str) -> str:
        """Name the run in the report.

        Returns:
            the dist, with its shard or its site.

        """
        if self.site:
            return f"{dist} site {self.site}"
        return dist if self.shard is None else f"{dist} shard {self.shard[0]}/{self.shard[1]}"


def select(raw_shard: str, site: str) -> Selection:
    """Read `MUTATE_SHARD` and `MUTATE_SITE`.

    Returns:
        the selection; a site and a shard select the grid two ways, so setting both is refused.

    Raises:
        ValueError: when both are set, or the shard is malformed.

    """
    shard = shard_spec(raw_shard)
    if site and shard is not None:
        msg = "MUTATE_SITE and MUTATE_SHARD select the grid two ways; set one"
        raise ValueError(msg)
    return Selection(shard, site)


def read_declared(dist: pathlib.Path) -> list[Declared]:
    """Read the distribution's declared defect classes, none when it has no `mutants.regex`.

    Returns:
        the declarations in file order; empty when the file is absent.

    Raises:
        ValueError: when the file is malformed; the message names the file and the line.

    """
    path = dist / DECLARATION_FILE
    if not path.is_file():
        return []
    try:
        return read_declarations(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        msg = f"{DECLARATION_FILE}: {exc}"
        raise ValueError(msg) from exc


def run_declared(grid: Grid, declared: Declared, *, debug: bool = False) -> str:
    """Plant one declared defect in a temp copy and run the distribution's suite against it.

    ⚑⚑ FOUR OUTCOMES, NOT THREE: `killed` (the suite noticed), `survived` (it is blind to a defect
    the distribution named), `errored` (the suite did not run, or the declaration is bad: a module
    that is not there, a rewrite that no longer parses) and `unapplied` (the pattern matches
    nothing, so no defect was planted and no question was asked: a STALE declaration).

    Returns:
        the outcome.

    """
    path = grid.dist / declared.module
    if not path.is_file():
        return "errored"
    try:
        mutant = plant(path.read_text(encoding="utf-8"), declared.spec)
    except ValueError:
        return "errored"
    if mutant is None:
        return "unapplied"
    return _run_text(grid, pathlib.Path(declared.module), mutant, debug=debug)


# ⚑ THE SANDBOX STAGES ONLY WHAT IS DECLARED, so these are the trees a mutant must not carry into
# its copy. `.venv` in particular is a directory of pointers at host absolute paths — the property
# that makes it unfit as a bazel input makes it unfit to copy.
_NOT_SOURCE_PATTERNS = (".venv", "build", "*.egg-info", "__pycache__", ".*_cache", "bazel-*")


def _not_source(_directory: str, names: list[str]) -> set[str]:
    """Name the entries of one directory that a mutant's copy must leave behind.

    ⚑ WRITTEN OUT RATHER THAN `shutil.ignore_patterns(...)`, whose return type carries `Any` in
    its first parameter — a callable the root's strict mypy cannot admit as an expression.

    Returns:
        the subset of `names` matching any pattern in `_NOT_SOURCE_PATTERNS`.

    """
    return {n for n in names if any(fnmatch.fnmatch(n, p) for p in _NOT_SOURCE_PATTERNS)}


_ENUM_BASES = frozenset(
    {"enum.Enum", "Enum", "enum.StrEnum", "StrEnum", "enum.IntEnum", "IntEnum"},
)


@dataclasses.dataclass(frozen=True)
class Grid:
    """What every mutant of one distribution shares: its interpreter, its tree, its config."""

    py: pathlib.Path
    dist: pathlib.Path
    config: pathlib.Path


@dataclasses.dataclass(frozen=True)
class Mutant:
    """One def-site to mutate: the module it lives in, that module's source, the site's path."""

    rel: pathlib.Path
    source: str
    name: str


# ⚑⚑ NO WALL-CLOCK TIMEOUT (operator 2026-09-23/24, "avoid wall-clock timeouts"; W1376). A mutant
# that turns a bounded wait into an unbounded one (a retry loop around the raised `AssertionError`)
# never ends its suite, and without a bound ONE such cell held the whole grid until bazel's own
# ceiling killed it (W356/W359). The bound used to be 60 s of WALL time, and on a loaded host
# elapsed time measures contention, not whether the suite is stuck: three shards were refused at
# 300 s with no test failing (2026-10-17), and each of them passes alone in about 110 s.
#
# So a suite is ended for one of two ABSENCES, never for being slow:
#   - HUNG: for `MUTATE_PATIENCE` polls in a row (every `MUTATE_POLL_S` seconds) neither its
#     output nor the CPU of its whole process tree changed. A slow suite on a loaded host still
#     advances its CPU every poll, so it is never ended; the count is of polls without progress,
#     and any progress resets it. This is `katas.hangwatch`'s rule (W1126), written again here
#     because this runner runs under each distribution's own venv and may import nothing of katas.
#   - SPINNING: its CPU seconds reach `MUTATE_CPU_S` (an `RLIMIT_CPU` on the suite process), for a
#     mutant that turns a wait into a busy loop, which a CPU-advancing tree never shows as hung.
_DEFAULT_POLL_S = 5.0
_DEFAULT_PATIENCE = 24
_DEFAULT_CPU_S = 120.0
_AFTER_COMM = 2
_PPID = 1
_UTIME = 11
_STIME = 12
_PGRP = 2
_BLOCK = 65536


def limits() -> tuple[float, int, float]:
    """Read the absence witness's knobs from the environment.

    Returns:
        (poll interval in seconds, polls of no progress that count as hung, CPU seconds a suite may
        use) from `MUTATE_POLL_S`, `MUTATE_PATIENCE` and `MUTATE_CPU_S`, with their defaults.

    """
    poll = float(os.environ.get("MUTATE_POLL_S", "") or _DEFAULT_POLL_S)
    patience = int(os.environ.get("MUTATE_PATIENCE", "") or _DEFAULT_PATIENCE)
    cpu = float(os.environ.get("MUTATE_CPU_S", "") or _DEFAULT_CPU_S)
    return poll, patience, cpu


def _stat(pid: str) -> tuple[int, int, int] | None:
    """Read one process's parent, CPU ticks and process group from `/proc/<pid>/stat`.

    The command name may hold spaces and parentheses, so fields count from the LAST `)`.

    Returns:
        (parent pid, utime + stime in ticks, process group), or None when the process is gone or
        unreadable.

    """
    try:
        text = pathlib.Path("/proc", pid, "stat").read_text(encoding="utf-8", errors="replace")
        fields = text[text.rindex(")") + _AFTER_COMM :].split()
        ticks = int(fields[_UTIME]) + int(fields[_STIME])
        return int(fields[_PPID]), ticks, int(fields[_PGRP])
    except (OSError, ValueError, IndexError):
        return None


def tree_cpu(root: int) -> float | None:
    """Sum the CPU seconds of `root` and every live descendant, read from `/proc`.

    ⚑ A TREE THAT IS GONE IS None, NOT 0: a finished suite and an idle one are different answers,
    and the sum falls when a descendant ends, which `_hung` counts as progress, never as stillness.

    Returns:
        the seconds, or None when `root` is not a live process.

    """
    own = _stat(str(root))
    if own is None:
        return None
    children: dict[int, list[tuple[int, int]]] = {}
    for entry in pathlib.Path("/proc").iterdir():
        row = _stat(entry.name) if entry.name.isdecimal() else None
        if row is not None:
            children.setdefault(row[0], []).append((int(entry.name), row[1]))
    ticks, pending = own[1], [root]
    while pending:
        for pid, used in children.get(pending.pop(), []):
            ticks += used
            pending.append(pid)
    return ticks / os.sysconf("SC_CLK_TCK")


def group_cpu(group: int) -> float | None:
    """Sum the CPU seconds of every live process in a process group, read from `/proc`.

    ⚑ THE SUITE'S GROUP OUTLIVES THE SUITE WHEN IT LEAKS A CHILD: `tree_cpu` of a finished leader is
    None, but a grandchild still in its session holds the group open. Pipes used to make the read
    wait on such a child until the wall timer killed it, and the katas mutants
    `child-shares-the-waiters-group` and `timeout-leaves-the-tree` were recorded KILLED that way;
    with files the suite exits at once and they survived. The group is the witness for what is left.

    Returns:
        the seconds, or None when no process is in the group.

    """
    ticks, found = 0, False
    for entry in pathlib.Path("/proc").iterdir():
        row = _stat(entry.name) if entry.name.isdecimal() else None
        if row is not None and row[2] == group:
            ticks += row[1]
            found = True
    return ticks / os.sysconf("SC_CLK_TCK") if found else None


def _cpu(pid: int) -> float | None:
    """Read the CPU of the suite's tree while its leader lives, else of its process group.

    Returns:
        the seconds, or None when nothing of the suite is left.

    """
    alive = tree_cpu(pid)
    return alive if alive is not None else group_cpu(pid)


_PROC = pathlib.Path("/proc")
_HOST_STATES = frozenset({"R", "D"})
_UNREADABLE = (-1, -1, "")


def _row(entry: pathlib.Path) -> tuple[int, int, str]:
    """Read one process's parent, process group and state letter from its `stat` file.

    Returns:
        (parent pid, process group, state letter), or `(-1, -1, "")` when the process is gone or
        unreadable, which is no process and never a runnable one.

    """
    try:
        text = (entry / "stat").read_text(encoding="utf-8", errors="replace")
        fields = text[text.rindex(")") + _AFTER_COMM :].split()
        return int(fields[_PPID]), int(fields[_PGRP]), fields[0]
    except (OSError, ValueError, IndexError):
        return _UNREADABLE


def waiting_on_host(root: int, proc: pathlib.Path = _PROC) -> bool:
    """Say whether any process of the suite is waiting on the HOST right now (state `R` or `D`).

    ⚑ A PROCESS WAITING ON THE HOST IS NOT STALLED (W2642, the same defect as W2632 in katas'
    waiter). The progress witness compares bytes and CPU between polls; on a busy host a live suite
    can be given no CPU for several polls and then read as hung. `R` is runnable and not yet run
    (the CPU scheduler); `D` is uninterruptible sleep, blocked on disk I/O (the I/O scheduler, a
    contended md0 or a reclaiming btrfs): github-cb's review, 2026-11-17. Neither is the opposite
    of an absence, so a poll in which any process of the suite's tree (or, once the leader has gone,
    its group) is in either state is never evidence of a stall. `S` stays countable: a suite asleep
    on its own futex or pipe with nothing waiting on the host is the genuine absence. This reads no
    clock: it is one reading of the process states.

    Returns:
        True when the root's tree, or its process group, holds a process in state `R` or `D`.

    """
    table = {int(entry.name): _row(entry) for entry in proc.iterdir() if entry.name.isdecimal()}
    members, pending = {root}, [root]
    while pending:
        parent = pending.pop()
        for pid, (ppid, _group, _state) in table.items():
            if ppid == parent and pid not in members:
                members.add(pid)
                pending.append(pid)
    members |= {pid for pid, (_ppid, group, _state) in table.items() if group == root}
    return any(table[pid][2] in _HOST_STATES for pid in members if pid in table)


def _drain(fd: int, chunks: list[bytes]) -> None:
    """Copy a pipe's read end into `chunks` as it arrives, until every writer has closed it.

    ⚑ THE READER ENDS ONLY AT EOF, so a descendant that outlives the suite and keeps the pipe open
    keeps the reader alive: exactly what made the old blocking read wait on a leaked child, and the
    two katas mutants that plant one (`child-shares-the-waiters-group`, `timeout-leaves-the-tree`)
    were recorded KILLED by it. The progress witness below is what now ends that wait.
    """
    while block := os.read(fd, _BLOCK):
        chunks.append(block)


def _hung(
    proc: subprocess.Popen[bytes],
    drains: tuple[tuple[list[bytes], threading.Thread], ...],
    watch: tuple[float, int],
    exited: threading.Event,
) -> bool:
    """Wait for the suite and its pipes to close, or end it when it shows no progress.

    ⚑ THIS LOOP DETECTS A HANG AND MEASURES NOTHING (W2805): the suite's CPU is read exactly by
    `reap`, from the kernel's own accounting at its exit, so no poll interval can shorten it.
    `exited` is set by `_watch_exit` when the leader has exited and is NOT yet reaped.

    ⚑ THE COUNT IS OF POLLS WITHOUT PROGRESS, NOT OF SECONDS: bytes received and CPU are read each
    poll, any change in either resets the count, and the suite's group is killed only when it
    reaches `patience`. The suite runs in its own session, so killing the group takes its
    descendants with it. After the leader has exited, silence with nothing computing counts too:
    that is a leaked child holding a pipe.

    Returns:
        True when the suite was hung and has been killed, False when it ended and its pipes closed.

    """
    poll, patience = watch
    still = 0
    last: tuple[int, float | None] | None = None
    while True:
        exited.wait(timeout=poll)
        ended = exited.is_set()
        if ended and not any(reader.is_alive() for _chunks, reader in drains):
            return False
        cpu = _cpu(proc.pid)
        seen = (sum(len(block) for chunks, _reader in drains for block in chunks), cpu)
        stalled = seen == last and (cpu is not None or ended) and not waiting_on_host(proc.pid)
        still = still + 1 if stalled else 0
        last = seen
        if still >= patience:
            # ⚑ AN EMPTY GROUP IS THE KILL ALREADY DONE (W1509). The leader can exit and its group
            # empty while a pipe is still held by a child that started its own session, and
            # `killpg` then raises ProcessLookupError out of the pool and crashes the whole grid.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            return True


def _watch_exit(pid: int, exited: threading.Event) -> None:
    """Block until the child has exited WITHOUT reaping it, then say so (W2805).

    ⚑ `WNOWAIT` LEAVES THE ZOMBIE FOR `reap`: the exit status and the resource usage are read once,
    by the one reaper, and `Popen` is never asked to wait.
    """
    with contextlib.suppress(ChildProcessError):
        os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
    exited.set()


def reap(proc: subprocess.Popen[bytes]) -> tuple[int, float]:
    """Reap the suite with `wait4` and read the CPU it and every descendant it waited for used.

    ⚑ EXACT AND PER SUITE, which a `RUSAGE_CHILDREN` delta is not once cells run concurrently, and
    which a polled peak is not either (a suite that burns CPU and exits between polls was lost,
    and one shard reserves 8 CPUs, so one poll interval can hide tens of CPU seconds).

    Returns:
        (the exit code, ru_utime + ru_stime of the suite and its waited-for descendants).

    """
    _pid, status, usage = os.wait4(proc.pid, 0)
    code = os.waitstatus_to_exitcode(status)
    proc.returncode = code
    return code, usage.ru_utime + usage.ru_stime


def _text(chunks: list[bytes]) -> str:
    """Join what a pipe delivered into text.

    Returns:
        the bytes, undecodable ones replaced.

    """
    return b"".join(chunks).decode("utf-8", errors="replace")


def launch(
    argv: list[str],
    cwd: pathlib.Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run one mutant's suite: argv only, no shell, output captured as text, ended by an absence.

    ⚑ ONE SEAM FOR THE ONE SUBPROCESS, so a test replaces THIS rather than `subprocess.run` for the
    whole interpreter — which also replaced the git its own fixture needed.

    ⚑⚑ THE SUITE RUNS IN ITS OWN SESSION AND THE WHOLE GROUP IS KILLED WHEN IT IS HUNG. Its output
    is read by two threads as it arrives, so the poll can see it grow, and the call returns only
    when the suite has exited AND every holder of its pipes has closed them, as a blocking read
    did before.

    Returns:
        the completed process; its status is read by `verdict`, never raised.

    Raises:
        subprocess.TimeoutExpired: when the suite was hung (no output and no CPU for the patience)
            or spent its CPU limit; the group is dead. It carries no wall-clock claim.

    """
    poll, patience, cpu_limit = limits()
    out: list[bytes] = []
    err: list[bytes] = []
    out_r, out_w = os.pipe()
    err_r, err_w = os.pipe()
    # ⚑ THE PIPES ARE MADE HERE, NOT BY POPEN, and Popen is not a `with`: its exit would close pipes
    # that a hung suite's leaked child still holds with a reader blocked inside `read`, and the
    # close would wait on that reader forever. The readers are daemon threads and a hung suite's
    # read ends are left to them.
    try:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=env, stdout=out_w, stderr=err_w, start_new_session=True
        )
    finally:
        os.close(out_w)
        os.close(err_w)
    with contextlib.suppress(ProcessLookupError):
        resource.prlimit(proc.pid, resource.RLIMIT_CPU, (int(cpu_limit), int(cpu_limit)))
    drains = (
        (out, threading.Thread(target=_drain, args=(out_r, out), daemon=True)),
        (err, threading.Thread(target=_drain, args=(err_r, err), daemon=True)),
    )
    for _chunks, reader in drains:
        reader.start()
    exited = threading.Event()
    threading.Thread(target=_watch_exit, args=(proc.pid, exited), daemon=True).start()
    hung = _hung(proc, drains, (poll, patience), exited)
    code, used = reap(proc)
    charge(used)
    if hung:
        raise subprocess.TimeoutExpired(argv, 0.0)
    os.close(out_r)
    os.close(err_r)
    if code == -signal.SIGXCPU:
        raise subprocess.TimeoutExpired(argv, cpu_limit)
    return subprocess.CompletedProcess(argv, code, _text(out), _text(err))


def _owned(tree: ast.Module) -> list[Site]:
    """Walk the module in source order, naming each def by its QUALIFIED path.

    ⚑⚑⚑ A BARE NAME IS NOT AN ADDRESS, AND THE GRID WAS ADDRESSING BY ONE. Sites were reported as
    `<module>::<name>` and each mutant mutated the FIRST def carrying that name, so two `parse`s
    in one module were two rows over ONE mutation. Measured on ratchet: a Protocol stub `parse`
    that nothing calls came back SURVIVED three times, because every `parse` mutated the stub
    and the implementations were never touched — counted, and never measured.
    ⚑⚑ THE PATH FOLLOWS PYTHON'S OWN `__qualname__`: `Class.method`, `outer.<locals>.inner`.
    ⚑ AND A PATH CAN STILL REPEAT — a property getter and setter are both `C.x`, and so are the
    two arms of an `if TYPE_CHECKING:` — so the n-th repeat (n >= 2) carries `#n`. The first
    keeps the bare path, which is what leaves a module of unique names reported as before.
    ⚑ THE WALK ITSELF IS `sitewalk.walk` under its GRID policy (W1761): one finder, shared with the
    declared-spec scope, so a rule about what is a site is stated once.

    Returns:
        the sites, each `(qualified path, node, owning class or None)`, in source order.

    """
    return walk(tree, GRID)


def sites(tree: ast.Module) -> list[tuple[str, FuncNode]]:
    """List every function definition in a parsed module, in source order, by qualified path.

    Returns:
        `(qualified path, FunctionDef)` pairs, nested defs included; every path is distinct.

    """
    return [(site.path, site.node) for site in _owned(tree)]


def import_time_sites(tree: ast.Module) -> set[str]:
    """Name the def-sites this operator structurally cannot reach, DERIVED from the source.

    ⚑⚑⚑ FOUND BY THE ERRORED CATEGORY ON ITS FIRST REAL RUN, which is the category existing to
    do exactly this. `BaselineState.__init__` and `__str__` errored on ratchet: `BaselineState`
    subclasses `enum.Enum`, so its members are constructed WHEN THE CLASS BODY EXECUTES —
    mutating them raises during import and no test ever collects.

    ⚑⚑ SO IT IS A LIMIT OF THE OPERATOR, NOT A DEFECT IN THE SUITE, and the two are easy to
    confuse because both read as *the suite did not notice*. A silent skip would erase the
    distinction; an unexplained ERRORED would report a limit as a finding. Declaring it keeps
    both legible, and the arm below still counts these in ATTEMPTED.

    ⚑ THE PREDICATE IS STRUCTURAL RATHER THAN A NAME LIST. Matching `__init__` by name would
    also exclude every ordinary class's constructor, which IS reachable — over-declaring the
    limit to cover two real cases. Measured across the tree: 158 def-sites, exactly 2 in this
    class, both the ones ERRORED named. The derivation admits a new enum method for free.

    ⚑⚑ AND THE SET IS OF QUALIFIED PATHS, as `sites` now reports. It returned BARE names while
    this docstring promised `<Class>.<method>`, so an enum's `__str__` also skipped every other
    class's `__str__` in the same module — the same bare-name collision as the mutation itself.

    Returns:
        `"<Class>.<method>"` for every method of an `Enum` subclass in this module.

    """
    return {
        site.path
        for site in _owned(tree)
        if site.owner is not None and {ast.unparse(b) for b in site.owner.bases} & _ENUM_BASES
    }


def mutate(source: str, target: str) -> str:
    """Replace one def-site's body with a bare raise, leaving the rest of the module alone.

    ⚑ THE DOCSTRING IS KEPT so the mutant stays syntactically a function with a body. Replacing
    everything including the docstring would change two things under one label, and a mutant that
    alters more than its operator claims cannot support a conclusion about that operator.

    ⚑⚑ `target` IS A QUALIFIED PATH FROM `sites`, NOT A BARE NAME: a bare name picked the first
    same-named def, so every other one was reported and never mutated.

    Returns:
        the module source with `target` mutated.

    Raises:
        LookupError: when no def-site carries that path.

    """
    tree = ast.parse(source)
    for path, node in sites(tree):
        if path != target:
            continue
        keep = (
            node.body[:1]
            if (
                isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            else []
        )
        raiser = ast.parse('raise AssertionError("mutant")').body
        node.body = [*keep, *raiser]
        return ast.unparse(ast.fix_missing_locations(tree))
    msg = f"no def-site at {target}"
    raise LookupError(msg)


def verdict(rc: int, stdout: str) -> str:
    """Sort one mutant run into `killed`, `survived` or `errored` — three outcomes, not two.

    ⚑⚑⚑ THE PREDECESSOR WAS `killed if rc else survived`, AND IT CREDITED THE SUITE FOR NOTICING
    THINGS IT NEVER RAN. A mutant that cannot import returns non-zero and was recorded as KILLED.
    Its `errored` list was bound, printed in the report, and never appended to — a POPULATION
    NEVER POPULATED, inside the instrument built to find exactly that.

    ⚑⚑ AND THE OBVIOUS REPAIR DOES NOT WORK, MEASURED, BECAUSE I ASSUMED IT WOULD. pytest's exit
    codes are documented as separating tests-failed (1) from internal error (3) and
    no-tests-collected (5), so keying on `rc` looked right. Across four shapes:

        unmutated control            rc=0   `151 passed`
        body -> raise (a real KILL)  rc=1   `1 failed`
        unparseable module           rc=1   `1 error`
        import-time raise            rc=1   `1 error`

    **All three non-zero cases return rc=1** — pytest reports a collection error as `1 error`
    rather than with a distinct code. THE EXIT STATUS CANNOT CARRY THIS DISTINCTION, and a repair
    keying on it would have been a second wrong answer wearing a measurement's clothes.

    ⚑ SO THE DISCRIMINATOR IS THE TERMINAL SUMMARY LINE. Weaker than an exit code and the one that
    exists — an honest `error` beats a confident `rc`.

    Returns:
        one of `"killed"`, `"survived"`, `"errored"`.

    """
    if rc == 0:
        return "survived"
    # ⚑⚑⚑ THE FIRST PREDICATE HERE WAS TOO BROAD AND ITS OWN CATEGORY CAUGHT IT. It read *any*
    # collection error as ERRORED, on a four-shape measurement where every error was an import
    # failure. Run against `fence`, three ordinary functions errored — and the traceback showed
    # the suite calling them AT COLLECTION TIME, through a module-level `_WHY = _unfenceable()`
    # guard that decides whether to skip. The suite's own code ran and REACHED the mutant.
    # ⚑⚑ SO THE DISTINCTION IS NOT *DID COLLECTION FINISH* BUT **WAS THE MUTANT REACHED**, which
    # is the question the whole grid asks. A mutant in the traceback was executed; the suite
    # noticed it, and where it noticed is not the measurement. That is a KILL.
    # ⚑ AND THE EXIT CODE WAS rc=2 HERE, a shape the original four-case measurement never
    # produced — a reminder that a predicate is only as wide as the corpus it was measured on.
    if "AssertionError: mutant" in stdout or "AssertionError('mutant')" in stdout:
        return "killed"
    # ⚑ THE LAST NON-EMPTY LINE IS pytest's SUMMARY under `-q`. Scanning the whole stdout would
    # also match the word `error` inside the traceback of a genuine FAILURE.
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    summary = lines[-1] if lines else ""
    # ⚑⚑ `failed` WINS OVER `error` WHEN BOTH APPEAR, and that case decides the predicate's shape:
    # `1 failed, 1 error` means the suite RAN and something failed, which is a kill. Without it,
    # `" error" in summary` alone would be sufficient and would misclassify.
    if " error" in summary and " failed" not in summary:
        return "errored"
    return "killed"


def _report_debug(proc: subprocess.CompletedProcess[str]) -> None:
    """Print what one mutant's suite said, for `--debug`."""
    tail = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1:]
    reached = "AssertionError: mutant" in proc.stdout
    sys.stdout.write(
        f"      rc={proc.returncode} mutant_in_stdout={reached} "
        f"summary={tail[0] if tail else '<none>'!r}\n"
    )
    if proc.stderr.strip():
        sys.stdout.write(f"      stderr: {proc.stderr.strip().splitlines()[-1]}\n")
    # ⚑ WHEN THE MUTANT NEVER APPEARS, THE INTERESTING TEXT IS THE ERROR ITSELF — the
    # suite failed BEFORE reaching mutated code, so the summary line says nothing about
    # the mutation and everything about the environment.
    if not reached:
        for ln in proc.stdout.splitlines():
            if "Error" in ln or "error" in ln.lower():
                sys.stdout.write(f"      | {ln.strip()[:160]}\n")


def selected_tests(dist: pathlib.Path, rel: pathlib.Path) -> list[str]:
    """Pick the test files that can see a mutation of module `rel`, from the dist's import graph.

    ⚑ EVERY MUTANT USED TO RUN THE WHOLE `tests` DIRECTORY (W1519): `-x` stops at the first failure,
    so a kill was quick only if the killing test sorted early, and a survivor ran everything. With
    `graph.json` (importdag, W1503) a test can see a module when the module is in the test's import
    cone, or the test declares it reads the file; only those files are run.

    ⚑ NO GRAPH, NO NARROWING. A distribution without a readable `graph.json`, or whose graph does
    not name the module, runs everything exactly as before: an unknown is never read as "no test
    needs this", because that would turn a kill into a survivor and fail the grid for no defect.

    Returns:
        the dist-relative test paths, sorted, or an empty list meaning the whole `tests` directory.

    """
    graph = _graph(dist)
    if graph is None:
        return []
    modules, tests = graph
    target = str(rel)
    if target not in modules:
        return []
    chosen = [
        path
        for path, entry in tests.items()
        if target in entry.get("reads", []) or target in _cone(entry.get("imports", []), modules)
    ]
    return sorted(chosen)


def chosen_tests(dist: pathlib.Path, rel: pathlib.Path, declared: str) -> list[str]:
    """Pick the tests a mutation of `rel` runs: the declared list, else the graph's selection.

    ⚑ A PER-SITE TARGET NAMES ITS TESTS AND STAGES NO `graph.json` (W1883). The graph changes
    whenever any test or module gains an import, and a target that staged it would rerun for
    every such change; the generator computes the list once and writes it into the target's own
    BUILD file, so only the targets whose list changed rerun. `MUTATE_TESTS` is that list,
    space-separated dist-relative paths; unset or blank is the graph's answer as before.

    Returns:
        the dist-relative test paths, or an empty list meaning the whole `tests` directory.

    """
    return declared.split() if declared.strip() else selected_tests(dist, rel)


def _graph(
    dist: pathlib.Path,
) -> tuple[dict[str, dict[str, list[str]]], dict[str, dict[str, list[str]]]] | None:
    # The dist's modules and tests from `graph.json`, or None when it is absent or not a mapping.
    try:
        doc: object = json.loads((dist / "graph.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict):
        return None
    parts = cast("dict[str, object]", doc)
    return _entries(parts, "modules"), _entries(parts, "tests")


def staged_files(dist: pathlib.Path, rel: pathlib.Path) -> tuple[list[str], list[str]] | None:
    """Name the files a per-site target must stage to mutate module `rel` (W1883).

    ⚑ EXACTLY WHAT A CHANGE CAN MOVE, NO MORE: the module, the import cone of every test that can
    see it, and those tests. A target that stages these reruns when one of them changes and hits the
    cache when anything else does, which is the point of one target per site (W1833).

    ⚑ THE SAME UNKNOWN AS `selected_tests`: no graph, or a module it does not name, is None, and the
    caller stages the whole distribution rather than guess that nothing else matters.

    Returns:
        `(sources, tests)`, dist-relative and sorted; None when the graph cannot narrow it.

    """
    graph = _graph(dist)
    chosen = selected_tests(dist, rel)
    if graph is None or not chosen:
        return None
    modules, tests = graph
    cone: set[str] = {str(rel)}
    for path in chosen:
        cone |= _cone(tests[path].get("imports", []), modules)
    return sorted(cone), chosen


def _entries(doc: dict[str, object], key: str) -> dict[str, dict[str, list[str]]]:
    # One section of the graph file, or an empty one when it is absent or not a mapping.
    got = doc.get(key)
    return cast("dict[str, dict[str, list[str]]]", got) if isinstance(got, dict) else {}


def _cone(roots: list[str], modules: dict[str, dict[str, list[str]]]) -> set[str]:
    # Every module reachable from `roots` along import edges, the roots included.
    seen: set[str] = set()
    todo = list(roots)
    while todo:
        name = todo.pop()
        if name not in seen:
            seen.add(name)
            todo.extend(modules.get(name, {}).get("imports", []))
    return seen


def run(grid: Grid, mutant: Mutant, *, debug: bool = False) -> str:
    """Build one mutant in a temp copy of the distribution and run its suite against it.

    Returns:
        this mutant's verdict.

    """
    return _run_text(grid, mutant.rel, mutate(mutant.source, mutant.name), debug=debug)


def cpu_mark() -> float:
    """Read the CPU seconds this process and the children it has reaped have used so far.

    Returns:
        user plus system CPU of this process and its reaped children.

    """
    spent = os.times()
    return spent.user + spent.system + spent.children_user + spent.children_system


def report_phase(label: str, since: float) -> None:
    """Print the CPU a phase of one mutant used, when `MUTATE_PHASES` is set (W2458).

    ⚑ A MEASUREMENT BEFORE A DESIGN: the hooks shards use 1.5x to 2.5x the CPU they did, and a
    per-module prepare target is only worth building if the cost is per shard. With one worker per
    shard (`children=1`) the delta since `cpu_mark` is the phase's own cost. Unset, it prints
    nothing.
    """
    if os.environ.get("MUTATE_PHASES"):
        sys.stdout.write(f"      phase {label}: {cpu_mark() - since:.2f}s cpu\n")


class ScratchTreeHeldError(Exception):
    """A cell's temp tree could not be removed although every holder had been ended (W2694).

    It carries the tree and the processes still naming it, and `run_all` records it against the cell
    as an INFRASTRUCTURE failure: never a mutant verdict, and never a shard that dies unnamed.
    """

    def __init__(self, root: pathlib.Path, remaining: list[int]) -> None:
        """Name the tree and the pids that still hold it."""
        super().__init__(f"{root} could not be removed; processes still holding it: {remaining}")
        self.root = root
        self.remaining = remaining


def holders(root: pathlib.Path, proc: pathlib.Path = _PROC) -> list[int]:
    """Name every live process whose environment mentions `root`, read from `/proc`.

    ⚑ A CELL'S TREE NAMES ITSELF IN ITS DESCENDANTS' ENVIRONMENT (W2694): `HOME` and `PYTHONPATH`
    are set to it, a random directory no other cell shares, so a process carrying it belongs to this
    cell however many sessions it has started since. The suite's process GROUP is not enough: a
    child the suite started in its own session (the katas waiter does, and the mutant
    `timeout-leaves-the-tree` leaves it alive) is in no group the runner holds. The match ends at a
    path separator, a colon, the end of an entry or the end of the data, so a sibling tree whose
    name merely begins the same is not a holder.

    Returns:
        the pids, never this process's own; a process whose environment cannot be read (gone,
        another user's, a zombie) is not named.

    """
    needle = re.compile(re.escape(os.fsencode(root)) + rb"(?=[/:\x00]|$)")
    found: list[int] = []
    for entry in proc.iterdir():
        if not entry.name.isdecimal() or int(entry.name) == os.getpid():
            continue
        try:
            environ = (entry / "environ").read_bytes()
        except OSError:
            continue
        if needle.search(environ):
            found.append(int(entry.name))
    return sorted(found)


_SYS_PIDFD_SEND_SIGNAL = 424
_SYS_PIDFD_OPEN = 434
# ⚑ THE PINNED PYTHON (3.13.13, hooks' own and bazel's) HAS NEITHER `os.pidfd_open` NOR
# `signal.pidfd_send_signal`: its build predates them, and 3.14 has both. The kernel does, and the
# two syscall numbers are the same on x86_64, arm64 and riscv, so they are called directly. Measured
# 2026-11-18: 3.13.13 `hasattr` False for both, the raw `pidfd_open` on this process answers a fd.
# ⚑ THIS SHIM IS DEBT THAT EXISTS ONLY BECAUSE OF THE 3.13 PIN, which breaks the fleet's 3.14 floor
# (operator rows 69229 and 170277). It is DELETED by mtools:W2721, blocked on W2422 (the move of the
# toolchain and every hub to 3.14): `_end` then calls the two `os`/`signal` wrappers directly.


class _Syscall(Protocol):
    """The shape of libc's `syscall`: a number and integer arguments, a signed result."""

    def __call__(self, number: int, /, *args: int) -> int:
        """Make the call."""
        ...


_SYSCALL = cast("_Syscall", ctypes.CDLL(None, use_errno=True).syscall)


def _syscall(number: int, *args: int) -> int:
    """Call one raw syscall, raising the `OSError` its errno names when it answers -1.

    Returns:
        the syscall's non-negative result.

    Raises:
        OSError: the syscall failed; `ProcessLookupError` for ESRCH, as the wrappers raise.

    """
    got = _SYSCALL(number, *args)
    if got < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return got


def _end(pid: int) -> None:
    """Kill one process through a pidfd and block until it has exited.

    ⚑ SIGKILL IS ASYNCHRONOUS: a signalled process can still run until the kernel delivers it, and
    it is not gone until it has exited. The pidfd names THIS process, so a pid reused in between
    cannot be hit, and it becomes readable exactly when the process exits, so the wait is the
    event itself and needs no timeout and no polling interval.
    """
    try:
        fd = _syscall(_SYS_PIDFD_OPEN, pid, 0)
    except ProcessLookupError:
        return
    try:
        with contextlib.suppress(ProcessLookupError):
            _syscall(_SYS_PIDFD_SEND_SIGNAL, fd, signal.SIGKILL, 0, 0)
        wait_readable([fd], [], [])
    finally:
        os.close(fd)


def end_holders(root: pathlib.Path, proc: pathlib.Path = _PROC) -> None:
    """Kill every process holding `root` and wait for each to exit, until a scan finds none.

    ⚑ A CELL ENDS WHEN ITS SUITE'S DESCENDANTS DO, not when its leader does. `launch` returns when
    the leader has exited and its pipes have closed; a leaked grandchild that holds neither is
    still running, and it can write into the tree while the tree is removed (W2694).

    ⚑ THE LOOP ENDS WITHOUT A COUNTED LIMIT, AND THAT IS THE PROOF. Each pass ends every process it
    named and waits for it to exit; a holder can only be started by a holder that was alive, so the
    set of live holders strictly runs out. When a scan finds none, no process of the cell is
    running, so nothing can write into the tree: the remover starts after every writer has exited.
    """
    while pids := holders(root, proc):
        for pid in pids:
            _end(pid)


def discard(root: pathlib.Path, proc: pathlib.Path = _PROC) -> None:
    """Remove a mutant's temp tree ONCE; raise `ScratchTreeHeldError` if that fails.

    ⚑ THE REMOVAL HAS NO CONCURRENT WRITER, so it is one `rmtree` and a failure is a fact, not a
    race to retry: a retry or `ignore_errors` here would hide a broken `end_holders` (W2694).
    `TemporaryDirectory` raised ENOTEMPTY out of the pool and one cleanup took b89's
    `//katas:mutants_4` down with no cell named. The error names the tree and what still holds it;
    `run_all` records it against the cell. A tree is never left in place silently: the tmp tier is
    shared memory, and an unnamed leftover is a capacity leak.

    Raises:
        ScratchTreeHeldError: the tree could not be removed; it names the tree and the holders.

    """
    try:
        shutil.rmtree(root)
    except OSError as err:
        raise ScratchTreeHeldError(root, holders(root, proc)) from err


class _ScratchTree:
    """The temp tree one mutant runs in: made on entry, emptied of its holders and removed on exit.

    Entering yields the directory's name, as `tempfile.TemporaryDirectory` did, so the body that
    used that context manager reads the same.
    """

    def __init__(self) -> None:
        self._root = pathlib.Path(tempfile.mkdtemp())

    def __enter__(self) -> str:
        return str(self._root)

    def __exit__(self, *_exc: object) -> None:
        end_holders(self._root)
        discard(self._root)


_QUIET_GIT = (("maintenance.auto", "false"), ("gc.auto", "0"))
"""The git settings a cell's suite runs under: no detached background maintenance, no auto gc."""


def quiet_git(env: dict[str, str]) -> dict[str, str]:
    """Add the settings that stop git starting background maintenance, through its own env config.

    ⚑ A FIXTURE'S `git commit` MUST NOT START A PROCESS THE SUITE DOES NOT OWN (W2724). `git commit`
    can start detached `git maintenance run --auto`, which creates and removes
    `objects/maintenance.lock`; a fixture that then copies the repository races it, and under gate
    load the lock vanishes between the listing and the copy. b91 was refused at `//hooks:mutants_39`
    by exactly that on an UNMUTATED control. Nondeterminism in every test that runs git, so it is
    set where every cell's environment is made, by the runner.

    ⚑ THE RUNNER SETS THIS, SO NOTHING RELIES ON A VARIABLE SURVIVING FROM A CALLER. `clean_env`
    strips every `GIT_*` the caller passed (W619, hook redirections that point a suite at the real
    repository); this is config injection by the runner itself, which that rule does not cover. An
    environment that already names a `GIT_CONFIG_COUNT` is appended to, never overwritten.

    Returns:
        a copy of `env` with the settings added after any it already carried.

    """
    raw = env.get("GIT_CONFIG_COUNT", "")
    start = int(raw) if raw.isdecimal() else 0
    added: dict[str, str] = {}
    for offset, (key, value) in enumerate(_QUIET_GIT):
        added[f"GIT_CONFIG_KEY_{start + offset}"] = key
        added[f"GIT_CONFIG_VALUE_{start + offset}"] = value
    return {**env, **added, "GIT_CONFIG_COUNT": str(start + len(_QUIET_GIT))}


def _run_text(grid: Grid, rel: pathlib.Path, text: str, *, debug: bool = False) -> str:
    """Write `text` over module `rel` in a temp copy of the distribution and run its suite there.

    ⚑ ONE PLACE FOR BOTH OPERATORS: a def-site mutant (`run`) and a declared regex defect
    (`run_declared`) differ only in the text they put on the module, so the isolation, the
    environment and the time limit below are written once and cannot drift apart.

    Returns:
        this mutant's verdict.

    """
    with _ScratchTree() as tmp:
        work = pathlib.Path(tmp) / grid.dist.name
        mark = cpu_mark()
        shutil.copytree(grid.dist, work, ignore=_not_source)
        mirror_siblings(grid.dist, pathlib.Path(tmp))
        (work / rel).write_text(text, encoding="utf-8")
        report_phase("copy", mark)
        # ⚑ THE SYNTHESIZED PACKAGE MARKERS GO, for the reason `mypy_check.sh` records: rules_python
        # writes an empty `__init__.py` at every runfiles level, including the `src/mikemol/` one
        # PEP 420 forbids here. Only the EMPTY ones — a hand-written package `__init__.py` has
        # content and is part of the distribution.
        for marker in work.rglob("__init__.py"):
            if marker.stat().st_size == 0:
                marker.unlink()
        # ⚑⚑⚑ `PATH` IS INHERITED, AND STRIPPING IT REPORTED A WHOLE DISTRIBUTION AS UNMEASURABLE.
        # A first cut pinned `PATH=/usr/bin:/bin` for hermeticity. MEASURED: all 64 of mdstruct's
        # def-sites came back ERRORED, because `pandoc` lives at `~/bin/pandoc` and its suite
        # shells out to it — so every mutant failed for a reason that had nothing to do with the
        # mutation. The predecessor probe carried the same strip, which is why the recorded
        # mdstruct figures only ever covered `cli.py`, the one module whose arms do not need it.
        # ⚑⚑ AND THE ERRORED CATEGORY IS WHAT MADE THAT VISIBLE RATHER THAN FLATTERING. Under the
        # old two-outcome verdict every one of those 64 would have been recorded as KILLED — a
        # distribution reported as fully covered by a grid that never ran a single test.
        # ⚑ THE HERMETIC ANSWER IS THE SANDBOX, NOT A PINNED `PATH`. Under bazel the tools are
        # declared inputs and `PATH` is the sandbox's; here the environment is the caller's, and
        # a probe that silently loses a host tool is worse than one that inherits it.
        # ⚑ THE TEMP `src` IS PREPENDED, NOT SUBSTITUTED, so the mutant wins over the installed
        # copy while every other resolution path stays intact — which is what makes the mutation
        # the only difference between this run and a clean one.
        # ⚑⚑ AN EARLIER COMMENT HERE CLAIMED THIS COMPOSITION WAS *THE* DEFECT BEHIND 64 ERRORED
        # MUTANTS. IT WAS NOT, and the claim is corrected rather than deleted because a refuted
        # cause left standing is read as an established one. Measured: `PYTHONPATH` set to the
        # temp tree alone, prepended, or absent made NO difference — all three produced the same
        # result. The cause was `.resolve()` on the interpreter (see `main`).
        # ⚑⚑⚑ EVERY `GIT_*` VARIABLE IS DROPPED, BECAUSE A MUTANT'S SUITE CAN WRITE INTO THE
        # CALLER'S REPOSITORY. Under a git hook `GIT_DIR` and `GIT_INDEX_FILE` name the REAL repo,
        # and a fixture that runs `git init; git commit` in its temp dir follows them there — `cwd=`
        # does not override an exported `GIT_DIR`. Measured 2026-09-23: nine junk commits,
        # since recovered.
        # ⚑ fence's `git_env.clean_env()` rule (W619: imported), at the runner, so suites not yet
        # written are covered too. A suite reading git state finds the repository from its `cwd`
        # as before.
        env = quiet_git(clean_env())
        existing = env.get("PYTHONPATH", "")
        src = str(work / "src")
        env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}" if existing else src
        env["HOME"] = tmp
        # ⚑ NO `PYTHONHOME` (W2340, MEASURED): bazel's launcher exports one naming its hermetic
        # 3.13, and every OTHER interpreter a suite starts (fence's payload is the host `python3`,
        # 3.14) then fails at startup with "Python path configuration" and exit 1. The suite's own
        # interpreter is a venv that finds its home from pyvenv.cfg, so it needs none.
        env.pop("PYTHONHOME", None)
        absolute_tools(env, grid.dist.parent)
        site = portable_python(grid.py)[1]
        if site:
            env["PYTHONPATH"] = os.pathsep.join([env["PYTHONPATH"], site])
        # ⚑ THE CONFIG IS THE TEMP TREE'S OWN COPY. Passing the REAL `pyproject.toml` sets pytest's
        # rootdir to the real distribution while `cwd` is the temp copy, so reported paths climb
        # out of the tree under measurement. Naming the copy keeps rootdir and cwd agreeing.
        # ⚑⚑ AN EARLIER COMMENT HERE ALSO CLAIMED TO BE *THE* DEFECT. IT WAS NOT EITHER — changing
        # it moved the error path from `../../../github/mtools/mdstruct/test_cli_flags.py` to
        # `tests/test_cli_flags.py` and the failure followed rather than disappearing. Correct on
        # its own merits, and not the cause. **Two comments in this file each announced themselves
        # as the defect and both were wrong**, which is why the real one below states what it
        # RULED OUT alongside what it found.
        # ⚑ `shutil.copytree` ALREADY BRINGS `pyproject.toml` ACROSS, so this names the copy
        # rather than adding a file: the fix is which path is passed, not what exists.
        # ⚑⚑ A SUITE THAT OUTLIVES THE LIMIT IS A KILL: it did not pass, and the only code that
        # differs from a clean run is the mutant, so the mutant is what it noticed.
        mark = cpu_mark()
        try:
            tests = chosen_tests(work, rel, os.environ.get("MUTATE_TESTS", ""))
            (work / PLUGIN_FILE).write_text(NODE_PLUGIN, encoding="utf-8")
            proc = _launch_suite(grid, work, env, tests, work / REPORT_FILE)
            report_phase(f"suite ({len(tests)} chosen)", mark)
        except subprocess.TimeoutExpired:
            report_phase("suite (ended)", mark)
            if debug:
                sys.stdout.write("      ended with no progress or over its CPU limit\n")
            return "killed"
        if debug:
            _report_debug(proc)
        result = verdict(proc.returncode, proc.stdout)
        if result == "killed" and _baseline_fails(grid, (work, rel), env, work / REPORT_FILE):
            return "errored"
        return result


REPORT_FILE = "mutate-nodes.jsonl"
"""The file each mutant's suite writes its failed node ids to, in its own tree (W2769)."""

PLUGIN_FILE = "_mutate_nodes.py"
"""The plugin the runner writes into each mutant's tree and loads with `-p`."""

NODE_PLUGIN = """\
import json
import os


def pytest_sessionstart(session):
    if not hasattr(session.config, 'workerinput'):
        open(os.environ['MUTATE_NODES'], 'w', encoding='utf-8').close()


def pytest_runtest_logreport(report):
    if report.failed:
        with open(os.environ['MUTATE_NODES'], 'a', encoding='utf-8') as out:
            out.write(json.dumps(report.nodeid) + chr(10))
"""
"""A pytest plugin that CREATES `$MUTATE_NODES` at session start and appends each failed test's id.

⚑ THE FILE EXISTS ONLY IF THE PLUGIN RAN. A report that is missing therefore means the instrument
did not load, which is different from a suite that ran and failed no test (an empty file).
"""

CONTROL_REPORT_FILE = "mutate-control-nodes.jsonl"
"""Where the control launch's plugin writes: the control's failures come from structure too."""


class NodeReportError(Exception):
    """The node report cannot be trusted, so the cell is ERRORED and the reason is named."""


class NodeReportMissingError(NodeReportError):
    """The report file does not exist: the plugin never ran in that suite."""


class NodeReportMalformedError(NodeReportError):
    """A line the plugin wrote does not parse as a node id: a broken instrument, not a non-test."""


def failing_nodes(report: pathlib.Path) -> list[str]:
    """Read the pytest node ids that failed, from the report the runner's plugin wrote (W2769).

    ⚑⚑ THE ID COMES FROM pytest ITSELF, NOT FROM ITS HUMAN OUTPUT. The control used to take the
    first `^FAILED ` line of the suite's text, and a suite that prints its own `FAILED` lines for
    items that are not tests (pytestspec's spec items: `spec.rego::p`) handed the control an id
    pytest cannot collect. It collected nothing (exit 5), the kill was read as unvouched and the
    cell was ERRORED: a verdict that depended on which line came first, so it flipped between runs
    of one tree (measured 2026-11-19, `//pytestspec:mutants_1`, mtools:W2769).
    ⚑ A TEST NODE IS A `.py` FILE'S CASE. A failure whose file is not Python source (a spec item)
    is not one; it is left out rather than named.

    ⚑ ABSENCE MEANS ONE THING (github-00 R1). The plugin creates the file at session start, so a
    missing file is a plugin that never loaded and a line that does not parse is a broken
    instrument: both raise, and neither reads as "no test failed".

    Returns:
        the failing test ids in the order they failed; empty when the suite ran and no test in a
        Python file failed.

    Raises:
        NodeReportMissingError: the report file does not exist.
        NodeReportMalformedError: a line is not a JSON string.

    """
    try:
        lines = report.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        msg = f"the node report {report.name} is missing: the plugin did not run in that suite"
        raise NodeReportMissingError(msg) from error
    nodes: list[str] = []
    for line in lines:
        try:
            node: object = json.loads(line)
        except ValueError as error:
            msg = f"the node report {report.name} has a line that is not JSON: {line[:80]!r}"
            raise NodeReportMalformedError(msg) from error
        if not isinstance(node, str):
            msg = f"the node report {report.name} has a line that is not a node id: {line[:80]!r}"
            raise NodeReportMalformedError(msg)
        if node.partition("::")[0].endswith(".py"):
            nodes.append(node)
    return nodes


def _baseline_fails(
    grid: Grid, tree: tuple[pathlib.Path, pathlib.Path], env: dict[str, str], report: pathlib.Path
) -> bool:
    """Say whether the test that killed a mutant also fails on the UNMUTATED module (W2340).

    ⚑⚑ A KILL IS ONLY AS GOOD AS ITS BASELINE. The runner had no control run, so a test that
    fails on the clean tree for a reason of the environment (a tool version that differs from
    the lock's, a copy that cannot be made in the temp tree) killed EVERY mutant it ran
    before, and each read as a kill (measured 2026-11-07: two such tests in a local
    whole-suite run). The failing test named in the output is put back against the original
    module and run alone; one that still fails proves nothing about the mutant, so the cell is
    ERRORED, never killed. The answer is kept per test id, so a run asks it once per test.

    ⚑ A CONTROL THAT PROVES NOTHING DOES NOT VOUCH FOR THE KILL (B2): one that times out, or
    that collects no test (exit 5), is read as a baseline that could not be checked, never as
    a baseline that passes.

    Returns:
        True when the named test fails on the unmutated module, or the control timed out or
        collected nothing; False when it passes there or when the output names no failing test.

    """
    try:
        named = failing_nodes(report)
    except NodeReportError as error:
        # ⚑ A BROKEN INSTRUMENT CANNOT VOUCH FOR A KILL: the cell is ERRORED and says why.
        sys.stdout.write(f"      control: {error}\n")
        return True
    if not named:
        return False
    test = named[0]
    if test not in _CONTROLS:
        work, rel = tree
        (work / rel).write_text((grid.dist / rel).read_text(encoding="utf-8"), encoding="utf-8")
        for cache in work.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
        try:
            control = _launch_suite(grid, work, env, [test, "-vvv"], work / CONTROL_REPORT_FILE)
        except subprocess.TimeoutExpired:
            # ⚑ A CONTROL THAT CANNOT RUN PROVES NOTHING (github-cb, B2 of the b66 review): the
            # kill is not vouched for, so the cell is ERRORED. NOT CACHED: the next mutant killed
            # by this test may get an answer.
            sys.stdout.write(f"      control: {test} timed out on the UNMUTATED module\n")
            return True
        _CONTROLS[test] = control.returncode != 0
        if _CONTROLS[test]:
            said = (
                "collected no test" if control.returncode == _NO_TESTS_COLLECTED else "also fails"
            )
            sys.stdout.write(f"      control: {test} {said} on the UNMUTATED module\n")
            sys.stdout.write(f"        | interpreter {portable_python(grid.py)} from {grid.py}\n")
            payload = shutil.which("python3", path=env.get("PATH"))
            sys.stdout.write(f"        | python3 on the suite's PATH: {payload}\n")
            sys.stdout.write(f"        | cgroup: {_own_cgroup()}\n")
            if payload:
                start = subprocess.run(
                    [payload, "-c", "pass"], env=env, capture_output=True, text=True, check=False
                )
                said = start.stderr.strip()[:300]
                sys.stdout.write(f"        | python3 -c pass: rc={start.returncode} {said}\n")
            lines = [ln for ln in control.stdout.splitlines() if ln.strip()]
            for line in ([ln for ln in lines if ln.lstrip().startswith("E ")] or lines)[:40]:
                sys.stdout.write(f"        | {line.strip()[:480]}\n")
    return _CONTROLS[test]


def _own_cgroup() -> str:
    """Read this process's cgroup line, so a failed control names the host it ran on.

    Returns:
        The `/proc/self/cgroup` text, or the reason it could not be read.

    """
    try:
        return pathlib.Path("/proc/self/cgroup").read_text(encoding="utf-8").strip()
    except OSError as error:
        return f"unreadable: {error}"


_MIRRORS: dict[str, pathlib.Path] = {}
"""The one copy of a runfiles root's siblings, per process and root (W2340, B3)."""


def _link_or_copy(src: str, dst: str) -> str:
    """Hard-link `src` as `dst`, or copy it when the two cannot share an inode.

    Returns:
        `dst`, as `shutil.copytree`'s copy function must.

    """
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
    return dst


def _sibling_mirror(dist: pathlib.Path) -> pathlib.Path | None:
    """Copy what sits beside `dist` in the runfiles root ONCE and name the copy.

    Returns:
        the directory holding the one copy, or None outside bazel (no `TEST_SRCDIR`, or `dist` not
        inside it), where the parent is a whole checkout and nothing needs mirroring.

    """
    runfiles = os.environ.get("TEST_SRCDIR", "")
    if not runfiles or not dist.resolve().is_relative_to(pathlib.Path(runfiles).resolve()):
        return None
    key = str(dist.parent)
    if key not in _MIRRORS:
        root = pathlib.Path(tempfile.mkdtemp(prefix="mutate-siblings-"))
        atexit.register(shutil.rmtree, root, ignore_errors=True)
        for entry in dist.parent.iterdir():
            if entry.name == dist.name or entry.name in _NOT_SOURCE_PATTERNS:
                continue
            if entry.is_dir():
                shutil.copytree(entry, root / entry.name, ignore=_not_source)
            else:
                shutil.copy2(entry, root / entry.name)
        _MIRRORS[key] = root
    return _MIRRORS[key]


def mirror_siblings(dist: pathlib.Path, into: pathlib.Path) -> None:
    """Put what sits beside `dist` in the runfiles root beside a mutant's temp tree.

    ⚑ A suite resolves the repository root as its tree's PARENT (`_DIST.parent`) and reads the
    sibling distributions' build files and the root's scripts from it. The mutation copy was a
    lone `dist` directory, so those tests failed on the UNMUTATED module (W2340). Under bazel
    (`TEST_SRCDIR` set, `dist` inside it) the other entries of the runfiles root are copied ONCE
    per process (`_sibling_mirror`) and HARD-LINKED into each mutant's tree, a copy only where a
    link cannot be made, so a shard's I/O is not the size of the runfiles root times its mutants
    (github-cb, B3 of the b66 review).
    ⚑ A HARD LINK, NOT A SYMLINK: this repository does not create links (operator 2026-10-02), and
    a hard link is a name for the same bytes, not a pointer that a test can read through to the
    wrong place. COST NAMED: a hard link shares the inode, so a test that WROTE INTO a sibling file
    in place would change the shared copy for later mutants; the siblings are read, never mutated.
    """
    root = _sibling_mirror(dist)
    if root is None:
        return
    for entry in root.iterdir():
        target = into / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target, copy_function=_link_or_copy)
        else:
            _link_or_copy(str(entry), str(target))


def absolute_tools(env: dict[str, str], base: pathlib.Path) -> None:
    """Make the tool paths a suite is given point at the real files, not at a path under `base`.

    ⚑ A target hands its tests `RUFF_BIN` and `OPA_BIN` as paths relative to the runfiles root
    (`$(location ...)`), and a test resolves them against ITS OWN tree's parent. The mutation
    copy is a temp tree, whose parent is not that root, so the relative path found nothing and
    the test failed on the UNMUTATED module (W2340). Every value that is a relative path to a
    FILE under `base` is made absolute here (`RUFF_BIN`, `OPA_BIN`, `CONTROL_RUFF`, ...); the
    copy sees the same file the target staged.
    """
    for key, value in list(env.items()):
        if not value or " " in value or pathlib.Path(value).is_absolute():
            continue
        try:
            found = (base / value).resolve()
            is_file = found.is_file()
        except OSError:
            continue
        if is_file:
            env[key] = str(found)


def _private_venv(base: pathlib.Path, real_site: pathlib.Path) -> str:
    """Build, once per process, a venv whose `home` is ABSOLUTE over the real packages.

    Returns:
        the private venv's interpreter: a copy of `base`, an absolute-home pyvenv.cfg beside it,
        and a `.pth` file that adds `real_site` to the path.

    """
    key = str(real_site)
    if key not in _PRIVATE_PYTHON:
        root = pathlib.Path(tempfile.mkdtemp(prefix="mutate-venv-"))
        atexit.register(shutil.rmtree, root, ignore_errors=True)
        (root / "bin").mkdir()
        shutil.copy2(base, root / "bin" / base.name)
        config = f"home = {base.parent}\ninclude-system-site-packages = false\n"
        (root / "pyvenv.cfg").write_text(config, encoding="utf-8")
        version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = root / "lib" / version / "site-packages"
        site.mkdir(parents=True)
        (site / "real.pth").write_text(f"{real_site}\n", encoding="utf-8")
        _PRIVATE_PYTHON[key] = str(root / "bin" / base.name)
    return _PRIVATE_PYTHON[key]


def portable_python(py: pathlib.Path) -> tuple[str, str]:
    """Pick the interpreter that runs a suite, and the venv site-packages it then needs.

    ⚑ A bazel-built venv writes `home = bin` in its pyvenv.cfg: RELATIVE, so the venv can move.
    A relative home resolves against the CURRENT directory, so any test that spawns
    `sys.executable` from another directory got `Could not find platform independent
    libraries` and failed on the UNMUTATED module (W2340, measured by the control on
    test_runproc). Passing the real interpreter with `PYTHONPATH` was not enough: a child the
    test starts with its OWN environment (test_stub_authority) then lost the venv's packages.
    For such a venv the suite runs through a PRIVATE venv (`_private_venv`), whose home is
    absolute and whose `.pth` reaches the real packages, so every child works from any directory
    and with any environment; a venv with an absolute home, or none, runs as before.

    Returns:
        (the interpreter to run, a site-packages directory to add to PYTHONPATH or '').

    """
    config = py.parent.parent / "pyvenv.cfg"
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except OSError:
        return str(py), ""
    homes = [ln.partition("=")[2].strip() for ln in lines if ln.startswith("home")]
    sites = sorted(py.parent.parent.glob("lib/python*/site-packages"))
    base = pathlib.Path(sys.base_prefix) / "bin" / "python3"
    if not homes or pathlib.Path(homes[0]).is_absolute() or not sites or not base.is_file():
        return str(py), ""
    return _private_venv(base, sites[0].resolve()), ""


def node_env(env: dict[str, str], work: pathlib.Path, report: pathlib.Path) -> dict[str, str]:
    """Add what the node-report plugin needs: where to write, and where it is importable from.

    ⚑ THE PLUGIN'S DIRECTORY IS NAMED ON `PYTHONPATH`, NOT LEFT TO `python -m`. Under bazel the
    interpreter runs with a safe path (no implicit cwd entry), so `-p _mutate_nodes` could not
    import and the suite never started (measured 2026-11-19 in `//:test_mutate_runner`).

    Returns:
        the environment with `MUTATE_NODES` and a `PYTHONPATH` that starts at `work`.

    """
    existing = env.get("PYTHONPATH", "")
    path = f"{work}{os.pathsep}{existing}" if existing else str(work)
    return {**env, "MUTATE_NODES": str(report), "PYTHONPATH": path}


def _launch_suite(
    grid: Grid,
    work: pathlib.Path,
    env: dict[str, str],
    tests: list[str],
    report: pathlib.Path,
) -> subprocess.CompletedProcess[str]:
    """Run the distribution's suite, or the tests chosen for this module, inside the mutant's tree.

    Returns:
        the completed suite process.

    """
    mark = cpu_mark()
    done = launch(
        [
            portable_python(grid.py)[0],
            "-m",
            "pytest",
            "-x",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            "-p",
            PLUGIN_FILE.removesuffix(".py"),
            "-c",
            str(work / grid.config.name),
            *(tests or ["tests"]),
        ],
        work,
        node_env(env, work, report),
    )
    report_phase("control launch" if "-vvv" in tests else "suite launch", mark)
    return done


def _plan(
    dist: pathlib.Path, modules: list[pathlib.Path]
) -> tuple[
    list[str],
    list[str],
    list[tuple[str, Mutant]],
]:
    """Enumerate every def-site, setting aside the ones this operator cannot reach.

    Returns:
        `(attempted, unreachable, jobs)` — every site, the import-time ones, and the rest as
        `(site, Mutant)` in source order.

    """
    attempted: list[str] = []
    unreachable: list[str] = []
    jobs: list[tuple[str, Mutant]] = []
    for mod in modules:
        source = mod.read_text(encoding="utf-8")
        tree = ast.parse(source)
        rel = mod.relative_to(dist)
        skip = import_time_sites(tree)
        for path, _node in sites(tree):
            site = f"{rel}::{path}"
            attempted.append(site)
            # ⚑ COUNTED IN ATTEMPTED AND NOT RUN. Dropping it from `attempted` would make the
            # accounting balance by shrinking the denominator, which is the flattering direction
            # and the one this runner's predecessor took with ERRORED.
            if path in skip:
                unreachable.append(site)
                continue
            jobs.append((site, Mutant(rel, source, path)))
    return attempted, unreachable, jobs


def lint_declared(dist: pathlib.Path, declared: list[Declared]) -> int:
    """Check every declared defect plants, without running a suite: `MUTATE_LINT=1` (W1176).

    A declaration the grid would report as errored or unapplied is found here in a second, not in
    a gate: the module is not a file, the rewrite leaves source that does not parse, or the pattern
    matches nothing in its scope. The line's format was already checked when it was read.

    Returns:
        0 when every declaration plants, 1 after naming each one that does not on stderr.

    """
    problems: list[str] = []
    for item in declared:
        path = dist / item.module
        if not path.is_file():
            problems.append(f"{item.label}: {item.module} is not a file")
            continue
        try:
            planted = plant(path.read_text(encoding="utf-8"), item.spec)
        except ValueError as exc:
            problems.append(f"{item.label}: {exc}")
            continue
        if planted is None:
            problems.append(f"{item.label}: the pattern matches nothing in its scope")
    for problem in problems:
        sys.stderr.write(f"mutate: {problem}\n")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    """Run the grid over one distribution and report the three categories by name.

    Returns:
        0 when every site was accounted for and none survived, 1 otherwise.

    """
    # ⚑⚑⚑ A DEBUG MODE IN THE RUNNER, NOT A REPRODUCTION BESIDE IT. The previous tick built a
    # standalone probe that reconstructed `run()` by hand; it WORKED while the real path failed,
    # which made a wrong diagnosis believable. A reproduction that is not the code under test is a
    # second instrument, and this tree has measured that class four times.
    debug = "--debug" in argv
    # ⚑⚑⚑ THE INTERPRETER IS NOT RESOLVED, AND RESOLVING IT COST THREE TICKS. `.venv/bin/python`
    # is a SYMLINK to the mise interpreter, and a venv works precisely BECAUSE the interpreter is
    # invoked through its own `bin/` path — that is what sets `sys.prefix` and puts the venv's
    # `site-packages` on the path. `.resolve()` follows the symlink and hands back
    # `~/.local/share/mise/.../python3.13`, so every mutant ran under the BARE SYSTEM INTERPRETER
    # with no venv at all.
    # ⚑⚑ AND IT ONLY SHOWED ON ONE DISTRIBUTION, WHICH IS WHY IT SURVIVED SO LONG: `ratchet` and
    # `fence` declare `dependencies = []`, so their suites run fine under a bare interpreter.
    # `mdstruct` declares `panflute` and died instantly — `ModuleNotFoundError` in 0.04s, which
    # was the tell all along. **A failure that fast has not imported anything**, and the message
    # named the missing package rather than the missing venv.
    # ⚑ FIVE HYPOTHESES DIED BEFORE THIS ONE, every one about the ENVIRONMENT of the subprocess —
    # PATH, PYTHONPATH composition, the editable `.pth`, pytest's rootdir, site-packages staging.
    # The cause was the INTERPRETER argument, one line above where they were all looking. What
    # found it was printing the arguments `main()` actually passes into `run()`, after `run()`
    # was measured CORRECT when called directly with the same-looking values.
    # ⚑ ABSOLUTE BUT NOT RESOLVED. The subprocess runs with `cwd` set to the temp tree, so a
    # relative argument names nothing there — measured, `FileNotFoundError` on the first cell.
    # `absolute()` prepends the caller's cwd WITHOUT following symlinks, which is exactly the
    # distinction this line turns on.
    config = pathlib.Path(argv[2]).resolve()
    grid = Grid(py=pathlib.Path(argv[1]).absolute(), dist=config.parent, config=config)
    modules = sorted((grid.dist / "src").rglob("*.py"))
    attempted, unreachable, jobs = _plan(grid.dist, modules)
    groups: dict[str, list[str]] = {"killed": [], "survived": [], "errored": []}

    # ⚑⚑ A MALFORMED `mutants.regex` REFUSES THE WHOLE GRID, naming the line (W629), rather than
    # being read as "declared nothing". A MALFORMED `MUTATE_SHARD` REFUSES IT THE SAME WAY (W970).
    try:
        chosen = select(os.environ.get("MUTATE_SHARD", ""), os.environ.get("MUTATE_SITE", ""))
        declared = [d for d in read_declared(grid.dist) if chosen.keep(d.label)]
    except ValueError as exc:
        sys.stderr.write(f"mutate: {exc}\n")
        return 1
    attempted = [s for s in attempted if chosen.keep(s)]
    unreachable = [s for s in unreachable if chosen.keep(s)]
    jobs = [(site, mutant) for site, mutant in jobs if chosen.keep(site)]
    if chosen.site and not attempted and not declared:
        sys.stderr.write(f"mutate: MUTATE_SITE {chosen.site!r} names no site or defect\n")
        return 1
    if os.environ.get("MUTATE_PLAN"):
        sys.stdout.write(plan_line(grid.dist.name, attempted, unreachable, len(declared)))
        return 0
    if os.environ.get("MUTATE_LINT"):
        return lint_declared(grid.dist, declared)
    verdicts, regex = run_all(
        grid,
        [m for _site, m in jobs],
        declared,
        debug=debug,
        share=chosen.share,
    )
    for (site, _mutant), got in zip(jobs, verdicts, strict=True):
        if debug:
            sys.stdout.write(f"    {site} -> {got}\n")
        groups[got].append(site)
    name = chosen.label(grid.dist.name)
    code = _account(name, len(modules), attempted, unreachable, groups)
    # ⚑ EVERY SECTION IS PRINTED BEFORE ANY DECIDES THE EXIT: `code or _regex_section(...)` would
    # skip printing the declared-defect section whenever the def-site grid had already failed.
    # ⚑ SURVIVED AND ERRORED CELLS ARE JUDGED AGAINST THE DISTRIBUTION'S BASELINE (W2340, github-cb
    # 2026-11-13): none recorded is the old rule, any such cell fails; a recorded one may only fall.
    _regex_section(regex)
    gated = judge_debt(grid.dist, (attempted, unreachable), declared, (groups, regex))
    return 1 if any((code, gated, _budget_section())) else 0


def site_keys(dist: pathlib.Path) -> list[str]:
    """List the key of every def-site this runner would mutate in a distribution (W1883).

    ⚑ THE GENERATOR ASKS THE RUNNER, NOT A SECOND FINDER: a per-site target that named a site the
    runner does not count would be refused by `MUTATE_SITE` ("names no site"), and a site the
    generator missed would never run. Import-time sites are not listed: the operator cannot reach
    them, so no target could kill them.

    Returns:
        the keys in source order, `src/pkg/mod.py::func`.

    """
    _attempted, _unreachable, jobs = _plan(dist, sorted((dist / "src").rglob("*.py")))
    return [site for site, _mutant in jobs]


def plan_line(name: str, attempted: list[str], unreachable: list[str], declared: int) -> str:
    """Say how big a grid is without running it: `MUTATE_PLAN=1` (mtools:W981).

    ⚑ SHARD COUNTS COME FROM DATA, NOT A GUESS (W967's method): a grid costs about its mutable
    sites times a suite run, so `sites` is what decides how many shards a `:mutants` target needs.

    Returns:
        one line: the grid's name, its mutable sites, its unreachable ones and its declared defects.

    """
    sites = len(attempted) - len(unreachable)
    return f"{name}: sites={sites} unreachable={len(unreachable)} declared={declared}\n"


def claim_cores(wanted: int, cpus: int, take: Callable[[str], bool]) -> list[str]:
    """Take up to `wanted` core labels, never waiting, from the labels `mutants-core:0..cpus-1`.

    ⚑ A CORE IS A LABEL CLAIM, SO SHARDS STARTING TOGETHER DIVIDE THE FREE CORES (W1765). Every
    shard used to read the same load sample at the same moment and each took the same free cores;
    a claim is exclusive, so two pools sharing one taker can take at most `cpus` labels between
    them. `take(label)` is the non-blocking fence claim (claims.take): True when the label was
    free and is now this shard's, False when another holds it. It stops at `wanted`, so a shard
    never hoards cores it will not use.

    Returns:
        the labels taken, in label order; possibly none.

    """
    taken: list[str] = []
    for core in range(cpus):
        if len(taken) >= wanted:
            break
        label = f"{CORE_LABEL}:{core}"
        if take(label):
            taken.append(label)
    return taken


def pool_size(
    jobs: str,
    cpus: int,
    share: int,
    load1: float = 0.0,
    take: Callable[[str], bool] | None = None,
) -> int:
    """Decide how many mutant suites one runner runs at once.

    ⚑ A SHARD GETS ITS SHARE OF THE MACHINE, NOT ALL OF IT (mtools:W970). Bazel schedules each
    shard as one test, but each shard's runner used to start `cpu_count` suites, so six shards of
    one distribution oversubscribed the host six times over and starved every healthy neighbour
    into a timeout (measured 2026-10-11: `test_operands` 3 s alone, 65 s in the gate). An explicit
    `MUTATE_JOBS` still wins. With a `take`, the declared count is a ceiling on CLAIMS (W1765):
    the pool is as wide as the cores it got, and a shard that got none still runs one worker
    rather than wait.

    Returns:
        the worker count, at least one.

    """
    if jobs and take is not None:
        return max(1, len(claim_cores(min(int(jobs), cpus), cpus, take)))
    if jobs:
        return max(1, min(int(jobs), free_cores(cpus, load1)))
    return max(1, cpus // max(1, share))


def load_one() -> float:
    """Read the host's one-minute load.

    Returns:
        the load, or 0.0 (an idle host) when `/proc/loadavg` cannot be read.

    """
    try:
        return float(pathlib.Path("/proc/loadavg").read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


def cpu_line(cpu_s: float, workers: int) -> str:
    """Say what the grid cost in CPU, which a loaded host cannot inflate (W1769).

    ⚑ WALL TIME CHASES LOAD, CPU TIME DOES NOT: one shard took 35 s alone and 265 s inside a gate at
    load 59, so sharding by the gate's wall time ratchets without end. The CPU seconds the suites
    used, divided by the children run at once, is the wall time the shard needs on an idle host.

    Returns:
        one newline-terminated line: the CPU seconds, the children, and the idle-host wall seconds.

    """
    width = max(1, workers)
    return f"shard cpu={cpu_s:.1f}s children={width} idle_wall={cpu_s / width:.1f}s\n"


def budget_verdict(cpu_s: float, budget: str) -> str | None:
    """Judge a shard's CPU seconds against the budget its BUILD declares (W1772).

    ⚑ THE FAILURE THRESHOLD IS CPU, NOT THE WALL CLOCK (operator 2026-09-23/24: bound by CPU
    time, never a timer; 2026-10-20: the 50% line is measured in the unit of the failure
    threshold). A shard that needs 90 CPU seconds needs them whether the host is idle or at
    load 60, so only a shard that really grew can fail. An unset or malformed budget judges
    nothing.

    Returns:
        a refusal line when `cpu_s` is over the budget, else None.

    """
    try:
        limit = float(budget)
    except ValueError:
        return None
    if limit <= 0 or cpu_s <= limit:
        return None
    return f"shard CPU BUDGET EXCEEDED: used {cpu_s:.1f}s, declared {limit:.1f}s; shard it finer\n"


def _budget_section() -> int:
    """Print the budget refusal when this shard's suites used more CPU than `MUTATE_SHARD_CPU_S`.

    Returns:
        1 when over budget, else 0.

    """
    used = resource.getrusage(resource.RUSAGE_CHILDREN)
    refusal = budget_verdict(
        used.ru_utime + used.ru_stime, os.environ.get("MUTATE_SHARD_CPU_S", "")
    )
    if refusal is None:
        return 0
    sys.stdout.write(refusal)
    return 1


def free_cores(cpus: int, load1: float) -> int:
    """Say how many cores are idle right now, never below one.

    ⚑ `MUTATE_JOBS` IS THE CEILING, NOT THE COUNT (github-8f, 2026-10-20): 31 shards timed out when
    each started its declared 8 children on a host already at load 78, and bazel's `cpu:K` tag does
    not hold these shards back (measured). The runner bounds its own fan-out at start, from what is
    free, and never waits, so a busy host runs a shard narrower and the wall limit is untouched.

    Returns:
        `cpus - load1` rounded, at least one.

    """
    return max(1, round(cpus - load1))


def settle_verdict(future: concurrent.futures.Future[str], cell: str, held: list[str]) -> str:
    """Read one cell's verdict; a held temp tree is recorded against the cell, not a verdict.

    ⚑ AN INFRASTRUCTURE FAILURE IS NOT A MUTANT VERDICT (W2694). A tree that could not be removed
    says nothing about whether the suite noticed the defect, so it is neither killed, survived nor
    errored: it is collected by name and the shard refuses after every other cell has finished.

    Returns:
        the cell's verdict, or `held` for a cell whose tree could not be removed.

    """
    try:
        return future.result()
    except ScratchTreeHeldError as err:
        held.append(f"{cell}: {err}")
        return "held"


def refuse_held(held: list[str]) -> None:
    """Name every cell whose temp tree was held, and end the shard.

    The shard is refused, loudly and by cell: a clean report over cells that left trees on the
    shared tmp tier would be a capacity leak, and a crash that names no cell is what b89 was.
    """
    if not held:
        return
    sys.stderr.write(
        f"\nmutate: {len(held)} cell(s) could not clean their temp tree (infrastructure):\n"
    )
    for line in held:
        sys.stderr.write(f"    {line}\n")
    sys.exit(1)


_CELL_CPU: contextvars.ContextVar[list[float]] = contextvars.ContextVar("mutate_cell_cpu")
"""The CPU seconds charged so far to the cell the current worker is running (W2805)."""


def charge(seconds: float) -> None:
    """Add CPU seconds to the cell this worker is running; nothing when no cell is being timed."""
    box = _CELL_CPU.get(None)
    if box is not None:
        box[0] += seconds


def timed(spent: dict[str, float], cell: str, job: Callable[[], str]) -> str:
    """Run one cell's job and record the CPU its suites used against the cell's id.

    ⚑ THE CPU IS RECORDED WHETHER THE JOB RETURNS OR RAISES, and a cell can run two suites (the
    control and the mutant): every launch the worker makes while the job runs is charged to it.

    Returns:
        the job's verdict.

    """
    box = [0.0]
    token = _CELL_CPU.set(box)
    try:
        return job()
    finally:
        _CELL_CPU.reset(token)
        spent[cell] = box[0]


def cell_lines(spent: Mapping[str, float], order: Sequence[str]) -> str:
    """Say what each cell cost in CPU, one line per cell in run order (W2805).

    ⚑ THE SHARD TOTAL HIDES WHICH CELL IS HEAVY: b104's two heaviest shards read 165.2 and 163.0 s
    over four to eight cells each, and the guard could not tell whether one cell carried them. A
    cell absent from `spent` reads 0.0, never a missing line.

    Returns:
        `cell cpu=<seconds>s <cell id>` per cell, newline-terminated.

    """
    return "".join(f"cell cpu={spent.get(cell, 0.0):.1f}s {cell}\n" for cell in order)


def reconcile_line(spent: Mapping[str, float], total: float) -> str:
    """Say how much of the shard's CPU the cells account for (W2805).

    ⚑ THE WITNESS THE INSTRUMENT NEEDS: the per-cell numbers are complete only if they add up to
    the shard's. What is left (the runner's own git calls, the interpreter copy) is `unattributed`;
    a large share means work escaped the cells. CPU of a process that is not a waited descendant
    of a suite (a daemonized child, a server a test talks to) is counted by neither side.

    Returns:
        `cells cpu=<sum>s shard cpu=<total>s unattributed=<difference>s`, newline-terminated.

    """
    cells = sum(spent.values())
    return f"cells cpu={cells:.1f}s shard cpu={total:.1f}s unattributed={total - cells:.1f}s\n"


def run_all(
    grid: Grid, mutants: list[Mutant], declared: list[Declared], *, debug: bool, share: int = 1
) -> tuple[list[str], list[tuple[str, str]]]:
    """Run every def-site mutant and every declared defect in one pool, results in input order.

    ⚑⚑ THE DECLARED DEFECTS SHARE THE POOL (W629): a distribution that declares none pays nothing,
    and one that declares some pays one suite run each, concurrently with the def-sites.

    Returns:
        the def-site verdicts, and each declared defect's `(label, outcome)`.

    """
    # ⚑⚑ THE MUTANTS RUN CONCURRENTLY, BECAUSE SERIAL COST GREW PAST THE TARGET'S CEILING. Measured
    # 2026-09-23: adding `membudget_cli` (~30 def-sites) took //fence:mutants past 300s at a load of
    # ~33 — the grid, not the host, was the cost: one full `-x` suite per site, one after another.
    # Raising the ceiling was refused (a standing rule) and so was narrowing the grid. Each mutant
    # already builds in its OWN temp tree with its OWN `HOME`, so they share nothing to race on;
    # results are gathered in SITE ORDER, so the report is the serial report, byte for byte.
    # `MUTATE_JOBS` bounds the pool; `1` restores the serial run; a shard takes its share (above).
    workers = pool_size(os.environ.get("MUTATE_JOBS", ""), os.cpu_count() or 1, share, load_one())
    # ⚑⚑ THE PRIVATE INTERPRETER IS BUILT BEFORE ANY WORKER EXISTS (W2340, measured 2026-11-13 on
    # //bibparse:mutants and //corpus:mutants: `OSError: [Errno 26] Text file busy`). Its first call
    # COPIES the interpreter, and a worker that forks while another worker has that copy open for
    # writing hands the child the write descriptor; the next exec of the copy then fails (ETXTBSY).
    # Built here, on the one thread, the copy is closed before the first fork.
    portable_python(grid.py)
    held: list[str] = []
    spent: dict[str, float] = {}
    sites = [f"{m.rel}::{m.name}" for m in mutants]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(timed, spent, cell, functools.partial(run, grid, mutant, debug=debug))
            for cell, mutant in zip(sites, mutants, strict=True)
        ]
        planted = [
            pool.submit(
                timed, spent, d.label, functools.partial(run_declared, grid, d, debug=debug)
            )
            for d in declared
        ]
        verdicts = [
            settle_verdict(f, f"{m.rel}::{m.name}", held)
            for f, m in zip(futures, mutants, strict=True)
        ]
        regex = [
            (d.label, settle_verdict(f, d.label, held))
            for d, f in zip(declared, planted, strict=True)
        ]
    refuse_held(held)
    used = resource.getrusage(resource.RUSAGE_CHILDREN)
    total = used.ru_utime + used.ru_stime
    sys.stdout.write(cpu_line(total, workers))
    sys.stdout.write(cell_lines(spent, [*sites, *(d.label for d in declared)]))
    sys.stdout.write(reconcile_line(spent, total))
    return verdicts, regex


def _regex_section(results: list[tuple[str, str]]) -> None:
    """Print the declared-defect section and say what a declared defect that was not killed means.

    ⚑ AN EMPTY SECTION IS NAMED, as the four before it are: `none declared` is a measurement and an
    absent heading is a silence that cannot be told from a section that never ran.

    ⚑⚑ ONLY `killed` IS NOT DEBT. `survived` is a suite blind to a defect the distribution named,
    `unapplied` a declaration the code has moved away from, and `errored` one that was never run;
    `baseline_gate` judges them against the distribution's recorded debt.
    """
    sys.stdout.write(
        f"\nREGEX ({len(results)}) — defects the distribution DECLARED in {DECLARATION_FILE}, "
        f"planted one at a time:\n"
    )
    if not results:
        sys.stdout.write("    none declared\n")
    for label, got in results:
        sys.stdout.write(f"    {label} -> {got}\n")
    bad = [label for label, got in results if got != "killed"]
    if bad:
        sys.stderr.write(
            f"\nmutate: {len(bad)} declared defect(s) NOT killed: a suite blind to a named defect "
            f"(survived), a stale declaration (unapplied) or one never run (errored)\n"
        )


BASELINE_FILE = "mutants-baseline.txt"
"""A distribution's recorded mutation debt: the cells its grid may leave ERRORED or SURVIVED.

⚑ A RATCHET BASELINE, NOT A WAIVER (github-cb's ruling on b66, 2026-11-13). The name matches the
ratchet classifier's `baseline` pattern, so census_repo counts its entries and nemik's pace and the
paydown rate see it. One entry per line, `<verdict> <cell>`, cells sorted and unique, `#` comments.
"""

_BASELINE_VERDICTS = ("survived", "errored", "unapplied")


def read_baseline(dist: pathlib.Path) -> tuple[dict[str, str], str]:
    """Read the cells a distribution's grid is recorded as leaving ERRORED, SURVIVED or unapplied.

    Returns:
        (cell -> verdict, a problem). The cells are empty when the distribution has no baseline
        file. The problem is empty when the file is well formed, else it names the first bad line:
        not `<verdict> <cell>`, an unknown verdict, or a cell repeated or out of order (the file
        is generated sorted, so a hand edit shows).

    """
    path = dist / BASELINE_FILE
    if not path.is_file():
        return {}, ""
    cells: dict[str, str] = {}
    previous = ""
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        verdict, _space, cell = line.partition(" ")
        if verdict not in _BASELINE_VERDICTS or not cell:
            return {}, f"{path.name}:{number}: not '<verdict> <cell>': {line!r}"
        if cell <= previous:
            return {}, f"{path.name}:{number}: {cell!r} is repeated or out of order"
        cells[cell] = verdict
        previous = cell
    return cells, ""


def debt_of(groups: dict[str, list[str]], regex: list[tuple[str, str]]) -> dict[str, str]:
    """Collect the cells a run left SURVIVED or ERRORED, and the declared defects not killed.

    Returns:
        cell -> verdict, for every def-site that survived or errored and every declared defect
        whose outcome was not `killed`.

    """
    debt = {site: verdict for verdict in ("survived", "errored") for site in groups[verdict]}
    debt.update({label: got for label, got in regex if got != "killed"})
    return debt


def baseline_gate(dist: pathlib.Path, debt: dict[str, str], ran: set[str]) -> int:
    """Judge this run's debt against the distribution's recorded debt: it may only fall.

    ⚑ A RISE AND A STALE ENTRY ARE BOTH REFUSED. A cell ERRORED or SURVIVED that the baseline does
    not list with that verdict is a rise. A baselined cell this run ran that is no longer in that
    state is stale: the baseline only falls when its file is edited down, so a paid-down cell
    cannot be left listed and later re-broken unseen. Only the cells this run RAN are judged, so a
    shard never refuses another shard's entry.

    Returns:
        0 when every debt cell is baselined with its verdict and every baselined cell this run ran
        is still in debt; 1 otherwise, or when the baseline file is malformed.

    """
    known, problem = read_baseline(dist)
    if problem:
        sys.stderr.write(f"mutate: {problem}\n")
        return 1
    rises = sorted(cell for cell, verdict in debt.items() if known.get(cell) != verdict)
    stale = sorted(
        cell for cell, verdict in known.items() if cell in ran and debt.get(cell) != verdict
    )
    sys.stdout.write(
        f"\nBASELINE ({len(known)} recorded in {BASELINE_FILE}): "
        f"{len(rises)} rise(s), {len(stale)} stale\n"
    )
    for cell in rises:
        sys.stdout.write(f"    RISE {debt[cell]} {cell}\n")
    for cell in stale:
        sys.stdout.write(f"    STALE {known[cell]} {cell}\n")
    if rises:
        sys.stderr.write(
            f"\nmutate: {len(rises)} cell(s) ERRORED or SURVIVED that {BASELINE_FILE} does not "
            f"list: the debt may only fall\n"
        )
    if stale:
        sys.stderr.write(
            f"\nmutate: {len(stale)} cell(s) listed in {BASELINE_FILE} are no longer in that "
            f"state: remove them, the baseline only falls\n"
        )
    return 1 if rises or stale else 0


def judge_debt(
    dist: pathlib.Path,
    cells: tuple[list[str], list[str]],
    declared: list[Declared],
    outcomes: tuple[dict[str, list[str]], list[tuple[str, str]]],
) -> int:
    """Judge one run's ERRORED and SURVIVED cells against the distribution's baseline.

    Args:
        dist: the distribution's directory, where its baseline file lives.
        cells: this run's attempted def-sites and its unreachable ones.
        declared: the declared defects this run planted.
        outcomes: the def-site groups by verdict and each declared defect's `(label, outcome)`.

    Returns:
        `baseline_gate`'s verdict over the cells this run ran.

    """
    attempted, unreachable = cells
    groups, regex = outcomes
    ran = (set(attempted) - set(unreachable)) | {d.label for d in declared}
    return baseline_gate(dist, debt_of(groups, regex), ran)


_LOG_SECTIONS = ("KILLED", "SURVIVED", "ERRORED", "UNREACHABLE", "REGEX")
_BAD_SECTIONS = {"SURVIVED": "survived", "ERRORED": "errored"}
_MIN_ARGV = 3  # the program, the flag, the distribution


def cells_from_log(text: str) -> tuple[set[str], dict[str, str]]:
    """Read the cells one shard's report ran and the ones it left in debt.

    ⚑ THE BASELINE IS GENERATED FROM A REPORT, NEVER TYPED (github-cb, 2026-11-13). A shard prints
    every category by name even when empty, so the sections are the whole account of what it ran.

    Returns:
        (every cell the report ran, cell -> verdict for each one SURVIVED, ERRORED or a declared
        defect not killed). Empty when the text has no section heading: a shard that crashed
        prints none, and the caller refuses it.

    """
    ran: set[str] = set()
    debt: dict[str, str] = {}
    section = ""
    for line in text.splitlines():
        head = line.split(" ", 1)[0]
        if head in _LOG_SECTIONS and line[len(head) :].startswith(" ("):
            section = head
        elif not line.startswith("    "):
            section = ""
        elif section == "REGEX" and " -> " in line:
            label, _arrow, got = line.strip().partition(" -> ")
            ran.add(label)
            if got != "killed":
                debt[label] = got
        elif section and section != "UNREACHABLE":
            cell = line.strip()
            ran.add(cell)
            if section in _BAD_SECTIONS:
                debt[cell] = _BAD_SECTIONS[section]
    return ran, debt


def render_baseline(cells: dict[str, str]) -> str:
    """Render a baseline file: a header, then `<verdict> <cell>` per line, cells sorted.

    Returns:
        the file's text.

    """
    header = (
        "# mutation debt: cells the grid leaves ERRORED, SURVIVED or unapplied.\n"
        "# A RATCHET: it only falls. GENERATED by\n"
        "# `mutate_runner.py --write-baseline DIST LOG...`, never hand-written.\n"
    )
    return header + "".join(f"{cells[cell]} {cell}\n" for cell in sorted(cells))


class BaselineMergeError(Exception):
    """A baseline cannot be regenerated; the message says why."""


def known_baseline(dist: pathlib.Path) -> dict[str, str]:
    """Read a distribution's recorded baseline, refusing a malformed one.

    Returns:
        the recorded cell -> verdict map (empty when the distribution has no baseline file).

    Raises:
        BaselineMergeError: the file is malformed, naming the first bad line.

    """
    cells, problem = read_baseline(dist)
    if problem:
        raise BaselineMergeError(problem)
    return cells


def merged_baseline(dist: pathlib.Path, logs: list[pathlib.Path]) -> dict[str, str]:
    """Merge shard reports into a distribution's baseline without writing it.

    Returns:
        the merged cell -> verdict map.

    Raises:
        BaselineMergeError: the old baseline is malformed, or a log holds no shard report.

    """
    known = known_baseline(dist)
    ran: set[str] = set()
    debt: dict[str, str] = {}
    for log in logs:
        seen, owed = cells_from_log(log.read_text(encoding="utf-8"))
        if not seen:
            msg = f"{log} holds no shard report (a crashed shard?)"
            raise BaselineMergeError(msg)
        ran |= seen
        debt.update(owed)
    return {cell: verdict for cell, verdict in known.items() if cell not in ran} | debt


def write_baseline(dist: pathlib.Path, logs: list[pathlib.Path]) -> int:
    """Rewrite a distribution's baseline from shard reports, keeping cells they did not run.

    ⚑ A REPORT REPLACES ONLY THE CELLS IT RAN, so one shard's log updates that shard's cells and
    leaves every other shard's entries as they were; the union of all the shards' logs is the whole
    distribution. A report with no section heading is refused (a crashed shard ran nothing).

    Returns:
        0 on success, 1 when the existing baseline is malformed or a log has no sections.

    """
    try:
        merged = merged_baseline(dist, logs)
    except BaselineMergeError as error:
        sys.stderr.write(f"mutate: {error}\n")
        return 1
    (dist / BASELINE_FILE).write_text(render_baseline(merged), encoding="utf-8")
    sys.stdout.write(f"{BASELINE_FILE}: {len(merged)} cell(s) from {len(logs)} report(s)\n")
    return 0


def shard_logs(dist: pathlib.Path, testlogs: pathlib.Path) -> list[pathlib.Path]:
    """Find a distribution's mutation test logs under bazel's testlogs root (W2777).

    Returns:
        every `<testlogs>/<dist>/mutants_N/test.log` in name order; the single
        `<testlogs>/<dist>/mutants/test.log` of a plain `sh_test` target when there are no shards;
        empty when neither exists.

    """
    base = testlogs / dist.name
    sharded = sorted(base.glob("mutants_*/test.log"))
    plain = base / "mutants" / "test.log"
    return sharded or ([plain] if plain.is_file() else [])


_SHARD_LINE = re.compile(r"\bshard (\d+)/(\d+):")


def require_one_shard_set(logs: list[pathlib.Path]) -> None:
    """Require the logs to be exactly ONE complete shard set (github-00 R3).

    ⚑ BAZEL'S TESTLOGS KEEPS THE LOGS OF SHARDS THAT NO LONGER EXIST, so a regeneration after the
    shard count changed (hooks 215 to 433) would fold a previous layout's logs into the baseline.
    Each runner report prints `shard i/N`; the set is accepted only when every log states the same
    N, the indices are exactly 0..N-1 once each, and the log count is N. ⚑ NOT PROVED: that every
    log is from ONE RUN: neither test.log nor test.xml carries the invocation id (read 2026-11-19),
    so same-layout logs of an older run could still mix.

    A plain single-target log (no `shard i/N` line) passes.

    Raises:
        BaselineMergeError: the logs repeat a shard, state different counts, or are not exactly
            shards 0..N-1.

    """
    seen: dict[int, int] = {}
    counts: set[int] = set()
    for log in logs:
        found = _SHARD_LINE.search(log.read_text(encoding="utf-8"))
        if found is None:
            continue
        index, total = int(found.group(1)), int(found.group(2))
        if index in seen:
            msg = f"shard {index} appears in two logs ({log})"
            raise BaselineMergeError(msg)
        seen[index] = total
        counts.add(total)
    if not seen:
        return
    if len(counts) != 1:
        msg = f"the logs state different shard counts {sorted(counts)}: another layout's leftover"
        raise BaselineMergeError(msg)
    (total,) = counts
    if sorted(seen) != list(range(total)) or len(logs) != total:
        listed = f"found {sorted(seen)} in {len(logs)} log(s)"
        msg = f"the logs are not exactly shards 0..{total - 1}: {listed}"
        raise BaselineMergeError(msg)


def regen_baseline(dist: pathlib.Path, testlogs: pathlib.Path) -> int:
    """Regenerate a distribution's baseline from its shard logs and say what changed (W2777).

    ⚑ MECHANIZES THE STEP A RUNNER CHANGE OWES EVERY DIST (b101 was refused at pkgbuild after only
    pytestspec's baseline was regenerated). It finds the logs, runs `write_baseline` over them, then
    prints each cell that came OFF (paydown) and each NEW cell (debt, which may only fall): a NEW
    cell is read before anything changes: the exit is 1 and the file is UNTOUCHED (github-00 R2). It
    also refuses logs that are not exactly one complete shard set (R3), and a malformed old
    baseline (R1), each with the reason named.

    Returns:
        0 when the baseline was written and no cell is new; 1 when there are no logs, they are
        not one complete shard set, a log or the old baseline is bad, or a cell is new (nothing
        is written then).

    """
    logs = shard_logs(dist, testlogs)
    if not logs:
        sys.stderr.write(f"mutate: no mutation test logs for {dist.name} under {testlogs}\n")
        return 1
    try:
        require_one_shard_set(logs)
        before = known_baseline(dist)
        merged = merged_baseline(dist, logs)
    except BaselineMergeError as error:
        sys.stderr.write(f"mutate: {error}\n")
        return 1
    for cell in sorted(set(before) - set(merged)):
        sys.stdout.write(f"OFF {before[cell]} {cell}\n")
    sys.stdout.write(f"paydown: {len(set(before) - set(merged))} cell(s) off\n")
    new = sorted(set(merged) - set(before))
    for cell in new:
        sys.stdout.write(f"NEW {merged[cell]} {cell}\n")
    if new:
        sys.stdout.write(
            f"mutate: {len(new)} NEW cell(s): the debt may only fall; {BASELINE_FILE} NOT written\n"
        )
        return 1
    (dist / BASELINE_FILE).write_text(render_baseline(merged), encoding="utf-8")
    sys.stdout.write(f"{BASELINE_FILE}: {len(merged)} cell(s) from {len(logs)} report(s)\n")
    return 0


def cli(argv: list[str]) -> int:
    """Run the baseline commands, or the grid when argv names neither.

    ⚑ `--write-baseline DIST LOG...` GENERATES the file, `--check-baseline DIST` says whether it is
    well formed (every shard also checks it, so the gate runs it on every mutation target).

    Returns:
        the command's exit status.

    """
    if len(argv) == _MIN_ARGV + 1 and argv[1] == "--regen-baseline":
        return regen_baseline(pathlib.Path(argv[2]), pathlib.Path(argv[3]))
    if len(argv) >= _MIN_ARGV and argv[1] == "--write-baseline":
        return write_baseline(pathlib.Path(argv[2]), [pathlib.Path(p) for p in argv[_MIN_ARGV:]])
    if len(argv) == _MIN_ARGV and argv[1] == "--check-baseline":
        problem = read_baseline(pathlib.Path(argv[2]))[1]
        if problem:
            sys.stderr.write(f"mutate: {problem}\n")
        return 1 if problem else 0
    return main(argv)


def _account(
    name: str,
    module_count: int,
    attempted: list[str],
    unreachable: list[str],
    groups: dict[str, list[str]],
) -> int:
    """Check that every site landed in exactly one category, then report all four by name.

    ⚑ SURVIVED AND ERRORED ARE REPORTED HERE AND JUDGED BY `baseline_gate`, which compares them to
    the distribution's recorded debt; this returns 1 only for a site that fell in no category.

    Returns:
        0 when every site was accounted for, 1 when one was not.

    """
    killed, survived, errored = groups["killed"], groups["survived"], groups["errored"]

    # ⚑⚑ SURVIVORS ARE `attempted - killed - errored` BY CONSTRUCTION, ASSERTED RATHER THAN
    # ASSUMED. paperkit's fingerprint names only the KILLED sites, so a site absent from it either
    # survived or was never mutated and the record cannot say which — *absent ≠ surviving*. They
    # volunteered that as the half to build differently. Carrying ATTEMPTED is what makes the three
    # sets exhaustive; this check is what makes the carrying real rather than decorative.
    accounted = sorted(killed + survived + errored + unreachable)
    if accounted != sorted(attempted):
        missing = sorted(set(attempted) - set(accounted))
        sys.stderr.write(
            f"mutate: {len(attempted)} attempted, {len(accounted)} accounted — "
            f"unclassified: {missing}\n"
        )
        return 1

    sys.stdout.write(
        f"{name}: ATTEMPTED {len(attempted)} def-site(s) in {module_count} module(s)\n"
    )
    # ⚑⚑⚑ EVERY CATEGORY PRINTS EVEN WHEN EMPTY, AND THAT IS NOT COSMETIC. The predecessor hid
    # ERRORED behind `if errored:`, so a reader saw no heading and could not tell *none occurred*
    # from *the set is never populated* — and the defect lived in exactly that gap for as long as
    # the probe existed. An empty category NAMED is a measurement; an absent category is a silence.
    for label, group, gloss in (
        ("KILLED", killed, "the suite RAN and a test FAILED"),
        ("SURVIVED", survived, "the suite ran and noticed nothing"),
        ("ERRORED", errored, "the suite did NOT run, so it noticed nothing"),
        (
            "UNREACHABLE",
            unreachable,
            (
                "constructed at IMPORT time (an Enum member); this OPERATOR cannot reach them, "
                "which is a fact about `body -> raise` and not about the suite"
            ),
        ),
    ):
        sys.stdout.write(f"\n{label} ({len(group)}) — {gloss}:\n")
        for site in sorted(group):
            sys.stdout.write(f"    {site}\n")

    if errored:
        sys.stderr.write(
            f"\nmutate: {len(errored)} mutant(s) could not be RUN — the grid is incomplete and "
            f"a clean SURVIVED list would be a claim over a population that was never measured\n"
        )
    if survived:
        sys.stderr.write(
            f"\nmutate: {len(survived)} def-site(s) SURVIVED — mutating them changed no verdict, "
            f"so nothing in this distribution's suite exercises them\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv))

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Progress of a running commit: CPU spent by its process tree and a no-progress witness (W1803).

`mikemol-commit` ends a gate that runs past a wall timeout (3 h) as NOT COMMITTED with no verdict.
Under load that is a verdict decided by the clock, which the operator rules out: a bound is CPU time
and a no-progress witness, never a timer. This is the measuring half, pure and seamed:

    tree_ticks(procs, root)   the CPU ticks (user plus system) of a process and all its descendants
    step(last, ticks, size)   the witness after one more look: progress resets it, a flat look adds
    stalled(w, looks)         True once `looks` consecutive looks showed no CPU delta and no output

⚑ PROGRESS IS EITHER OF TWO THINGS: the tree spent CPU since the last look, or the commit's output
grew (a phase mark was written). A gate waiting on a lease or on the network spends no CPU and
writes nothing: that is the no-progress case. A gate grinding on one long test writes nothing but
spends CPU: progress. Neither alone is the witness.

⚑ A LOOK IS A SAMPLE, NOT A DEADLINE. How many flat looks make a stall, and how far apart the looks
are, belong to the caller (learned from the gate's own history); nothing here reads a clock.

⚑ THE PROCESS TABLE IS A SEAM: `snapshot` reads `/proc` through a reader the tests replace, so the
tests build a table by hand and the real reader is checked once against this process.

⚑ THE WATCH REPLACES THE WALL WAIT (W1804): `watch` waits on the child in slices of `period`
seconds, takes a look at each slice's end, and gives up only on a stall. The period is how
often to look, not how long the gate may run: a gate that keeps spending CPU or writing runs
as long as it likes, and one that does neither for `looks` looks in a row is ended and says
which gate phase it was in. Both numbers come from the environment, for the caller to learn.

CONSUMED BY: `commit_kata.run_git_in`.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks.gatephase import marks
from mikemol.hooks.snapshot import DEFAULT_NAMESPACE, NAMESPACE_ENV

CPU_FIELDS = (13, 14)  # utime and stime in /proc/<pid>/stat, counted after the command name
PPID_FIELD = 1
Procs = Mapping[int, tuple[int, int]]
"""pid to (parent pid, CPU ticks)."""
Read = Callable[[Path], str | None]
Wait = Callable[[float], int | None]
LOOKS_ENV = "MIKEMOL_COMMIT_STALL_LOOKS"
PERIOD_ENV = "MIKEMOL_COMMIT_LOOK_S"
DEFAULT_LOOKS = 120
DEFAULT_PERIOD_S = 30.0
NO_PHASE = "none marked"
SERVER_COMM = "bazel("
WORKSPACE_FLAG = "--workspace_directory="


@dataclass(frozen=True, slots=True)
class Witness:
    """What the last look saw and how many looks in a row showed nothing new."""

    ticks: int = 0
    size: int = 0
    flat: int = 0


def parse_stat(text: str) -> tuple[int, int] | None:
    """Read (parent pid, CPU ticks) out of one /proc/<pid>/stat line.

    The command name is parenthesised and may hold spaces and parentheses, so the fields are
    counted from the LAST closing parenthesis.

    Returns:
        the pair, or None when the line is not a stat line.

    """
    close = text.rfind(")")
    fields = text[close + 1 :].split() if close >= 0 else []
    if len(fields) <= max(CPU_FIELDS) - 2:
        return None
    try:
        parent = int(fields[PPID_FIELD])
        ticks = sum(int(fields[index - 2]) for index in CPU_FIELDS)
    except ValueError:
        return None
    return parent, ticks


def read_text(path: Path) -> str | None:
    """Read a file, None when it cannot be read (a process that exited between look and read).

    Returns:
        the text, or None.

    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def snapshot(proc: Path = Path("/proc"), read: Read = read_text) -> dict[int, tuple[int, int]]:
    """Read the process table.

    Returns:
        pid to (parent pid, CPU ticks) for every process whose stat line could be read.

    """
    table: dict[int, tuple[int, int]] = {}
    try:
        names = [entry.name for entry in proc.iterdir() if entry.name.isdecimal()]
    except OSError:
        return table
    for name in names:
        text = read(proc / name / "stat")
        parsed = parse_stat(text) if text is not None else None
        if parsed is not None:
            table[int(name)] = parsed
    return table


def tree_ticks(procs: Procs, root: int) -> int:
    """Add up the CPU ticks of `root` and every descendant in the table.

    Returns:
        the sum; 0 when `root` is not in the table.

    """
    if root not in procs:
        return 0
    seen = {root}
    frontier = [root]
    while frontier:
        parent = frontier.pop()
        for pid, (ppid, _) in procs.items():
            if ppid == parent and pid not in seen:
                seen.add(pid)
                frontier.append(pid)
    return sum(procs[pid][1] for pid in seen)


def servers_of(proc: Path = Path("/proc"), read: Read = read_text) -> dict[int, str]:
    """Find the running bazel servers and the workspace each one serves.

    A bazel server is a daemon, not a child of the client that started it: it renames itself
    `bazel(<workspace>)` and carries `--workspace_directory=<dir>` in its command line, so the
    process comm picks the candidates and only those have their command line read.

    Returns:
        pid to workspace directory for every server whose command line could be read.

    """
    found: dict[int, str] = {}
    try:
        names = [entry.name for entry in proc.iterdir() if entry.name.isdecimal()]
    except OSError:
        return found
    for name in names:
        comm = read(proc / name / "comm")
        if comm is None or not comm.startswith(SERVER_COMM):
            continue
        line = read(proc / name / "cmdline")
        for word in (line or "").split("\0"):
            if word.startswith(WORKSPACE_FLAG):
                found[int(name)] = word[len(WORKSPACE_FLAG) :]
    return found


def gate_servers(servers: Mapping[int, str], roots: Sequence[Path]) -> list[int]:
    """Pick the servers whose workspace lies under one of the gate's directories.

    Returns:
        their pids, in pid order; none when `roots` is empty.

    """
    return sorted(
        pid
        for pid, workspace in servers.items()
        if any(Path(workspace).is_relative_to(root) for root in roots)
    )


def gate_roots(repo: str, env: Mapping[str, str]) -> list[Path]:
    """Name the directories a commit's gate builds in: its snapshot and the staged copy.

    ⚑ THE SNAPSHOT NAMESPACE IS NARROWED TO THE REPOSITORY'S OWN DIRECTORY when it is known, so
    another repository's gate running at the same time is not read as this one's progress. The
    staged copy is the pre-commit's own `$TMPDIR/mtools-staged`.

    Returns:
        the namespace (with the repository's name when given) and the staged directory.

    """
    namespace = Path(env.get(NAMESPACE_ENV, DEFAULT_NAMESPACE))
    temp = Path(env.get("TMPDIR") or Path.home() / ".cache")
    return [namespace / repo if repo else namespace, temp / "mtools-staged"]


def step(last: Witness, ticks: int, size: int) -> Witness:
    """Fold one look into the witness.

    Returns:
        a witness with the flat count reset when the CPU grew or the output grew, else one more.

    """
    if ticks > last.ticks or size > last.size:
        return Witness(ticks, size, 0)
    return Witness(max(ticks, last.ticks), max(size, last.size), last.flat + 1)


def stalled(witness: Witness, looks: int) -> bool:
    """Say whether `looks` consecutive looks showed no progress.

    Returns:
        True once the flat count reaches `looks`; never for a `looks` below one.

    """
    return looks >= 1 and witness.flat >= looks


def looks_from(env: Mapping[str, str]) -> int:
    """Say how many flat looks in a row make a stall.

    Returns:
        `MIKEMOL_COMMIT_STALL_LOOKS` when it is a positive integer, else `DEFAULT_LOOKS`; zero or
        text is ignored and never read as no bound, which would let a wedged gate hold the lease.

    """
    raw = env.get(LOOKS_ENV, "")
    return int(raw) if raw.isdecimal() and int(raw) > 0 else DEFAULT_LOOKS


def period_from(env: Mapping[str, str]) -> float:
    """Say how many seconds pass between looks.

    Returns:
        `MIKEMOL_COMMIT_LOOK_S` when it is a positive number, else `DEFAULT_PERIOD_S`.

    """
    try:
        value = float(env.get(PERIOD_ENV, ""))
    except ValueError:
        return DEFAULT_PERIOD_S
    return value if value > 0 else DEFAULT_PERIOD_S


def phase_of(text: str) -> str:
    """Name the gate phase the output had reached.

    Returns:
        the last phase mark's name, or `NO_PHASE` when the output holds none.

    """
    found = marks(text)
    return found[-1].name if found else NO_PHASE


def stall_text(text: str, looks: int, period: float) -> str:
    """Say why a commit was ended, for the process's stderr.

    Returns:
        one sentence naming the looks, their spacing and the last phase.

    """
    return (
        f"git made no progress: no CPU in its process tree and no new output for {looks} looks "
        f"{period:g} s apart; last gate phase: {phase_of(text)}"
    )


@dataclass(frozen=True, slots=True)
class Probes:
    """What a look reads: the output's size, the process table and the gate's other pids.

    `extra` names the pids outside the child's tree whose CPU counts as the gate's progress (the
    gate's bazel servers: daemons, not children, and where a build spends almost all of its CPU).
    """

    size: Callable[[], int]
    procs: Callable[[], Procs] = snapshot
    extra: Callable[[], Sequence[int]] = tuple


def watch(wait: Wait, pid: int, probes: Probes, pace: tuple[int, float]) -> int | None:
    """Wait for the process `pid`, looking at its progress between slices.

    `wait(seconds)` waits up to that long and returns the exit code, or None while the
    process still runs (the caller owns the subprocess); `pace` is (looks, period seconds).

    Returns:
        the exit code once the process ends, or None when `looks` consecutive looks showed no
        CPU and no output (the process is left running; the caller ends it).

    """
    looks, period = pace
    seen = Witness()
    while True:
        code = wait(period)
        if code is not None:
            return code
        table = probes.procs()
        ticks = tree_ticks(table, pid) + sum(tree_ticks(table, s) for s in probes.extra())
        seen = step(seen, ticks, probes.size())
        if stalled(seen, looks):
            return None

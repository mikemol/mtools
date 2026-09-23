# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Admission before fencing: lease `mb` from a machine-global total, or wait, or be refused.

Ported by design from substrate's `scripts/membudget` (bash: `cmd_run` plus the sourced
`membudget-ledger`), per its semaphore letter of 2026-09-22. `run_once` fences one command and
knows about no other; this module decides whether that command may START, against every live lease
on the host.

⚑⚑ TWO HALVES, AND THE SPLIT IS THE DESIGN. The first is a function of a ledger SNAPSHOT and
injected facts (which owners are alive, what the load is): parsing, gc to a fixpoint, the admission
verdict, the claim keyway — every row of the letter's table is testable without a lock, a clock or a
second process. The second, below it, is the locked file, the wait loop and the lease's lifetime,
and it decides nothing the first half did not already decide.

⚑⚑ NESTED LEASES ARE DISJOINT, NOT SUB-ALLOCATED. Every lease, top-level or nested, draws from the
GLOBAL pool and gets its own cap; a parent governs only cascade-gc and the parent-gone refusal. The
"recursive sub-allocation" model was retired at the origin on 2026-08-05 and survives in prose
there; this follows the live source.

CONSUMED BY: nothing in this repository yet — substrate's `scripts/membudget` becomes a thin CLI
over it once it lands (letter, "After it lands").
"""

from __future__ import annotations

import contextlib
import enum
import fcntl
import os
import sys
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# The ledger's two line kinds, and each one's word count (a lease's label may hold spaces, so its
# count is a minimum).
_TOTAL = "TOTAL_MB"
_TOTAL_FIELDS = 2
_LEASE = "LEASE"
_LEASE_FIELDS = 7

# `/proc/<pid>/stat` field 22 (starttime), as an index into the fields AFTER the comm's `)` —
# which begin at field 3.
_STARTTIME_AFTER_COMM = 22 - 3

# The parent field's spelling for a top-level lease.
NO_PARENT = "-"

# The label prefix that makes a lease exclusive by name.
CLAIM = "claim:"


@dataclass(frozen=True, slots=True)
class Lease:
    """One live reservation: who holds how much, under which parent, for what.

    ⚑ `owner` IS `pid:starttime`, NOT A PID. A reused pid carries a different start time, so a dead
    lease can never be kept alive by an unrelated process that inherited its number.
    """

    lease_id: str
    mb: int
    owner: str
    epoch: int
    parent: str
    label: str

    def line(self) -> str:
        """Render this lease as its ledger line.

        Returns:
            the `LEASE …` line, without a newline.

        """
        return " ".join(
            (_LEASE, self.lease_id, str(self.mb), self.owner, str(self.epoch), self.parent,
             self.label))


@dataclass(frozen=True, slots=True)
class Ledger:
    """A snapshot of the shared ledger: the total, if declared, and the live leases."""

    total_mb: int | None
    leases: tuple[Lease, ...]
    # How many `TOTAL_MB` lines the text carried. ⚑ MORE THAN ONE IS CORRUPTION, NOT A CHOICE:
    # taking either would size the shared pool by line order, so `decide` refuses and nothing
    # rewrites it.
    total_lines: int = 0

    @property
    def ambiguous(self) -> bool:
        """Whether the ledger declares its total more than once — refused, never resolved."""
        return self.total_lines > 1

    @property
    def used(self) -> int:
        """The sum of every live lease — nested ones included, because nesting is disjoint.

        Returns:
            megabytes held.

        """
        return sum(lease.mb for lease in self.leases)

    def render(self) -> str:
        """Render the snapshot as ledger text.

        Returns:
            the ledger file's content.

        """
        head = [] if self.total_mb is None else [f"{_TOTAL} {self.total_mb}"]
        return "".join(f"{line}\n" for line in head + [lease.line() for lease in self.leases])


def parse(text: str) -> Ledger:
    """Read ledger text. A line of neither kind, or a malformed lease, is skipped.

    ⚑ SKIPPED, NOT FATAL: the ledger is appended by many processes, and one torn line must not take
    every repo's admission down. A malformed lease reads as ABSENT — which frees its budget early,
    the one direction a bad line can err in, and gc would have dropped it anyway.

    Returns:
        the snapshot.

    """
    total: int | None = None
    total_lines = 0
    leases: list[Lease] = []
    for raw in text.splitlines():
        words = raw.split(" ")
        if words[0] == _TOTAL:
            # ⚑ COUNTED EVEN WHEN MALFORMED: a second total that does not parse is still a second
            # claim about the pool's size.
            total_lines += 1
            if len(words) == _TOTAL_FIELDS and words[1].isdigit():
                total = int(words[1])
        elif words[0] == _LEASE and len(words) >= _LEASE_FIELDS:
            _kind, lease_id, mb, owner, epoch, parent = words[:6]
            if mb.isdigit() and epoch.isdigit():
                label = " ".join(words[6:])
                leases.append(Lease(lease_id, int(mb), owner, int(epoch), parent, label))
    return Ledger(total, tuple(leases), total_lines)


def starttime(pid: int, proc: str = "/proc") -> str | None:
    """Return a live pid's start time (field 22 of `/proc/<pid>/stat`), or None when it is gone.

    ⚑ THE COMM FIELD CAN HOLD SPACES AND PARENTHESES, so fields are counted from the LAST `)`.

    Returns:
        the start time in clock ticks, as text, or None.

    """
    try:
        stat = (Path(proc) / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    after = stat[stat.rfind(")") + 2:].split(" ")
    return after[_STARTTIME_AFTER_COMM] if len(after) > _STARTTIME_AFTER_COMM else None


def owner_of(pid: int, proc: str = "/proc") -> str:
    """Return the `pid:starttime` identity of a live process.

    Returns:
        the owner string.

    """
    return f"{pid}:{starttime(pid, proc)}"


def alive(owner: str, proc: str = "/proc") -> bool:
    """Report whether a lease's owner is the SAME process still running.

    Returns:
        True only when the pid exists AND its start time matches.

    """
    pid, _sep, start = owner.partition(":")
    return pid.isdigit() and bool(start) and starttime(int(pid), proc) == start


def gc(ledger: Ledger, is_alive: Callable[[str], bool]) -> Ledger:
    """Drop dead-owned leases, then orphans of dropped parents, to a fixpoint, on ONE snapshot.

    ⚑ LIVENESS IS ASKED ONCE PER OWNER, before the cascade — a process that dies mid-gc is
    somebody's next gc, not a reason for this one to disagree with itself.

    Returns:
        the snapshot without dead leases; the SAME object when nothing was dropped, so a caller can
        skip the rewrite (an unconditional rewrite woke every waiter into a churn storm).

    """
    live = {owner: is_alive(owner) for owner in {lease.owner for lease in ledger.leases}}
    kept = [lease for lease in ledger.leases if live[lease.owner]]
    while True:
        ids = {lease.lease_id for lease in kept}
        orphans = [lease for lease in kept if lease.parent not in {NO_PARENT, *ids}]
        if not orphans:
            break
        kept = [lease for lease in kept if lease not in orphans]
    if len(kept) == len(ledger.leases):
        return ledger
    return replace(ledger, leases=tuple(kept))


class Verdict(enum.Enum):
    """The admission decision for one request against one snapshot."""

    ADMIT = "admit"
    BLOCK = "block"
    IMPOSSIBLE = "impossible"
    PARENT_GONE = "parent-gone"
    NO_TOTAL = "no-total"
    CLAIMED = "claimed"
    AMBIGUOUS_TOTAL = "ambiguous-total"


# Exit codes, as the origin: 3 = cannot proceed now (or ever), 4 = the ledger itself says no.
EXIT_REFUSED = 3
EXIT_LEDGER = 4


def exit_code(verdict: Verdict) -> int | None:
    """Return the origin's exit code for a terminal verdict, or None for ADMIT and BLOCK.

    ⚑ CLAIMED MAPS TO 3 ONLY WHEN THE CALLER WILL NOT WAIT — it is a BLOCK otherwise, like
    over-budget; the wait loop decides which.

    Returns:
        3, 4, or None.

    """
    return {
        Verdict.IMPOSSIBLE: EXIT_REFUSED,
        Verdict.CLAIMED: EXIT_REFUSED,
        Verdict.PARENT_GONE: EXIT_LEDGER,
        Verdict.NO_TOTAL: EXIT_LEDGER,
        Verdict.AMBIGUOUS_TOTAL: EXIT_LEDGER,
    }.get(verdict)


class Kind(enum.Enum):
    """How a claim tag's name is compared — declared by the claimant, never guessed.

    ⚑⚑⚑ THE KEYWAY, AS THE FINDINGS LEFT IT: BYTE comparison let four spellings of one path acquire
    at once (trailing slash, `//`, `./`, case — cassian §2a); realpath-for-everything was refuted
    (it mangles Bazel labels, splits one artifact across hash-named output bases, and resolves bare
    words against the cwd). What survives is DECLARE THE KIND: `claim:path:` compares by realpath,
    `claim:label:` by label normalisation, and a bare `claim:` stays byte-compared — uncomparable
    with anything but its own spelling, which is the honest answer for a name nobody typed.
    """

    PATH = "path"
    LABEL = "label"
    BARE = "bare"


@dataclass(frozen=True, slots=True)
class ClaimKey:
    """A claim tag, reduced to what two claims must share to exclude each other."""

    kind: Kind
    canonical: str


def normalise_label(raw: str) -> str:
    """Return a Bazel label's canonical spelling: `//pkg` → `//pkg:pkg`, trailing `/` dropped.

    ⚑ NEVER A FILESYSTEM OPERATION. `//x:y` names a target in a build graph, not a path under the
    cwd; realpath would turn it into a directory that may or may not exist.

    Returns:
        the canonical label.

    """
    label = raw.rstrip("/") if raw not in {"", "//"} else raw
    if ":" in label or not label.startswith(("//", "@")):
        return label
    return f"{label}:{label.rsplit('/', 1)[-1]}"


def claim_key(label: str) -> ClaimKey | None:
    """Return the claim a lease label makes, or None when it makes none.

    Returns:
        the key two claims must share to exclude each other, or None.

    """
    if not label.startswith(CLAIM):
        return None
    tag = label[len(CLAIM):]
    kind, sep, name = tag.partition(":")
    if sep and kind == Kind.PATH.value:
        return ClaimKey(Kind.PATH, os.path.realpath(name))
    if sep and kind == Kind.LABEL.value:
        return ClaimKey(Kind.LABEL, normalise_label(name))
    return ClaimKey(Kind.BARE, tag)


@dataclass(frozen=True, slots=True)
class Request:
    """What a caller asks for: an amount, a label, and the lease it nests under."""

    mb: int
    label: str = ""
    parent: str = NO_PARENT


def decide(request: Request, ledger: Ledger) -> Verdict:
    """Return the admission verdict for `request` against a (gc'd) snapshot.

    ⚑⚑ THE ORDER IS THE LETTER'S TABLE, AND IT MATTERS: a ledger with no total refuses before
    anything is compared against it; an impossible request refuses WITHOUT BLOCKING — waiting cannot
    make `mb > total` fit; a vanished parent refuses rather than orphaning a child the next gc would
    drop. Only then do the waitable conditions — a held claim, or not enough free — say BLOCK.
    ⚑ A CLAIM NEEDS NO CAPACITY: `mb=0` with a claim is a first-class request.

    Returns:
        the verdict.

    """
    refused = _refusal(request, ledger)
    if refused is not None:
        return refused
    key = claim_key(request.label)
    if key is not None and any(claim_key(lease.label) == key for lease in ledger.leases):
        return Verdict.CLAIMED
    total = ledger.total_mb if ledger.total_mb is not None else 0
    if request.mb > total - ledger.used:
        return Verdict.BLOCK
    return Verdict.ADMIT


def _refusal(request: Request, ledger: Ledger) -> Verdict | None:
    """Return the verdict waiting cannot change, or None when the request may wait or proceed.

    ⚑ THE LEDGER'S OWN REFUSALS COME FIRST — two totals, then none — because nothing may be compared
    against a pool whose size is unknown or contested.

    Returns:
        AMBIGUOUS_TOTAL, NO_TOTAL, IMPOSSIBLE or PARENT_GONE, or None.

    """
    if ledger.ambiguous:
        return Verdict.AMBIGUOUS_TOTAL
    if ledger.total_mb is None:
        return Verdict.NO_TOTAL
    if request.mb > ledger.total_mb:
        return Verdict.IMPOSSIBLE
    if request.parent != NO_PARENT and request.parent not in {
            lease.lease_id for lease in ledger.leases}:
        return Verdict.PARENT_GONE
    return None


def load_ok(load: tuple[float, float, float], nproc: int, maxload: float) -> bool:
    """Report whether the host's load admits a new start. `maxload <= 0` disables the gate.

    ⚑ BOTH CONJUNCTS, AS THE ORIGIN: the one-minute load, AND the smaller of the five- and
    fifteen-minute loads — so a spike alone does not hold starts back, and neither does a long
    average that has already fallen.

    Returns:
        whether a start may proceed.

    """
    if maxload <= 0:
        return True
    ceiling = nproc * maxload
    load1, load5, load15 = load
    return load1 <= ceiling and min(load5, load15) <= ceiling


# --- the effectful half: the locked ledger file, the wait loop, the lease's lifetime ---

# The origin's defaults: a bounded lock acquire, a gc rate limit, and the waiter's poll backoff.
LOCK_TIMEOUT_S = 10.0
GC_INTERVAL_S = 2.0
POLL_START_S = 0.1
POLL_MAX_S = 2.0
_BACKOFF = 1.6

# `TOTAL_MB`'s default: 70% of the host's memory, never more than 8 GiB.
_DEFAULT_FRACTION = 0.7
_DEFAULT_CEILING_MB = 8192
_KIB_PER_MB = 1024

# The load gate's default ceiling, per CPU.
MAXLOAD = 10.0


class LockTimeoutError(RuntimeError):
    """The ledger lock stayed held past its bound — a live but wedged holder, never a dead one."""


class RefusedError(RuntimeError):
    """Admission was refused; `code` is the origin's exit code (3 or 4)."""

    def __init__(self, verdict: Verdict, code: int, message: str) -> None:
        """Carry the verdict and its exit code with the message."""
        super().__init__(message)
        self.verdict = verdict
        self.code = code


@dataclass(frozen=True, slots=True)
class Store:
    """The shared ledger file and its lock file beside it.

    ⚑⚑ WRITES ARE ATOMIC, SO A READ OUTSIDE THE LOCK IS ALWAYS CONSISTENT: a claim is one appended
    line; gc and release write a sibling file and rename it over the ledger. A stale read can only
    UNDER-count free budget — the safe direction — so the waiter polls without the lock and takes
    it only to claim or reap.
    """

    path: Path
    lock_timeout_s: float = LOCK_TIMEOUT_S

    @property
    def lock_path(self) -> Path:
        """The lock file, `<ledger>.lock`."""
        return self.path.with_name(self.path.name + ".lock")

    @contextlib.contextmanager
    def locked(self) -> Iterator[None]:
        """Hold the ledger lock, acquiring it within `lock_timeout_s` or raising.

        ⚑ BOUNDED, BECAUSE A DEAD HOLDER'S DESCRIPTOR CLOSES AND FREES IT: a timeout can only mean
        a live holder that is wedged, and waiting forever on that is how one repo stalls the rest.

        Yields:
            nothing; the lock is held for the block's duration.

        Raises:
            LockTimeoutError: the lock stayed held past the bound.

        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            deadline = time.monotonic() + self.lock_timeout_s
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        msg = f"{self.lock_path} held past {self.lock_timeout_s}s"
                        raise LockTimeoutError(msg) from None
                    time.sleep(0.01)
            yield
        finally:
            os.close(fd)

    def read(self) -> Ledger:
        """Return the current snapshot; an absent ledger is an empty one with no total.

        Returns:
            the snapshot.

        """
        try:
            return parse(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return Ledger(None, ())

    def append(self, lease: Lease) -> None:
        """Append one lease line. Call only under the lock."""
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(lease.line() + "\n")

    def rewrite(self, ledger: Ledger) -> None:
        """Replace the ledger atomically: write a sibling, rename it. Under the lock only.

        ⚑⚑ AN AMBIGUOUS LEDGER IS NEVER REWRITTEN. Rendering writes ONE total, so a gc or a release
        over a file with two would quietly "repair" it by keeping one — the guess `decide` exists to
        refuse. The one place that guards it is here, so no caller can reach around it.
        """
        if ledger.ambiguous:
            return
        tmp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        tmp.write_text(ledger.render(), encoding="utf-8")
        tmp.replace(self.path)


def default_total_mb(meminfo: Path = Path("/proc/meminfo")) -> int:
    """Return `min(70% of MemTotal, 8192)` in megabytes.

    Returns:
        the default `TOTAL_MB`.

    """
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            kib = int(line.split()[1])
            return min(int(kib / _KIB_PER_MB * _DEFAULT_FRACTION), _DEFAULT_CEILING_MB)
    return _DEFAULT_CEILING_MB


def init(store: Store, total_mb: int) -> bool:
    """Declare the ledger's total, unless one is already declared.

    ⚑ AN EXISTING TOTAL IS NOT OVERWRITTEN: every repo on the host shares it, and a second init
    resizing the pool under live leases would change what each of them was admitted against.

    Returns:
        whether this call wrote the total.

    Raises:
        RefusedError: the ledger declares its total more than once — fix the file; init guesses
            nothing, the same rule substrate's bash applies.

    """
    with store.locked():
        snap = store.read()
        if snap.ambiguous:
            raise RefusedError(Verdict.AMBIGUOUS_TOTAL, EXIT_LEDGER,
                               f"{store.path} has {snap.total_lines} TOTAL_MB lines")
        if snap.total_mb is not None:
            return False
        store.rewrite(Ledger(total_mb, snap.leases))
        return True


def reap(store: Store, is_alive: Callable[[str], bool] = alive) -> Ledger:
    """Gc the ledger under the lock, rewriting it ONLY when something was dropped.

    Returns:
        the snapshot after gc.

    """
    with store.locked():
        snap = store.read()
        kept = gc(snap, is_alive)
        if kept is not snap:
            store.rewrite(kept)
        return kept


def _announce(msg: str) -> None:
    """Write a waiter's one-time notice where a person watching the run will see it."""
    sys.stderr.write(msg + "\n")


@dataclass(frozen=True, slots=True)
class Waiting:
    """How a blocked request waits: whether it may, for how long, and against which load ceiling."""

    noblock: bool = False
    timeout_s: float | None = None
    maxload: float = MAXLOAD
    poll_start_s: float = POLL_START_S
    poll_max_s: float = POLL_MAX_S
    gc_interval_s: float = GC_INTERVAL_S


@dataclass(frozen=True, slots=True)
class Host:
    """The facts about the machine the loop reads — injected, so no arm depends on the box."""

    is_alive: Callable[[str], bool] = alive
    loadavg: Callable[[], tuple[float, float, float]] = os.getloadavg
    nproc: int = os.cpu_count() or 1
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    announce: Callable[[str], None] = _announce


# The defaults `acquire` and `admit` wait and read the host with, as singletons.
WAIT = Waiting()
HOST = Host()


def _terminal_message(verdict: Verdict, request: Request, snap: Ledger) -> str:
    """Say why a verdict waiting cannot change is a refusal.

    Returns:
        the refusal's message.

    """
    messages = {
        Verdict.IMPOSSIBLE: f"IMPOSSIBLE: {request.mb} MB exceeds the total {snap.total_mb} MB",
        Verdict.PARENT_GONE: f"parent lease {request.parent} is no longer in the ledger",
        Verdict.NO_TOTAL: "the ledger declares no TOTAL_MB — run init first",
        Verdict.AMBIGUOUS_TOTAL: (f"the ledger has {snap.total_lines} TOTAL_MB lines — corrupt or "
                                  "hand-edited; fix the file, do not guess"),
    }
    return messages.get(verdict, verdict.name)


def _claim(store: Store, request: Request, host: Host) -> Lease | None:
    """Under the lock: gc, re-decide, and append the lease only if it STILL fits.

    ⚑⚑ THE RE-CHECK UNDER THE LOCK IS WHAT MAKES A RACE HAVE ONE WINNER. Two contenders can both
    pass the lock-free check; only the one that re-decides ADMIT against the locked snapshot writes.

    Returns:
        the appended lease, or None when the locked snapshot no longer admits it.

    """
    with store.locked():
        raw = store.read()
        snap = gc(raw, host.is_alive)
        if snap is not raw:
            store.rewrite(snap)
        if decide(request, snap) is not Verdict.ADMIT:
            return None
        lease = Lease(uuid.uuid4().hex[:12], request.mb, owner_of(os.getpid()),
                      int(time.time()), request.parent, request.label)
        store.append(lease)
        return lease


def acquire(store: Store, request: Request, waiting: Waiting = WAIT,
            host: Host = HOST) -> Lease:
    """Wait for `request` to fit, then lease it; or refuse.

    ⚑⚑ A DEAD HOLDER IS REAPED BEFORE IT IS BELIEVED: every pass that would BLOCK first gcs, so a
    budget held by a killed process is freed by the next contender rather than waited on forever.

    Returns:
        the lease, live until `release`.

    Raises:
        RefusedError: the request is impossible, the ledger refuses it, or it would wait while
            `noblock` is set or past `timeout_s`.

    """
    started = host.clock()
    poll = waiting.poll_start_s
    announced = False
    last_gc = float("-inf")
    while True:
        snap = store.read()
        now = host.clock()
        if now - last_gc >= waiting.gc_interval_s or not announced:
            snap = reap(store, host.is_alive)
            last_gc = now
        verdict = decide(request, snap)
        if verdict not in {Verdict.ADMIT, Verdict.BLOCK, Verdict.CLAIMED}:
            code = exit_code(verdict) or EXIT_REFUSED
            raise RefusedError(verdict, code, _terminal_message(verdict, request, snap))
        load_fits = load_ok(host.loadavg(), host.nproc, waiting.maxload)
        if verdict is Verdict.ADMIT and load_fits:
            lease = _claim(store, request, host)
            if lease is not None:
                return lease
            continue
        if waiting.noblock:
            raise RefusedError(verdict, EXIT_REFUSED, f"would wait ({verdict.name}); noblock set")
        if waiting.timeout_s is not None and now - started >= waiting.timeout_s:
            raise RefusedError(verdict, EXIT_REFUSED, f"gave up after {waiting.timeout_s}s")
        if not announced:
            free = (snap.total_mb or 0) - snap.used
            host.announce(f"fence.admit: waiting ({verdict.name}, load ok={load_fits}): "
                          f"need {request.mb} MB, free {free} MB of {snap.total_mb} MB")
            announced = True
        host.sleep(poll)
        poll = min(poll * _BACKOFF, waiting.poll_max_s)


def release(store: Store, lease: Lease) -> None:
    """Drop `lease` from the ledger. If the lock cannot be taken, leave it for gc to reap.

    ⚑ GIVING UP IS SAFE HERE: the lease's owner is this process, and once it exits the next gc
    drops the line — releasing early only returns the budget sooner.
    """
    with contextlib.suppress(LockTimeoutError), store.locked():
        snap = store.read()
        kept = tuple(item for item in snap.leases if item.lease_id != lease.lease_id)
        if len(kept) != len(snap.leases):
            store.rewrite(Ledger(snap.total_mb, kept))


@contextlib.contextmanager
def admit(store: Store, request: Request, waiting: Waiting = WAIT,
          host: Host = HOST) -> Iterator[Lease]:
    """Hold a lease for the duration of a `with` block — acquired on entry, released on exit.

    Yields:
        the lease.

    """
    lease = acquire(store, request, waiting, host)
    try:
        yield lease
    finally:
        release(store, lease)

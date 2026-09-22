# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Admission before fencing: lease `mb` from a machine-global total, or wait, or be refused.

Ported by design from substrate's `scripts/membudget` (bash: `cmd_run` plus the sourced
`membudget-ledger`), per its semaphore letter of 2026-09-22. `run_once` fences one command and
knows about no other; this module decides whether that command may START, against every live lease
on the host.

⚑⚑ THIS FILE IS THE PURE HALF, AND THE SPLIT IS THE DESIGN. Everything here is a function of a
ledger SNAPSHOT and injected facts (which owners are alive, what the load is): parsing, gc to a
fixpoint, the admission verdict, the claim keyway. The locked file, the wait loop and the context
manager are the effectful half and sit on top. A verdict computed from a snapshot can be tested
against every row of the letter's table without a lock, a clock or a second process.

⚑⚑ NESTED LEASES ARE DISJOINT, NOT SUB-ALLOCATED. Every lease, top-level or nested, draws from the
GLOBAL pool and gets its own cap; a parent governs only cascade-gc and the parent-gone refusal. The
"recursive sub-allocation" model was retired at the origin on 2026-08-05 and survives in prose
there; this follows the live source.

CONSUMED BY: nothing in this repository yet — substrate's `scripts/membudget` becomes a thin CLI
over it once it lands (letter, "After it lands").
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

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
    leases: list[Lease] = []
    for raw in text.splitlines():
        words = raw.split(" ")
        if words[0] == _TOTAL and len(words) == _TOTAL_FIELDS and words[1].isdigit():
            total = int(words[1])
        elif words[0] == _LEASE and len(words) >= _LEASE_FIELDS:
            _kind, lease_id, mb, owner, epoch, parent = words[:6]
            if mb.isdigit() and epoch.isdigit():
                label = " ".join(words[6:])
                leases.append(Lease(lease_id, int(mb), owner, int(epoch), parent, label))
    return Ledger(total, tuple(leases))


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
    return Ledger(ledger.total_mb, tuple(kept))


class Verdict(enum.Enum):
    """The admission decision for one request against one snapshot."""

    ADMIT = "admit"
    BLOCK = "block"
    IMPOSSIBLE = "impossible"
    PARENT_GONE = "parent-gone"
    NO_TOTAL = "no-total"
    CLAIMED = "claimed"


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
    if ledger.total_mb is None:
        return Verdict.NO_TOTAL
    if request.mb > ledger.total_mb:
        return Verdict.IMPOSSIBLE
    if request.parent != NO_PARENT and request.parent not in {
            lease.lease_id for lease in ledger.leases}:
        return Verdict.PARENT_GONE
    key = claim_key(request.label)
    if key is not None and any(claim_key(lease.label) == key for lease in ledger.leases):
        return Verdict.CLAIMED
    if request.mb > ledger.total_mb - ledger.used:
        return Verdict.BLOCK
    return Verdict.ADMIT


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

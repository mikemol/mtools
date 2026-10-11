# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Claims owned by a long-lived process: take one and return, drop it, list who holds what (W911).

⚑ `hold` OWNS ITS LEASE THROUGH THE CHILD IT SPAWNS, so a claim made that way ends with the command.
A session working a card needs a claim that outlives any one command (mtools:W889,
`.claude/design/W889-work-claims.md`): the lease is written with the OWNER the caller names, a
`pid:starttime` of the long-lived process (default: the caller's parent, the session), and the verb
returns. The ledger's own gc reaps it when that owner dies, so nothing here has to be remembered to
be released.

⚑ ADVISORY WITH A NAME ON IT, NOT A MUTEX. A held claim refuses the second taker with the holder's
`pid:starttime`, lease id and age (`admit.holder_note`), and the refusal is exit 3 for a caller to
print, not a lock to wait on. The commit claim stays the only true mutex.

⚑ ZERO CAPACITY, SO IT NEVER COMPETES FOR BUDGET: the lease is 0 units, which `admit.decide` admits
when no live lease holds the same claim key, whatever the ledger's total or unit.

Everything here takes the store, the host's facts and the time as arguments, so the tests run on a
temporary ledger and a fixed clock.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from mikemol.fence import admit

if TYPE_CHECKING:
    from collections.abc import Sequence

_OWNER_FLAG = "--owner-pid"
_ID_LENGTH = 12


@dataclass(frozen=True, slots=True)
class Outcome:
    """What a claim verb did: whether it succeeded, and the line to say."""

    ok: bool
    message: str


def now() -> int:
    """Read the wall clock in whole seconds, as a lease's epoch is written.

    Returns:
        the unix time.

    """
    return int(time.time())


def parse(args: Sequence[str], default_pid: int) -> tuple[str, int]:
    """Read `LABEL [--owner-pid N]`.

    Returns:
        the label and the owning pid.

    Raises:
        ValueError: no label, an extra operand, a bad pid, or a label that makes no claim.

    """
    rest = list(args)
    pid = default_pid
    if _OWNER_FLAG in rest:
        at = rest.index(_OWNER_FLAG)
        if at + 1 >= len(rest) or not rest[at + 1].isdecimal() or int(rest[at + 1]) < 1:
            msg = f"{_OWNER_FLAG} needs a positive pid"
            raise ValueError(msg)
        pid = int(rest[at + 1])
        rest = rest[:at] + rest[at + 2 :]
    if len(rest) != 1:
        msg = "takes one LABEL and an optional --owner-pid N"
        raise ValueError(msg)
    if admit.claim_key(rest[0]) is None:
        msg = f"{rest[0]!r} makes no claim: a claim label starts with `claim:`"
        raise ValueError(msg)
    return rest[0], pid


def take(store: admit.Store, host: admit.Host, label: str, pid: int, epoch: int) -> Outcome:
    """Write a zero-capacity claim owned by `pid`, or name the holder.

    ⚑ A CLAIM FOR A DEAD PROCESS IS REFUSED: it would be born unowned and reaped by the next gc,
    saying "claimed" to no one.

    Returns:
        success with the lease id, or a refusal saying who holds the claim or why none can be made.

    """
    owner = admit.owner_of(pid)
    if not host.is_alive(owner):
        return Outcome(ok=False, message=f"the owner process {pid} is not running")
    request = admit.Request(0, label, admit.NO_PARENT)
    with store.locked():
        snap = admit.gc(store.read(), host.is_alive)
        verdict = admit.decide(request, snap)
        if verdict is not admit.Verdict.ADMIT:
            said = admit.holder_note(snap, request, epoch) or verdict.name
            return Outcome(ok=False, message=said)
        lease_id = uuid.uuid4().hex[:_ID_LENGTH]
        lease = admit.Lease(lease_id, 0, owner, epoch, admit.NO_PARENT, label)
        store.rewrite(replace(snap, leases=(*snap.leases, lease)))
    return Outcome(ok=True, message=lease_id)


def drop(store: admit.Store, host: admit.Host, label: str, pid: int) -> Outcome:
    """Remove the claims on `label` that `pid` owns, and no one else's.

    ⚑ ONLY THE OWNER RELEASES. A claim held by another process is the holder's to drop, or the
    gc's when it dies; releasing by label alone would let a session free a peer's declaration.

    Returns:
        success naming how many were dropped, or a refusal saying nobody of that owner held it.

    """
    key = admit.claim_key(label)
    owner = admit.owner_of(pid)
    with store.locked():
        snap = admit.gc(store.read(), host.is_alive)
        kept = tuple(
            lease
            for lease in snap.leases
            if not (admit.claim_key(lease.label) == key and lease.owner == owner)
        )
        dropped = len(snap.leases) - len(kept)
        if dropped:
            store.rewrite(replace(snap, leases=kept))
    if not dropped:
        return Outcome(ok=False, message=f"{label} is not held by {owner}")
    return Outcome(ok=True, message=f"released {label} ({dropped})")


def listing(snap: admit.Ledger, epoch: int) -> list[str]:
    """List every live claim with its holder, lease id and age.

    Returns:
        one line per claim lease, in ledger order; empty when nothing is claimed.

    """
    return [
        f"{lease.label} owner={lease.owner} id={lease.lease_id} age={max(0, epoch - lease.epoch)}s"
        for lease in snap.leases
        if admit.claim_key(lease.label) is not None
    ]

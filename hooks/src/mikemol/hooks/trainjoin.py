# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A lease holder finds the stacks queued behind it and joins their entries to its run (W1669).

⚑ THE QUEUE IS ONE TIP, NOT N GATES (github-8f and the operator, 2026-10-18: 25 stacks behind a
serial gate at 12 to 35 minutes each, "test the tip work and move it to the front of the queue").
The holder of the lease already gates a stack's tip once; it can gate the tip of EVERY stack waiting
behind it in the same run, and the merge train (`trainrun`) lands the green ones and bisects a red.

⚑ A FOLLOWER IS WHAT ITS SUBMIT LEFT IN THE LEDGER, NOT WHAT ITS PROCESS KNOWS: at submit a stack
froze its files into `stack-<key>.snap` (W1447) and, since this card, left a copy of its entries
beside it as `stack-<key>.items.json`. A leader that finds both can build the follower's commits
from the submit-time bytes without asking the follower's process for anything, so the follower
may be waiting on its lock, on a re-exec, or anywhere else.

⚑ ONLY A STACK BEHIND THE LEADER JOINS (a larger submit key), IN SUBMIT ORDER, so the order the
operator submitted is the order the train lands. A follower missing either file, or whose snapshot
no longer matches its entries, is left alone and runs on its own turn as before: joining is an
acceleration and never a reason to lose a stack.

CONSUMED BY: the merge train driver (W1654); `stackfreeze.at_submit` writes the items copy.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from mikemol.hooks import stacksnap
from mikemol.hooks.stackrun import Item, items_of


@dataclass(frozen=True)
class Follower:
    """A queued stack read back from the ledger: its key and its items, files frozen."""

    key: str
    items: tuple[Item, ...]


def items_path(ledger: Path, key: str) -> Path:
    """Name the copy of a stack's entries a submit leaves beside its snapshot.

    Returns:
        `<ledger>/stack-<key>.items.json`.

    """
    return ledger / f"stack-{key}.items.json"


def snap_path(ledger: Path, key: str) -> Path:
    """Name the snapshot of a stack's frozen files.

    Returns:
        `<ledger>/stack-<key>.snap`, the file `stackfreeze.at_submit` writes.

    """
    return ledger / f"stack-{key}.snap"


def load(ledger: Path, key: str) -> Follower | None:
    """Read one queued stack back from the ledger.

    Returns:
        the follower with its frozen files on its items, or None when either file is missing or
        unreadable or the snapshot's entry count differs from the entries'.

    """
    items = items_of(items_path(ledger, key))
    loaded = stacksnap.load(snap_path(ledger, key))
    if isinstance(items, str) or loaded is None or len(loaded) != len(items):
        return None
    joined = tuple(
        replace(item, files=tuple(files)) for item, files in zip(items, loaded, strict=True)
    )
    return Follower(key, joined)


def followers(ledger: Path, key: str, queued: Sequence[str]) -> list[Follower]:
    """Find the queued stacks behind `key` that can join its run, in submit order.

    Returns:
        one follower per queued key larger than `key` whose ledger files are whole; a key that is
        not a number is never joined.

    """
    behind = sorted((k for k in queued if k.isdigit() and int(k) > int(key)), key=int)
    found = [load(ledger, k) for k in behind]
    return [f for f in found if f is not None]

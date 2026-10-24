# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""When the current turn began and how many Stop blocks it has had (W1903, of W1896).

A Stop hook that escalates an idle end (W1896, rung 2) must know two things the Stop payload does
not carry: the time the turn began, so it can ask whether any card moved since, and how many times
it has already blocked this turn, so a broken guard cannot trap it. Both are facts of the
transcript, so the reader that owns the format answers them, and the hook does not parse it.

⚑ A TURN BEGINS AT THE LAST USER-ROLE RECORD THAT STARTED SOMETHING. A tool result answers a call
inside the turn, and a Stop block's feedback continues the turn it blocked, so neither begins one;
a human prompt, a scheduled wake, a background-task event and a peer message each do (`waker` in
cacheturns names them).

⚑ THE BLOCKS ARE THE STOP-HOOK RECORDS AFTER THAT START: each block the hook wrote came back as a
user-role record carrying `Stop hook`, so counting them is counting this turn's blocks.

⚑ A TRANSCRIPT WITH NO TURN-STARTING RECORD ANSWERS NONE, never a guessed time.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from mikemol.transcriptstruct.cacheturns import waker
from mikemol.transcriptstruct.records import Record, UserRecord

_CONTINUES = frozenset({"tool-result", "stop-hook"})


@dataclass(frozen=True, slots=True)
class TurnStart:
    """The record a turn began at and the Stop blocks that have followed it."""

    line: int
    at: str
    blocks: int


def turn_start(records: Iterable[Record]) -> TurnStart | None:
    """Find where the latest turn began and count its Stop blocks.

    Returns:
        the line and timestamp of the last user record that is neither a tool result nor a Stop
        block, with the number of Stop-block records after it; None when there is none or it
        carries no timestamp.

    """
    start: TurnStart | None = None
    for record in records:
        if not isinstance(record, UserRecord):
            continue
        kind = waker(record)
        if kind not in _CONTINUES:
            stamp = record.raw.get("timestamp")
            start = TurnStart(record.line, stamp, 0) if isinstance(stamp, str) else None
        elif kind == "stop-hook" and start is not None:
            start = TurnStart(start.line, start.at, start.blocks + 1)
    return start

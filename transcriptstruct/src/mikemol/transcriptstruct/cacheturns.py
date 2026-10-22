# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each assistant turn's prompt-cache use, the gap before it and what woke it (W1830, of W1828).

A prompt cache lives about an hour. A turn that rebuilds most of its context (a large
`cache_creation_input_tokens` and a small `cache_read_input_tokens`) is COLD, and a cold turn costs
the whole context again, so an operator who notices one by eye has noticed late. The 2026-10-22
reading of one session's transcript found four cold API calls in 24 h: two after gaps over an hour,
one after a compaction, one after an 84-minute pending question. This module is that reading as a
tracked mode, so a metric producer (W1828) and a human read the same parse.

⚑ A TURN IS ONE API CALL, NOT ONE RECORD: a response with several content blocks is written as
several assistant records that repeat the same usage, so records sharing a `message.id` are folded
into the first. Counting records would triple a cold call.

⚑ THE GAP IS TO THE PREVIOUS TURN'S TIMESTAMP, the first turn of a transcript has none (None), and
a negative gap from clock skew is reported as 0.

⚑ WHAT WOKE A TURN is read from the nearest user record before it, by the marker its text carries,
because the harness gives no field for it: `cron` (a scheduled tick prompt), `notification` (a
background-task event), `peer` (a cross-session message), `stop-hook` (a Stop block's feedback),
`tool-result` (the answer to a tool call), else `operator-or-other`. A reading, not a verdict.

⚑ COLD IS A THRESHOLD, NOT A FACT ABOUT THE CACHE: `COLD_CREATION` tokens created and less than
`COLD_READ_SHARE` of the turn's input read. It is stated here so a reader can change it in one
place.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from mikemol.transcriptstruct.records import AssistantRecord, Record, UserRecord

COLD_CREATION = 20_000
COLD_READ_SHARE = 0.5
_MARKERS = (
    ("paths-forward tick", "cron"),
    ("task-notification", "notification"),
    ("cross-session-message", "peer"),
    ("Stop hook", "stop-hook"),
)


@dataclass(frozen=True, slots=True)
class Turn:
    """One API call: where, when, which model, its cache use, the gap before it and its waker."""

    line: int
    at: str
    model: str
    cache_read: int
    cache_creation: int
    input_tokens: int
    gap_s: float | None
    woke: str

    @property
    def cold(self) -> bool:
        """Say whether this turn rebuilt most of its context.

        Returns:
            True when it created at least `COLD_CREATION` tokens and read under `COLD_READ_SHARE`
            of its input.

        """
        total = self.cache_read + self.cache_creation + self.input_tokens
        return self.cache_creation >= COLD_CREATION and self.cache_read < COLD_READ_SHARE * total


def _dict(value: object) -> dict[str, object]:
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _count(usage: dict[str, object], key: str) -> int:
    value = usage.get(key)
    return value if isinstance(value, int) else 0


def waker(record: UserRecord) -> str:
    """Name what a user-role record is: the scheduler, a notification, a peer, a hook or a result.

    Returns:
        one of `cron`, `notification`, `peer`, `stop-hook`, `tool-result`, `operator-or-other`.

    """
    text = record.content if isinstance(record.content, str) else json.dumps(record.content)
    for marker, name in _MARKERS:
        if marker in text:
            return name
    return "tool-result" if record.raw.get("toolUseResult") is not None else "operator-or-other"


def _seconds(stamp: str) -> float:
    return datetime.fromisoformat(stamp).timestamp()


def _turn(record: AssistantRecord, previous: Turn | None, woke: str) -> Turn | None:
    # The turn a record starts, or None when it carries no usage or timestamp.
    message = _dict(record.raw.get("message"))
    usage = _dict(message.get("usage"))
    stamp = record.raw.get("timestamp")
    if not usage or not isinstance(stamp, str):
        return None
    gap = None if previous is None else max(_seconds(stamp) - _seconds(previous.at), 0.0)
    return Turn(
        record.line,
        stamp,
        str(message.get("model")),
        _count(usage, "cache_read_input_tokens"),
        _count(usage, "cache_creation_input_tokens"),
        _count(usage, "input_tokens"),
        gap,
        woke,
    )


def turns(records: Iterable[Record]) -> list[Turn]:
    """Read the transcript's API calls with their cache use, gap and waker.

    Returns:
        one `Turn` per distinct `message.id` that carries usage, in transcript order.

    """
    found: list[Turn] = []
    seen: set[str] = set()
    woke = "operator-or-other"
    for record in records:
        if isinstance(record, UserRecord):
            woke = waker(record)
            continue
        if not isinstance(record, AssistantRecord) or record.is_sidechain:
            continue
        ident = _dict(record.raw.get("message")).get("id")
        if not isinstance(ident, str) or ident in seen:
            continue
        turn = _turn(record, found[-1] if found else None, woke)
        if turn is not None:
            seen.add(ident)
            found.append(turn)
    return found

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Rung 2 of the idle-escalation ladder: a Stop that leaves ready work and no progress is blocked.

The operator saw sessions go idle with ready work even after the tick-close refused (host transcript
695f3e0a, line 92550): a refusal the session can ignore is not a control. This is the next rung, at
the one place every turn passes through. When the turn is ending, ready cards exist and no card
ADVANCED since the turn began, the hook blocks and names the top ready card and the remedy.

⚑ THE CAP IS COUNTED FROM THE TRANSCRIPT, NOT TRUSTED TO A FLAG. `stop_hook_active` says only that a
Stop block already happened, so a cap of two needs the count: the reader (`--turn-start`, W1903)
returns the Stop blocks since the turn began, and at `CAP` the hook lets the turn end. A broken
guard therefore cannot trap a turn, and each block it did write is a record in the transcript
(the block's feedback), which is the rung's auditable mark.

⚑ A READING THAT DID NOT HAPPEN NEVER STOPS A TURN. No transcript path, a reader that cannot run or
prints something else, a queue that cannot be read, a turn start that does not parse: each answers
None, and the turn ends as it would have. The reader is found and run as `hold_lift` finds and runs
it, not a second way.

⚑ A COMMIT IS ADVANCEMENT, A MARK IS NOT (W1950, part 2): the cards a commit since the turn began
cites (`Waypoint:` trailers in `git log --since`) are handed to `idle_card`, which counts a card
that is finished, blocked with a named blocker, or cited by one of them. A git that cannot be run
names no card, so the other two signals decide alone.
"""

import json
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from mikemol.hooks.hold_lift import reader_path, run_reader
from mikemol.hooks.idle_progress import idle_card
from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.round_order import order as round_of
from mikemol.hooks.runproc import run_process
from mikemol.hooks.stamps import parse_time

CAP = 2
QUEUE = Path(".claude") / "paths-forward.json"
# ⚑ THE MARK FOLLOWS REAL WORK (W2316): this text used to tell a session to TAKE a named card, and a
# mark made only to quiet it was an empty mark the round check then punished. It now asks for the
# advance and names the mark as the thing to make once the work has begun.
REASON = (
    "ready work and no card moved this turn: advance {card} with real work (when you begin it, "
    "mark it: mikemol-paths-forward --state {queue} --update {card} --status working; a mark "
    "nothing is building is refused when a ready round card is passed over), or block it on a "
    "named blocker, before ending the turn"
)
_TRAILER = re.compile(r"^Waypoint: (W\d+)", re.MULTILINE)
TurnReader = Callable[[str], dict[str, object] | None]
Landed = Callable[[Path, datetime], frozenset[str]]


def read_turn(transcript: str) -> dict[str, object] | None:
    """Ask the transcript reader where the latest turn began.

    Returns:
        its `{line, at, blocks}` record; None when the reader is absent, fails, or says null.

    """
    binary = reader_path(os.environ)
    if binary is None:
        return None
    code, said = run_reader([binary, transcript, "--turn-start"])
    if code != 0:
        return None
    try:
        answer: object = json.loads(said)
    except ValueError:
        return None
    return as_record(answer) or None


def commit_cards(root: Path, since: datetime) -> frozenset[str]:
    """Name the cards a commit since `since` cites in a `Waypoint:` trailer.

    Returns:
        the symbols; empty when git cannot be run or the log cannot be read.

    """
    code, said = run_process(["git", "log", f"--since={since.isoformat()}", "--format=%B"], root)
    if code != 0:
        return frozenset()
    return frozenset(str(found.group(1)) for found in _TRAILER.finditer(said))


def idle_reason(
    payload: dict[str, object],
    root: Path,
    reader: TurnReader = read_turn,
    landed: Landed = commit_cards,
) -> str | None:
    """Decide whether this Stop should be blocked for idling with ready work.

    Returns:
        the reason naming the top ready card; None when no reading is possible, the cap is
        reached, or a card advanced this turn or none is ready.

    """
    transcript = text_of(payload.get("transcript_path"))
    turn = reader(transcript) if transcript else None
    start = parse_time(text_of(turn.get("at"))) if turn else None
    blocks = turn.get("blocks") if turn else None
    if start is None or not isinstance(blocks, int) or blocks >= CAP:
        return None
    try:
        queue: object = json.loads((root / QUEUE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    # W1950: the published round decides which ready card is named; no round is the queue's order.
    card = idle_card(queue, start, round_of(root, datetime.now(UTC)), landed(root, start))
    return None if card is None else REASON.format(card=card, queue=QUEUE)

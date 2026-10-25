# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the published round and the queue, and judge the working set against them (W1942).

`round_check` is the pure judgement; this is the reading it needs: where nemik publishes the round
(`round.json`, nemik:W1025), how old a round may be before it is ignored, and which cards of the
queue are ready and working.

⚑ NO ROUND MEANS NO REFUSAL, in every way a round can be absent: no file, an unreadable file or
queue, a file with no stamp, a stamp older than STALE, or no rows for this repository. A guard that
refuses on a missing input traps a turn on something the session cannot fix.

⚑ THE STALENESS BOUND IS CHOSEN, NOT LEARNED. nemik rewrites the file on a host timer whose period
is not yet known (luthen-observability schedules it); three hours is about four land intervals, so a
round survives a normal pause and dies with an abandoned timer. Replace it with a learned bound
when the timer's period exists.

⚑ THE REPOSITORY IS THE QUEUE DIRECTORY'S NAME (`mtools` for the checkout `mtools`), the same name
nemik publishes rows under.

CONSUMED BY: the tick-stop hook (W1942); the stack submit is the card's next part.
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.round_check import composition, round_symbols
from mikemol.hooks.stamps import parse_time

STALE = timedelta(hours=3)
ENV = "MIKEMOL_ROUND_FILE"
_QUEUE = ".claude/paths-forward.json"
_AS_OF = re.compile(r'"as_of"\s*:\s*"([^"]+)"')


def round_path() -> Path:
    """Find the round file.

    Returns:
        the path named by MIKEMOL_ROUND_FILE, else `round.json` in the nemik cache directory.

    """
    named = os.environ.get(ENV)
    return Path(named) if named else Path.home() / ".cache" / "nemik" / "round.json"


def published_at(text: str) -> datetime | None:
    """Read the stamp the round file carries on its head line.

    Returns:
        the aware time of `as_of`; None when the file has no usable stamp.

    """
    found = _AS_OF.search(text)
    if found is None:
        return None
    return parse_time(text[found.start(1) : found.end(1)])


def _symbols(queue: object, status: str) -> list[str]:
    raw = as_record(queue).get("waypoints")
    cards = [as_record(card) for card in raw] if isinstance(raw, list) else []
    return [text_of(card.get("symbol")) for card in cards if card.get("status") == status]


def refusals(queue: object, text: str, repo: str, now: datetime) -> list[str]:
    """Judge a queue against a round file's text.

    Returns:
        the refusals of `composition`; empty when the round is stale, unstamped or has no rows
        for `repo`.

    """
    stamp = published_at(text)
    if stamp is None or now - stamp > STALE:
        return []
    return composition(
        round_symbols(text, repo), _symbols(queue, "ready"), _symbols(queue, "working")
    )


def round_reason(directory: Path, now: datetime, round_file: Path | None = None) -> str | None:
    """Read the round and the queue under `directory` and judge them.

    Returns:
        the refusals joined into one reason; None when there is nothing to refuse or an input
        cannot be read.

    """
    try:
        text = (round_file or round_path()).read_text(encoding="utf-8")
        queue: object = json.loads((directory / _QUEUE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    found = refusals(queue, text, directory.name, now)
    return " | ".join(found) if found else None

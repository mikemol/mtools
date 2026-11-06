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

⚑ THE DATA THE BOUND IS LEARNED FROM IS KEPT HERE (W1949): `note_stamp` appends each newly seen
`as_of` once to `<git dir>/mtools/round-stamps`, on the read the hook already makes, with no
timer of its own. The spacing of that log is the timer's real period.

⚑ THE REPOSITORY IS THE QUEUE DIRECTORY'S NAME (`mtools` for the checkout `mtools`), the same name
nemik publishes rows under.

⚑ A MARK FOR A CARD BEING BUILT IS ADMITTED (W2316, nemik:W2027): a working card is not "outside"
when a live stack names it (`in_gate`) or a held scratch tree is cut for it (`held_trees`). What is
left to refuse is an EMPTY mark, one nothing is building, that passes over a ready round card. A
scratch tree is held while it EXISTS: `mikemol-scratch open` cuts it and `close` removes it, so
that protocol, not a clock, says a card is being built (a leftover tree admits its card's mark).
⚑ A READING THAT FAILED IS NEVER ADMITTED SILENTLY: an unreadable commit queue or no declared
scratch root exempts nothing, so the refusal stands; an unreadable commit queue is also SAID in
the refusal, so a mark refused only because the stack could not be seen is not mistaken for an
empty one.

CONSUMED BY: the tick-stop hook and the stack submit (`now_reason`, W1948).
"""

import json
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mikemol.hooks.commit_counts import live
from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.round_check import composition, round_symbols
from mikemol.hooks.scratch import ScratchError, path_for, root_of
from mikemol.hooks.stamps import parse_time

STALE = timedelta(hours=3)
ENV = "MIKEMOL_ROUND_FILE"
_COUNTS = ".git/mtools/commit.counts"
_QUEUE = ".claude/paths-forward.json"
_STAMPS = ".git/mtools/round-stamps"
_AS_OF = re.compile(r'"as_of"\s*:\s*"([^"]+)"')


def round_path() -> Path:
    """Find the round file.

    Returns:
        the path named by MIKEMOL_ROUND_FILE, else `round.json` in luthen's nemik-export tree
        (luthen-observability:W1612 writes it there hourly).

    """
    named = os.environ.get(ENV)
    return Path(named) if named else Path.home() / ".local/share/luthen/nemik-export/round.json"


def published_at(text: str) -> datetime | None:
    """Read the stamp the round file carries on its head line.

    Returns:
        the aware time of `as_of`; None when the file has no usable stamp.

    """
    found = _AS_OF.search(text)
    if found is None:
        return None
    return parse_time(text[found.start(1) : found.end(1)])


def note_stamp(directory: Path, stamp: datetime) -> bool:
    """Append a round stamp to the log when it is not the last one kept.

    ⚑ ONE LINE PER DISTINCT STAMP: the hook reads the file every turn, and the same `as_of` read
    a hundred times is one observation of the timer, not a hundred. A file system that refuses
    changes nothing about the judgement, so a failure is reported and never raised. A READ NEVER
    CREATES THE DIRECTORY: `<git dir>/mtools` belongs to the tools that run in a repository, so a
    checkout none of them has run in keeps no log.

    Returns:
        True when a line was appended; False when the stamp was already the last line, the
        directory is absent, or the log could not be written.

    """
    path = directory / _STAMPS
    line = stamp.isoformat()
    if not path.parent.is_dir():
        return False
    try:
        kept = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
        if kept and kept[-1] == line:
            return False
        with path.open("a", encoding="utf-8") as log:
            log.write(f"{line}\n")
    except OSError:
        return False
    return True


def _symbols(queue: object, status: str) -> list[str]:
    raw = as_record(queue).get("waypoints")
    cards = [as_record(card) for card in raw] if isinstance(raw, list) else []
    return [text_of(card.get("symbol")) for card in cards if card.get("status") == status]


def in_gate(directory: Path) -> frozenset[str]:
    """Name the cards a live submission of `directory` cites.

    ⚑ A CARD A QUEUED OR GATING STACK NAMES IS IN PROGRESS BY CONSTRUCTION (github-8f, W2000),
    and the commit queue knows it: an entry counts only while its pid and start time both match,
    so a dead stack's leftovers exempt nothing. A mark made just to quiet the hook is on no
    stack, so it stays outside.

    Returns:
        the waypoints of every live entry; empty when there is no queue map.

    """
    return frozenset(w for row in live(directory / _COUNTS) for w in row.waypoints)


def queue_readable(directory: Path) -> bool:
    """Say whether the commit queue map can be read, an absent one counting as readable.

    ⚑ ABSENT IS NOT BROKEN: nothing queued writes no map. A map that exists and is not a JSON object
    is the case `in_gate` cannot tell from an empty queue, and the refusal says so.

    Returns:
        False only when the map exists and cannot be read as a JSON object.

    """
    path = directory / _COUNTS
    if not path.is_file():
        return True
    try:
        doc: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(doc, dict)


def held_trees(directory: Path, working: list[str], environ: Mapping[str, str]) -> frozenset[str]:
    """Name the working cards a scratch tree of `directory` is cut for.

    Returns:
        the symbols among `working` whose worktree exists under the declared scratch root; empty
        when no root is declared or a symbol is not `W<n>`.

    """
    try:
        root = root_of(environ)
        return frozenset(s for s in working if path_for(root, directory, s).is_dir())
    except ScratchError:
        return frozenset()


def refusals(
    queue: object, text: str, repo: str, now: datetime, cited: frozenset[str] = frozenset()
) -> list[str]:
    """Judge a queue against a round file's text.

    Returns:
        the refusals of `composition`, a working card named in `cited` not counted as outside;
        empty when the round is stale, unstamped or has no rows for `repo`.

    """
    stamp = published_at(text)
    if stamp is None or now - stamp > STALE:
        return []
    doing = [symbol for symbol in _symbols(queue, "working") if symbol not in cited]
    # W2005: a READY card a live submission names is in progress too (its status was not updated),
    # so the round does not demand it be taken (nemik-84).
    waiting = [symbol for symbol in _symbols(queue, "ready") if symbol not in cited]
    return composition(round_symbols(text, repo), waiting, doing)


def round_reason(
    directory: Path,
    now: datetime,
    round_file: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Read the round and the queue under `directory` and judge them.

    Returns:
        the refusals joined into one reason, saying so when the commit queue could not be read;
        None when there is nothing to refuse or an input cannot be read.

    """
    try:
        text = (round_file or round_path()).read_text(encoding="utf-8")
        queue: object = json.loads((directory / _QUEUE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    seen = published_at(text)
    if seen is not None:
        note_stamp(directory, seen)
    working = _symbols(queue, "working")
    cited = in_gate(directory) | held_trees(
        directory, working, os.environ if environ is None else environ
    )
    found = refusals(queue, text, directory.name, now, cited)
    if not found:
        return None
    blind = (
        ""
        if queue_readable(directory)
        else (" (the commit queue could not be read, so a mark on a live stack is not exempted)")
    )
    return " | ".join(found) + blind


def now_reason(directory: Path) -> str | None:
    """Judge `directory`'s queue against the round as of the wall clock.

    Returns:
        what `round_reason` says at this moment; the stack submit's seam, since it has no clock
        of its own.

    """
    # ⚑ AT SUBMIT NO SCRATCH TREE EXEMPTS ANYTHING (W2316): the submit refuses a stack whose card is
    # outside the round while a ready round card is passed over, however honest the work; an empty
    # environment declares no scratch root. Only the Stop hook, which judges marks, admits a tree.
    return round_reason(directory, datetime.now(UTC), None, {})

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Send each recent session's latest cache turn to the metrics store (W1828).

A session whose prompt cache expired pays for its whole context again, and nobody sees it unless
they read the transcript. `mikemol-transcriptstruct --cache-turns` (W1830) reads each API call's
cache use, the gap before it and whether it was cold; this sends the LATEST turn of every recent
session as four gauges, labelled by session and model, through `mikemol-otlp metrics`:

    mikemol.session.cache_read      tokens read from the cache
    mikemol.session.cache_creation  tokens written to it
    mikemol.session.gap_s           seconds since the session's previous turn
    mikemol.session.cold            1 when the turn rebuilt most of its context, else 0

and one unlabelled gauge, `mikemol.session.cache.sessions`, the number of transcripts read.

⚑ LATEST TURN ONLY, SO THE SERIES COUNT IS THE SESSION COUNT (luthen-observability:W1525, who
register the `mikemol_session_` family with a ceiling): one sample per turn would put a new series
behind every turn. A gauge answers "is this session cold now", and its history is the store's.

⚑ THE COUNT GAUGE IS SENT ON EVERY RUN, 0 WHEN NO SESSION WAS READ: the four per-session gauges are
event-like (a session with no recent turn has no series), so a continuous sibling is what lets a
dead producer show as a missing series and not a quiet zero.

⚑ THE CAP IS A COUNT, `MAX_SESSIONS`, AND A WINDOW BESIDE IT: the most recently written
transcripts, at most `MAX_SESSIONS`, and only those written within `MAX_AGE_S`, because a dead
session's last turn would otherwise stay cold in the store for ever.

⚑ A TRANSCRIPT WITH NO TURN, A READER THAT FAILS AND A STORE THAT IS NOT NAMED SEND NOTHING FOR THE
SESSION: it is left out of this pass rather than reported as warm, because absence of a reading is
not a warm cache. A first turn has no gap, and its `gap_s` is left out and not sent as 0.

⚑ THE SEND IS WAITED FOR, AND A LOST ONE IS NOT EXIT 0 (luthen-observability, 2026-10-23,
first live pass: exit 0 in 28 s and no series in the store): the emitter used to be a
detached child, which a oneshot unit's cgroup ends when the main process exits, before it
sent. Each batch now runs to completion; a non-zero exit from the emitter is written to
stderr and the pass exits `EXIT_SEND_FAILED`, so a lost send shows in the unit's status.

CONSUMED BY: the `mikemol-session-cache` console script (a timer's job, one pass per run).
"""

import json
import os
import shutil
import sys
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import cast

from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.runproc import run_process, run_with_stdin

SERVICE = "mikemol-session"
NAMESPACE = "mtools"
COUNT_NAME = "mikemol.session.cache.sessions"
READER_ENV = "MIKEMOL_TRANSCRIPTSTRUCT_BIN"
READER = "mikemol-transcriptstruct"
MAX_AGE_S = 6 * 3600
MAX_SESSIONS = 40
BATCH = 100
EXIT_OK = 0
EXIT_NO_READER = 3
EXIT_NO_STORE = 4
EXIT_SEND_FAILED = 5
SEND_NOTE_CHARS = 200
Send = Callable[[Sequence[str], str], tuple[int, str]]
Run = Callable[[Sequence[str], Path], tuple[int, str]]


def latest(text: str) -> dict[str, object] | None:
    """Take the last turn from `--cache-turns` output.

    Returns:
        the final JSON object line (the `#` count line and anything else is skipped), or None.

    """
    for line in reversed(text.splitlines()):
        if not line.startswith("{"):
            continue
        try:
            parsed = cast("object", json.loads(line))
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return cast("dict[str, object]", parsed)
    return None


def _number(turn: dict[str, object], key: str) -> float | None:
    value = turn.get(key)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _line(name: str, value: float, fields: dict[str, str]) -> str:
    record: dict[str, object] = {"name": name, "value": value, "fields": fields}
    return json.dumps(record)


def rows(session: str, turn: dict[str, object]) -> list[str]:
    """Spell a session's latest turn as the lines `mikemol-otlp metrics` reads.

    Returns:
        one JSON line per gauge: read, creation, cold, and the gap when the turn has one.

    """
    fields = {"session": session, "model": str(turn.get("model", ""))}
    values = {
        "mikemol.session.cache_read": _number(turn, "cache_read"),
        "mikemol.session.cache_creation": _number(turn, "cache_creation"),
        "mikemol.session.gap_s": _number(turn, "gap_s"),
        "mikemol.session.cold": 1.0 if turn.get("cold") is True else 0.0,
    }
    return [_line(name, value, fields) for name, value in values.items() if value is not None]


def recent(
    root: Path, now_s: float, max_age_s: float = MAX_AGE_S, cap: int = MAX_SESSIONS
) -> list[Path]:
    """List the newest transcripts under `root` written to within the window.

    Returns:
        at most `cap` `<project>/<session>.jsonl` files modified in the last `max_age_s`, the most
        recently written first.

    """
    stamped = [(p.stat().st_mtime, p) for p in root.glob("*/*.jsonl")]
    fresh = sorted((s for s in stamped if now_s - s[0] <= max_age_s), reverse=True)
    return [path for _, path in fresh[:cap]]


def batches(lines: Sequence[str], size: int = BATCH) -> Iterable[str]:
    """Cut the lines into stdin texts small enough to write before the child reads.

    Returns:
        one newline-joined text per `size` lines.

    """
    return ("\n".join(lines[i : i + size]) for i in range(0, len(lines), size))


def collect(paths: Sequence[Path], reader: str, run: Run) -> list[str]:
    """Read each transcript's latest turn and spell it as gauge lines.

    Returns:
        the count gauge first, then all the sessions' lines in turn; a transcript whose reader
        fails or that has no turn is left out of the lines but not of the count's denominator.

    """
    found = [_line(COUNT_NAME, float(len(paths)), {})]
    for path in paths:
        status, out = run([reader, str(path), "--cache-turns"], path.parent)
        turn = latest(out) if status == 0 else None
        if turn is not None:
            found += rows(path.stem, turn)
    return found


def send_all(send: Send, command: Sequence[str], texts: Iterable[str]) -> int:
    """Send every batch and say so on stderr for each one that failed.

    Returns:
        how many batches the emitter did not accept.

    """
    lost = 0
    for text in texts:
        code, said = send(command, text)
        if code != 0:
            lost += 1
            note = said.strip()[-SEND_NOTE_CHARS:]
            sys.stderr.write(f"mikemol-session-cache: send failed (exit {code}): {note}\n")
    return lost


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    run: Run = run_process,
    send: Send = run_with_stdin,
    now_s: float | None = None,
) -> int:
    """Send one pass of every recent session's latest cache turn.

    Returns:
        `EXIT_OK` after the pass (the count gauge is sent even when no session was read),
        `EXIT_NO_READER` when the transcript reader cannot be found, `EXIT_NO_STORE` when there
        is no emitter or store, `EXIT_SEND_FAILED` when any batch's send exited non-zero.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    environ = os.environ if env is None else env
    reader = environ.get(READER_ENV) or shutil.which(READER)
    program = binary(environ)
    if reader is None:
        return EXIT_NO_READER
    if program is None or not store_named(environ):
        return EXIT_NO_STORE
    root = Path(args[0]) if args else Path.home() / ".claude" / "projects"
    paths = recent(root, time.time() if now_s is None else now_s)
    command = [program, "metrics", "--service", SERVICE, "--namespace", NAMESPACE]
    lost = send_all(send, command, batches(collect(paths, reader, run)))
    return EXIT_SEND_FAILED if lost else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

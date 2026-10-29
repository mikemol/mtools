# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W813: after a compaction, say where the durable state lives and what the host looks like now.

A compaction replaces the conversation with a summary, and a summary keeps the conclusions and loses
the working state: which detached commits were running, which procedure file holds the rules, what
the machine was doing. The state itself lives on disk, in queues and tracked files; what is lost is
the knowledge of WHERE to look. This hook (SessionStart, matcher `compact`) puts that back.

It adds two things as context:
  - the project's own notes, `<cwd>/.claude/after-compaction.md`, a small tracked file the project
    authors: POINTERS to where durable state lives, not state itself, so it cannot go stale;
  - the live host facts (zram use and the tick lock), read now, at the moment they are wanted. That
    is why there is no PreCompact half: a snapshot taken before compaction is already old when it is
    read, and this reads the same facts fresh.

⚑ A SESSION START MUST NEVER BE BLOCKED. This hook only adds context, exits 0 on every path, and
passes untouched a payload whose `source` is present and is not `compact`.

⚑ A MISSING OR UNREADABLE NOTES FILE IS SAID, NOT SKIPPED: the context then names the path it looked
for, so a project that has not written one learns it can.

⚑ NO ARMING VARIABLE: it adds context with no advisory mode, and this file must not spell that
variable's name (the wiring arm reads a module that does as one that arms).
"""

import json
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TextIO

from mikemol.hooks.host_facts import Headroom, zram_headroom
from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.tick_gate import facts_line
from mikemol.hooks.tick_stop import payload_dir, payload_lock

# The project's pointers to its durable state, relative to the session's directory.
NOTES = Path(".claude") / "after-compaction.md"

# A notes file is pointers, so it is short; one that is not is cut here and says so.
MAX_NOTES_CHARS = 6000

COMPACT = "compact"

# W2117: where a compaction's frozen facts go, beside the transcript they describe.
FREEZE_DIR = "compaction"
READ_CHUNK = 1 << 20
VALIDATOR_LINE = "run the compaction-summary validator over {frozen}"


def freeze_dir(transcript: Path, session: str) -> Path:
    """Name the directory that holds a session's compaction records.

    ⚑ BESIDE THE TRANSCRIPT, NOT IN A TEMPORARY DIRECTORY: the transcript lives under the user's
    project directory on durable storage, and a record kept in a scratch area is lost with the
    reboot that loses the scratch area (2026-10-29).

    Returns:
        `<transcript's directory>/compaction/<session>`.

    """
    return transcript.parent / FREEZE_DIR / session


def latest_freeze(directory: Path) -> Path | None:
    """Find the compaction record with the highest number.

    Returns:
        its path, or None when the directory holds none (or does not exist).

    """
    found = [(int(path.stem), path) for path in directory.glob("*.json") if path.stem.isdecimal()]
    return max(found)[1] if found else None


def _line_bound(transcript: Path) -> int | None:
    # How many lines the transcript holds now, counted in chunks; None when it cannot be read.
    try:
        with transcript.open("rb") as handle:
            return sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(READ_CHUNK), b""))
    except OSError:
        return None


def freeze(payload: dict[str, object], now: datetime) -> Path | None:
    """Write the facts of a compaction that is about to happen (W2117, no model involved).

    ⚑ ONLY FACTS ARE FROZEN: the transcript line the compaction will cover (the bound), the path of
    the transcript, the compaction's trigger, and the path of the PRIOR record (so a validator can
    follow the chain to the earlier summary's bound). Nothing is summarised here.

    ⚑ A COMPACTION IS NEVER BLOCKED: a payload without a readable transcript, or a directory that
    cannot be written, freezes nothing and answers None.

    Returns:
        the record's path, `<freeze_dir>/<n>.json`; None when nothing was written.

    """
    named = text_of(payload.get("transcript_path"))
    if not named:
        return None
    transcript = Path(named)
    session = text_of(payload.get("session_id")) or transcript.stem
    bound = _line_bound(transcript)
    if bound is None:
        return None
    directory = freeze_dir(transcript, session)
    prior = latest_freeze(directory)
    number = (int(prior.stem) if prior is not None else 0) + 1
    record: dict[str, object] = {
        "n": number,
        "session": session,
        "trigger": text_of(payload.get("trigger")),
        "transcript": str(transcript),
        "line_bound": bound,
        "prior": str(prior) if prior is not None else "",
        "at": now.isoformat(),
    }
    target = directory / f"{number}.json"
    staging = target.with_name(f"{target.name}.tmp")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        staging.write_text(json.dumps(record), encoding="utf-8")
        staging.replace(target)
    except OSError:
        return None
    return target


def read_notes(directory: Path) -> str | None:
    """Read the project's after-compaction notes, cut to MAX_NOTES_CHARS.

    Returns:
        the notes (with a marker when cut); None when the file is missing or unreadable.

    """
    try:
        text = (directory / NOTES).read_text(encoding="utf-8")
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    if len(text) <= MAX_NOTES_CHARS:
        return text
    return text[:MAX_NOTES_CHARS] + "\n... (notes cut here)"


def context(directory: Path, notes: str | None, facts: str, frozen: Path | None = None) -> str:
    """Compose the context a compaction gets back.

    Returns:
        the notes (or the statement that there are none, naming where they would be), then the
        live host facts, then, when a PreCompact record exists (W2117), the one line that tells the
        session to run the compaction-summary validator over it.

    """
    if notes is None:
        head = f"after compaction: no notes file at {directory / NOTES}; write one (pointers only)."
    else:
        head = f"after compaction, this project's notes ({NOTES}):\n{notes.rstrip()}"
    body = f"{head}\n{facts}"
    return body if frozen is None else f"{body}\n{VALIDATOR_LINE.format(frozen=frozen)}"


def _frozen_for(payload: dict[str, object]) -> Path | None:
    # The newest compaction record of the session this SessionStart belongs to, if any.
    named = text_of(payload.get("transcript_path"))
    if not named:
        return None
    transcript = Path(named)
    session = text_of(payload.get("session_id")) or transcript.stem
    return latest_freeze(freeze_dir(transcript, session))


def run(
    payload: dict[str, object],
    read_headroom: Callable[[], Headroom | None],
    out: TextIO,
) -> int:
    """Add the after-compaction context for one SessionStart payload.

    Returns:
        0 always: a session start is never blocked.

    """
    source = text_of(payload.get("source"))
    if source and source != COMPACT:
        return 0
    directory = payload_dir(payload)
    facts = facts_line(read_headroom(), payload_lock(payload))
    added: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context(
                directory, read_notes(directory), facts, _frozen_for(payload)
            ),
        }
    }
    out.write(json.dumps(added) + "\n")
    return 0


def precompact() -> int:
    """Read the PreCompact payload on stdin and freeze the compaction's facts (W2117).

    An unreadable payload freezes nothing and says so on stderr: a compaction must not be blocked.

    Returns:
        0 always.

    """
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        sys.stderr.write("precompact: the payload was not JSON; nothing frozen\n")
        return 0
    freeze(as_record(raw), datetime.now().astimezone())
    return 0


def main() -> int:
    """Read the SessionStart payload on stdin and add the context.

    An unreadable payload adds nothing and says so: a session start must not be blocked by it.

    Returns:
        the exit code from `run`, or 0.

    """
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        sys.stderr.write("after-compaction: the payload was not JSON; nothing added\n")
        return 0
    return run(as_record(raw), zram_headroom, sys.stdout)

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

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks.host_facts import zram_headroom
from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.tick_gate import facts_line
from mikemol.hooks.tick_stop import payload_dir, payload_lock

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO

    from mikemol.hooks.host_facts import Headroom

# The project's pointers to its durable state, relative to the session's directory.
NOTES = Path(".claude") / "after-compaction.md"

# A notes file is pointers, so it is short; one that is not is cut here and says so.
MAX_NOTES_CHARS = 6000

COMPACT = "compact"


def read_notes(directory: Path) -> str | None:
    """Read the project's after-compaction notes, cut to MAX_NOTES_CHARS.

    Returns:
        the notes (with a marker when cut); None when the file is missing or unreadable.

    """
    try:
        text = (directory / NOTES).read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    if len(text) <= MAX_NOTES_CHARS:
        return text
    return text[:MAX_NOTES_CHARS] + "\n... (notes cut here)"


def context(directory: Path, notes: str | None, facts: str) -> str:
    """Compose the context a compaction gets back.

    Returns:
        the notes (or the statement that there are none, naming where they would be), then the
        live host facts.

    """
    if notes is None:
        head = f"after compaction: no notes file at {directory / NOTES}; write one (pointers only)."
    else:
        head = f"after compaction, this project's notes ({NOTES}):\n{notes.rstrip()}"
    return f"{head}\n{facts}"


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
            "additionalContext": context(directory, read_notes(directory), facts),
        }
    }
    out.write(json.dumps(added) + "\n")
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

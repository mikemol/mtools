# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Tell a session when the canonical loop prompt changed since its last tick (W1524).

The operator edits `~/github/.claude/loop-prompt.md` and expects every session to follow it from
its next tick, but a session only re-reads it when it remembers to, and on 2026-10-17 the newest
Fleet practice (ready means pickable, block unmanifested cards on an atomizing card, waiting cards
blocked on the real ask) had not been picked up by a session that was armed to follow the file.
Nobody should depend on noticing, so `--tick-open` prints what changed.

⚑ THE LAST READING IS KEPT BESIDE THE QUEUE'S GIT DIRECTORY, NOT IN THE QUEUE: `<git dir>/mtools/
loop-prompt.seen` holds the whole text the previous tick saw, so the notice can say which lines
were added and removed instead of only that a hash differs. It is untracked, per checkout, and
replaced whole by a rename.

⚑ A PROMPT THAT IS ABSENT SAYS NOTHING. A repo outside `~/github`, or a host without the file, has
no canonical prompt to watch, and a notice about nothing would train the reader to skip notices.

⚑ A CHANGE REPEATS UNTIL IT IS ACKNOWLEDGED (W1563, github-8f 2026-10-18): printing the lines was
never a reading, and a notice shown once and ignored was gone at the next tick, which is how a new
rule was loaded and never noticed. The lines stay at every `--tick-open` until the session records
that it read them with `--prompt-ack` (`acknowledge`).

⚑ THE FIRST READING IS RECORDED, NOT DIFFED: with no earlier text there is nothing to compare, and
the line says so once.
"""

import difflib
import os
from pathlib import Path

PROMPT_NAME = "loop-prompt.md"
SEEN_NAME = "loop-prompt.seen"
SHOWN = 12
"""How many changed lines a notice lists before it says how many more there are."""


def prompt_of(project_root: Path) -> Path:
    """Name the canonical prompt for a repo: `.claude/loop-prompt.md` in the directory above it.

    Returns:
        the path, which may not exist.

    """
    return project_root.parent / ".claude" / PROMPT_NAME


def _changed(old: str, new: str) -> list[str]:
    # The added and removed lines of a change, marked, with the diff headers left out.
    delta = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
    return [line for line in delta if line[:1] in {"+", "-"} and line[:3] not in {"+++", "---"}]


def remember(seen: Path, text: str) -> None:
    """Replace the remembered reading whole; a failed write only repeats a later notice."""
    try:
        seen.parent.mkdir(parents=True, exist_ok=True)
        staging = seen.with_name(f"{seen.name}.{os.getpid()}.tmp")
        staging.write_text(text, encoding="utf-8")
        staging.replace(seen)
    except OSError:
        return


def acknowledge(prompt: Path, seen: Path) -> int | None:
    """Record the canonical prompt as read, and confirm the record took (W1562, github-8f).

    ⚑ AN ACKNOWLEDGEMENT THAT CAN FAIL SILENTLY IS NOT ONE: `remember` ignores a failed write,
    which is right for a notice and wrong here, so the record is read back before it is claimed.

    Returns:
        the number of lines acknowledged, or None when the prompt is absent or the record did not
        take.

    """
    try:
        now = prompt.read_text(encoding="utf-8")
    except OSError:
        return None
    remember(seen, now)
    try:
        taken = seen.read_text(encoding="utf-8") == now
    except OSError:
        return None
    return len(now.splitlines()) if taken else None


def notice(prompt: Path, seen: Path) -> list[str]:
    """Compare the canonical prompt with what the previous tick saw, and remember this reading.

    Returns:
        the lines to print: none when the prompt is absent or unchanged, one for a first reading,
        otherwise a heading, up to `SHOWN` changed lines and a count of the rest.

    """
    try:
        now = prompt.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        before: str | None = seen.read_text(encoding="utf-8")
    except OSError:
        before = None
    if before == now:
        return []
    if before is None:
        remember(seen, now)
        return [f"canonical loop prompt: first reading recorded from {prompt}"]
    changes = _changed(before, now)
    shown = changes[:SHOWN]
    rest = len(changes) - len(shown)
    head = (
        f"canonical loop prompt changed since your last tick ({len(changes)} lines): re-read it, "
        "then run --prompt-ack"
    )
    more = [f"  ... and {rest} more"] if rest else []
    return [head, *(f"  {line}" for line in shown), *more]

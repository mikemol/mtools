# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A baseline file that mirrors the cards blocked on one card must stay equal to that list (W2298).

⚑ A BACKLOG MODELED AS A RATCHET IS ONLY AS TRUE AS ITS FILE (operator 2026-11-05, W1667: 128 cards
parked behind one card became `.claude/unmanifested-baseline.txt`, one symbol per line). The census
reads the file's line count, and nothing else keeps it equal to the queue, so a card released
without its line deleted would keep the ratchet high, and a card parked without a line would hide
from it. This check compares the two.

⚑ THE MARK IS A HEADER, NOT A NAME. A file `.claude/<name>-baseline.txt` that carries a line
`# blocked-on: W<n>` is a mirror of the open cards blocked on `W<n>`; no other baseline is read, so
a ratchet that is not a backlog is never judged by it. A file that cannot be read is skipped: the
census already reports it UNREAD.
"""

import re
from pathlib import Path

from mikemol.pathsforward import attach
from mikemol.pathsforward.model import State, strlist, text

_DIR = ".claude"
_PATTERN = "*-baseline.txt"
_MARK = re.compile(r"^#\s*blocked-on:\s*(W\d+)\s*$")
_SYMBOL = re.compile(r"^W\d+$")
_DONE = "done"


def _read(path: Path) -> tuple[str, list[str]] | None:
    """Read a mirror file.

    Returns:
        the symbol its header names and the symbols it lists; None when the file cannot be read or
        carries no header.

    """
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError):
        return None
    parked = next((m.group(1) for line in lines if (m := _MARK.match(line))), None)
    if parked is None:
        return None
    return parked, [line for line in lines if _SYMBOL.match(line)]


def findings(state: State) -> list[str]:
    """Compare each mirror file with the open cards blocked on the card it names.

    Returns:
        one finding per card blocked on the named card and missing from the file, and one per
        symbol listed that is no longer blocked on it; empty when the repository has no mirror.

    """
    root = attach.project_path(text(state.doc, "project_root"))
    found: list[str] = []
    for path in sorted((root / _DIR).glob(_PATTERN)):
        read = _read(path)
        if read is None:
            continue
        parked, listed = read
        blocked = [
            text(w, "symbol")
            for w in state.waypoints
            if text(w, "status") != _DONE and parked in strlist(w, "blocked_on")
        ]
        name = f"{_DIR}/{path.name}"
        found.extend(
            f"{name}: {sym} is blocked on {parked} and not listed (parked and uncounted)"
            for sym in blocked
            if sym not in listed
        )
        found.extend(
            f"{name}: {sym} is listed but no longer blocked on {parked}; delete its line"
            for sym in listed
            if sym not in blocked
        )
    return found

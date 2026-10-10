# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The human views: the derived markdown mirror, and the one-screen queue.

⚑ THE MIRROR SAYS IT IS DERIVED, in its first line (skill section 1): a human who edits it and
watches the edit vanish stops trusting the loop.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from mikemol.pathsforward.digest import v2
from mikemol.pathsforward.model import blocker_index, describe_rank, ordered, strlist, text

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import Json, State

DERIVED = "<!-- DERIVED from the state file by mikemol-paths-forward --render. NEVER EDIT. -->"


WIDTH = 120
SPAN = re.compile(r"(`[^`]*`)")
_TAG = re.compile(r"<[A-Za-z/!?][^\s<>`]*>?")
_BLOCK_START = re.compile(r"^(?:[-+*>]|#+|\d+[.)])$")


def cell(value: str) -> str:
    """Make a value safe inside a markdown table cell.

    Returns:
        the value with pipes escaped and newlines flattened, or an em dash when empty.

    """
    return value.replace("|", "\\|").replace("\n", " ") or "\u2014"


def safe(value: str) -> str:
    """Backtick every `<tag` that would open inline HTML, leaving existing code spans alone.

    Returns:
        the value with each `<` plus letter, `/`, `!` or `?` token wrapped in backticks.

    """
    parts = SPAN.split(value)
    return "".join(p if i % 2 else _TAG.sub(r"`\g<0>`", p) for i, p in enumerate(parts))


def wrap(head: str, body: str, indent: str) -> list[str]:
    """Wrap `head + body` at WIDTH, continuing on `indent`, without dropping a character.

    A continuation line that would open a list, quote or heading is escaped so it stays prose.

    Returns:
        the wrapped lines.

    """
    words = " ".join(safe(body).split()).split(" ")
    lines: list[str] = []
    current = head
    for word in words:
        if word and len(current) + 1 + len(word) > WIDTH and current.strip():
            lines.append(current)
            current = indent + ("\\" if _BLOCK_START.match(word) else "") + word
        else:
            current = f"{current} {word}" if current.strip() and word else current + word
    lines.append(current)
    return lines


def _entry(index: int, w: Json) -> list[str]:
    """Render one waypoint as a list item with its blocked-on and next step beneath.

    Returns:
        the lines of the item.

    """
    head = f"{index}. **{text(w, 'symbol')}** ({text(w, 'status') or '-'})"
    lines = wrap(head, text(w, "title"), "   ")
    blocked = ", ".join(strlist(w, "blocked_on"))
    if blocked:
        lines += wrap("   - blocked on:", blocked, "     ")
    step = text(w, "next_bounded_step")
    if step:
        lines += wrap("   - next:", step, "     ")
    return lines


def mirror(state: State, state_path: Path) -> str:
    """Render the mirror.

    Returns:
        the markdown text.

    """
    lines = [DERIVED, "# paths-forward", ""]
    lines += wrap("state file:", f"`{state_path}`", "")
    lines += [
        "",
        (
            f"counter {state.counter} \u00b7 heartbeat {text(state.doc, 'heartbeat') or '-'} "
            f"\u00b7 job `{text(state.doc, 'job_id') or '-'}` \u00b7 hash `{v2(state.waypoints)}`"
        ),
        "",
        "| # | symbol | status |",
        "|---|---|---|",
    ]
    ranked = ordered(state.waypoints)
    lines += [
        f"| {i} | {cell(text(w, 'symbol'))} | {cell(text(w, 'status'))} |"
        for i, w in enumerate(ranked, 1)
    ]
    lines += ["", "## waypoints", ""]
    for i, w in enumerate(ranked, 1):
        lines += _entry(i, w)
    lines += ["", "## residue", ""]
    for r in state.residue:
        head = f"- **{text(r, 'symbol')}** ({text(r, 'dropped_at')})"
        lines += wrap(head, f"{text(r, 'title')}: {text(r, 'reason')}", "  ")
    if not state.residue:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


def queue(state: State) -> str:
    """Render the queue in the one shared order: working, ready, blocked, then the rest.

    Returns:
        one line per waypoint.

    """
    index = blocker_index(state.waypoints)
    return "\n".join(
        f"{i:>2}. {text(w, 'symbol'):<4} {text(w, 'status'):<8} {text(w, 'title')}"
        f"  \u2014 {text(w, 'rank_reason') or describe_rank(w, state.waypoints, index)}"
        for i, w in enumerate(ordered(state.waypoints), 1)
    )

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The human views: the derived markdown mirror, and the one-screen queue.

⚑ THE MIRROR SAYS IT IS DERIVED, in its first line (skill section 1): a human who edits it and
watches the edit vanish stops trusting the loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.digest import v2
from mikemol.pathsforward.model import ordered, strlist, text

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import State

DERIVED = "<!-- DERIVED from the state file by mikemol-paths-forward --render. NEVER EDIT. -->"


def _cell(value: str) -> str:
    """Make a value safe inside a markdown table cell.

    Returns:
        the value with pipes escaped and newlines flattened, or an em dash when empty.

    """
    return value.replace("|", "\\|").replace("\n", " ") or "\u2014"


def mirror(state: State, state_path: Path) -> str:
    """Render the mirror.

    Returns:
        the markdown text.

    """
    lines = [
        DERIVED,
        f"# paths-forward \u2014 {state_path}",
        "",
        (
            f"counter {state.counter} \u00b7 heartbeat {text(state.doc, 'heartbeat') or '-'} "
            f"\u00b7 job `{text(state.doc, 'job_id') or '-'}` \u00b7 hash `{v2(state.waypoints)}`"
        ),
        "",
        "| # | symbol | status | title | blocked on | next bounded step |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {i} | {_cell(text(w, 'symbol'))} | {_cell(text(w, 'status'))} | "
        f"{_cell(text(w, 'title'))} | {_cell(', '.join(strlist(w, 'blocked_on')))} | "
        f"{_cell(text(w, 'next_bounded_step'))} |"
        for i, w in enumerate(ordered(state.waypoints), 1)
    ]
    lines += ["", "## residue", ""]
    lines += [
        f"- **{text(r, 'symbol')}** ({text(r, 'dropped_at')}) {text(r, 'title')}: "
        f"{text(r, 'reason')}"
        for r in state.residue
    ] or ["- (none)"]
    return "\n".join(lines) + "\n"


def queue(state: State) -> str:
    """Render the queue in the one shared order: working, ready, blocked, then the rest.

    Returns:
        one line per waypoint.

    """
    return "\n".join(
        f"{i:>2}. {text(w, 'symbol'):<4} {text(w, 'status'):<8} {text(w, 'title')}"
        f"  \u2014 {text(w, 'rank_reason')}"
        for i, w in enumerate(ordered(state.waypoints), 1)
    )

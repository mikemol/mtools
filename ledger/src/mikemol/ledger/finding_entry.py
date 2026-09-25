# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Render one roster entry as SOURCE TEXT, and locate where it goes.

Moved from substrate (N-a row 6).

⚑⚑⚑ A RENDERER, NOT A SECOND WRITER. A write protocol (render, diff, snapshot, write, re-parse,
verify) belongs to whoever owns the roster file; this produces the two strings it needs and
decides nothing about how they land.

⚑⚑⚑ A SOURCE SPLICE, NOT AN AST REWRITE: a four-line addition must be a four-line diff, so a
reviewer reads the CHANGE rather than a reformat that renormalises the provenance comments.

⚑⚑ DOUBLE QUOTES ON THE KEY, AND `repr` GETS THIS WRONG: the bib's witness resolver matches
`check=item:<key>` with a regex requiring double quotes, and a single-quoted key registers,
resolves at runtime, and is invisible to the one reader whose refusal it has to clear.

⚑ THE NOTE STILL GOES THROUGH `repr`, PER LINE: it is agent-supplied text emitted as source, and a
stray quote would write a file that does not parse — landing on the NEXT reader.

⚑⚑ THE ANCHOR IS COUNTED, NEVER SEARCHED-AND-HOPED, AND IT IS THE CALLER'S. Substrate's copy
fixed it to the text following its own roster's closing brace; where a roster ends is that
roster's shape, so `splice` takes the anchor, and refuses unless it occurs exactly once.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mikemol.ledger.finding_kindspec import Spec

# How wide a wrapped note line may run before it is broken.
WIDTH = 94

# The indent a continued note literal carries inside the roster.
CONT = "\n        "


def wrap_note(note: str, width: int = WIDTH) -> str:
    """Return the note as one or more Python string literals, `repr`-quoted per line.

    ⚑ EVERY LINE BUT THE LAST KEEPS A TRAILING SPACE, so the concatenated literals rejoin into the
    original sentence. ⚑ An empty note still emits a literal (`''`): substrate's original emitted
    nothing, which splices a syntax error.

    Returns:
        the literal source.

    """
    words = note.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    if not lines:
        return "''"
    last = len(lines) - 1
    return CONT.join(repr(line if i == last else line + " ") for i, line in enumerate(lines))


def render(key: str, spec: Spec, note: str) -> str:
    """Return the roster entry for one witness, as the source line(s) to splice.

    ⚑ THE KEY IS INTERPOLATED WITH DOUBLE QUOTES DIRECTLY rather than through `repr` — safe only
    because the caller has already refused any key outside the slug alphabet
    (`finding_kindspec.bad_key`).

    Returns:
        the entry's source, one indented comma-terminated row.

    """
    if spec.builder == "_mode_undocumented":
        body = f"lambda: _mode_undocumented({CONT}{spec.tool!r}, {spec.flag!r})"
    elif spec.cmd:
        body = f"lambda: {spec.builder}({CONT}{list(spec.cmd)!r}, {wrap_note(note)})"
    else:
        body = f"lambda: {spec.builder}({CONT}{wrap_note(note)})"
    return f'    "{key}": {body},\n'


def splice(source: str, entry: str, *, anchor: str) -> tuple[str, str]:
    """Return `(new_source, "")`, or `("", refusal)` when `anchor` is not unique in `source`.

    `anchor` is the text the roster's closing brace is followed by; the entry lands just before.

    ⚑⚑ COUNTED, NOT SEARCHED: zero means the roster's shape changed, several means the choice is
    ambiguous, and a splice at the wrong offset can still PARSE — so both refuse.

    Returns:
        the spliced source and "", or "" and the refusal.

    """
    found = source.count(anchor)
    if found != 1:
        return "", (
            f"cannot locate the roster terminator ({found} occurrence(s), expected 1) — refusing "
            "to guess an insertion point, since a splice at the wrong offset can still parse"
        )
    return source.replace(anchor, entry + anchor, 1), ""

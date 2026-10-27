# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a whole-list setter that drops a stored line without saying so (W2058, of W1930, W862).

`--standing-set`, `--preamble-set` and `--tick-hooks-set` each replace a stored list WHOLE from a
file, so a line left out of the file is silently gone: github-8f's measured case dropped a measured
sensor from the tick hooks while widening another (W1930), and the standing list has the same
shape (W862: "a rule left out of the file is a rule retired, a visible edit", but nothing made it
visible). The class fix is one check, not three: a stored line absent from the new file is refused
and named unless the file declares it gone with a `# replaces: <line>` or `# retires: <line>`
comment.

⚑ THE DECLARATION COMMENTS ARE NOT CONTENT: `split` takes them out of the lines to store, so a
declaration never lands in the standing list or the preamble as if it were a rule.
⚑ THE COMPARISON IS AGAINST THE WRITER'S OWN STORED LIST, never HEAD: a queue is not always under
git (the host's is not).
⚑ `--outcomes-set` TAKES TWO COMMA-SEPARATED OPERANDS AND NO FILE, so it has nowhere to carry a
declaration; it is not covered here (W2058 says so).

CONSUMED BY: `cli` (`_standing_set`, `_preamble_set`).
"""

from collections.abc import Sequence

from mikemol.pathsforward.tickhooks import DECLARES


def stored(doc: dict[str, object], key: str) -> list[str]:
    """Read a stored list of lines out of a state document.

    Returns:
        the strings of the list under `key`; empty when it is absent or not a list.

    """
    value = doc.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def split(text: str) -> tuple[list[str], set[str]]:
    """Separate a file's lines to store from the lines it declares gone.

    Returns:
        the lines of `text` that are not declaration comments, in order, and the set of lines named
        after `# replaces:` or `# retires:`, stripped.

    """
    kept: list[str] = []
    gone: set[str] = set()
    for raw in text.splitlines():
        stripped = raw.strip()
        mark = next((m for m in DECLARES if stripped.startswith(m)), None)
        if mark is None:
            kept.append(raw)
        else:
            gone.add(stripped[len(mark) :].strip())
    return kept, gone


def lost(prior: Sequence[str], text: str) -> list[str]:
    """Name the stored lines a new file loses without declaring them.

    Returns:
        the non-blank prior lines, in stored order, that the file neither keeps (compared
        stripped) nor declares gone.

    """
    kept, gone = split(text)
    present = {line.strip() for line in kept if line.strip()}
    return [p for p in prior if p.strip() and p.strip() not in present and p.strip() not in gone]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count a pyproject's lint exemptions: one per (file, rule) in `per-file-ignores` (W2138, W1976).

    count(pyproject_text)   # 3 for two files holding three rules between them; None if unread

⚑ A PER-FILE EXEMPTION MOVES DEBT OUT OF A COUNTED FILE (operator 2026-10-25): the ratchet counts
findings per file, so an entry in `[tool.ruff.lint.per-file-ignores]` makes a finding disappear
from the count without fixing it. This reader makes the exemptions themselves a number a ratchet
can hold, so adding one is a rise and removing one is a paydown.

⚑ UNREAD IS NOT ZERO: text that does not parse, or a table that is not a table of rule lists, is
`None`. A reader that called an unreadable file zero would show every broken pyproject as a clean
one. An ABSENT table is a real zero: the file parsed and holds no exemption.

One reader per file: a caller with a dist-level pyproject beside the root one counts each and sums,
so one unreadable file leaves the sum unread rather than short.
"""

import tomllib
from typing import cast


def count(pyproject_text: str) -> int | None:
    """Count the (file, rule) pairs in `[tool.ruff.lint.per-file-ignores]`.

    Returns:
        the number of rules listed across all files; 0 when the table is absent; None when the
        text does not parse or the table is not a table of lists of rules.

    """
    try:
        node: object = tomllib.loads(pyproject_text)
    except tomllib.TOMLDecodeError:
        return None
    for key in ("tool", "ruff", "lint", "per-file-ignores"):
        if not isinstance(node, dict):
            return None
        fields = cast("dict[str, object]", node)
        if key not in fields:
            return 0
        node = fields[key]
    if not isinstance(node, dict):
        return None
    total = 0
    for rules in cast("dict[str, object]", node).values():
        if not isinstance(rules, list):
            return None
        total += len(cast("list[object]", rules))
    return total

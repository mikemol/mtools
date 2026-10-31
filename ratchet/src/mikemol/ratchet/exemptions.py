# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count a repository's lint exemptions: pyproject `per-file-ignores` and suppression comments.

    count(pyproject_text)   # 3 for two files holding three rules between them; None if unread
    suppressions(source)    # 1 for a Python source with one `# noqa` or `# type: ignore` comment

⚑ A PER-FILE EXEMPTION MOVES DEBT OUT OF A COUNTED FILE (operator 2026-10-25): the ratchet counts
findings per file, so an entry in `[tool.ruff.lint.per-file-ignores]` makes a finding disappear
from the count without fixing it. This reader makes the exemptions themselves a number a ratchet
can hold, so adding one is a rise and removing one is a paydown.

⚑ A SUPPRESSION COMMENT IS THE SAME MOVE AT LINE GRAIN (W2140): the pycheck gate refuses to add
one, so a nonzero count is a leftover that stays visible. Only a real COMMENT token counts: a
docstring that names `# noqa` in prose is a string, not a suppression.

⚑ UNREAD IS NOT ZERO: text that does not parse, or a table that is not a table of rule lists, is
`None`. A reader that called an unreadable file zero would show every broken pyproject as a clean
one. An ABSENT table is a real zero: the file parsed and holds no exemption.

One reader per file: a caller with a dist-level pyproject beside the root one counts each and sums,
so one unreadable file leaves the sum unread rather than short.
"""

import io
import re
import tokenize
import tomllib
from typing import cast

_SUPPRESSION = re.compile(r"#\s*(noqa\b|type:\s*ignore\b|ruff:\s*(noqa|ignore)\b)")


def suppressions(source: str) -> int | None:
    """Count the suppression comments in one Python source.

    Returns:
        the number of comments that begin a `noqa`, `type: ignore` or `ruff: ignore`/`noqa`
        directive; 0 for none; None when the source does not tokenize.

    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return None
    return sum(
        1 for tok in tokens if tok.type == tokenize.COMMENT and _SUPPRESSION.match(tok.string)
    )


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

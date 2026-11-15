# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count a repository's lint exemptions: pyproject `per-file-ignores` and suppression comments.

    count(pyproject_text)   # 3 for two files holding three rules between them; None if unread
    count(text, tracked)    # a glob key counts once per tracked file it matches (W2387)
    new_globs(head, work)   # the glob keys the working text has and HEAD's did not
    suppressions(source)    # 1 for a Python source with one `# noqa` or `# type: ignore` comment

⚑ A PER-FILE EXEMPTION MOVES DEBT OUT OF A COUNTED FILE (operator 2026-10-25): the ratchet counts
findings per file, so an entry in `[tool.ruff.lint.per-file-ignores]` makes a finding disappear
from the count without fixing it. This reader makes the exemptions themselves a number a ratchet
can hold, so adding one is a rise and removing one is a paydown.

⚑ A GLOB COUNTS BY ITS EXPANSION (W2387, linux-sources W534): replacing N per-file entries with one
glob (`tests/*.py = [S101]`) would "pay down" N-1 pairs while WIDENING the exemption to every future
file, so given the tracked files a glob key counts one pair per file it matches (at least one, so a
glob matching nothing is not free). Collapsing entries into a glob is then neutral, and a NEW glob
key is a thing `new_globs` names for the caller to refuse. Without the tracked files the count is
the old one, a key a pair.

⚑ A SUPPRESSION COMMENT IS THE SAME MOVE AT LINE GRAIN (W2140): the pycheck gate refuses to add
one, so a nonzero count is a leftover that stays visible. Only a real COMMENT token counts: a
docstring that names `# noqa` in prose is a string, not a suppression.

⚑ UNREAD IS NOT ZERO: text that does not parse, or a table that is not a table of rule lists, is
`None`. A reader that called an unreadable file zero would show every broken pyproject as a clean
one. An ABSENT table is a real zero: the file parsed and holds no exemption.

One reader per file: a caller with a dist-level pyproject beside the root one counts each and sums,
so one unreadable file leaves the sum unread rather than short.
"""

import fnmatch
import io
import re
import tokenize
import tomllib
from collections.abc import Sequence
from typing import cast

_SUPPRESSION = re.compile(r"#\s*(noqa\b|type:\s*ignore\b|ruff:\s*(noqa|ignore)\b)")
_GLOB = re.compile(r"[*?\[]")


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


def _table(pyproject_text: str) -> dict[str, object] | None:
    """Read `[tool.ruff.lint.per-file-ignores]`.

    Returns:
        the table; an empty one when it is absent; None when the text does not parse or the
        table is not a table.

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
            return {}
        node = fields[key]
    return cast("dict[str, object]", node) if isinstance(node, dict) else None


def _weight(key: str, tracked: Sequence[str] | None) -> int:
    """Count the pairs one rule under `key` stands for.

    Returns:
        the tracked files a glob key matches (at least one), else one.

    """
    if tracked is None or not _GLOB.search(key):
        return 1
    return max(1, sum(1 for path in tracked if fnmatch.fnmatchcase(path, key)))


def count(pyproject_text: str, tracked: Sequence[str] | None = None) -> int | None:
    """Count the (file, rule) pairs in `[tool.ruff.lint.per-file-ignores]`.

    Args:
        pyproject_text: the pyproject's text.
        tracked: the tracked file paths, relative to the pyproject; a glob key then counts once per
            file it matches. Omitted, every key counts once.

    Returns:
        the number of rules listed across all files; 0 when the table is absent; None when the
        text does not parse or the table is not a table of lists of rules.

    """
    table = _table(pyproject_text)
    if table is None or not all(isinstance(rules, list) for rules in table.values()):
        return None
    return sum(
        len(cast("list[object]", rules)) * _weight(key, tracked) for key, rules in table.items()
    )


def entries(
    pyproject_text: str, tracked: Sequence[str] | None = None
) -> list[tuple[str, str]] | None:
    """List the (file, rule) pairs `count` counts, one per pair (W2306 slice 2).

    ⚑ THE LIST IS THE COUNT, SPELLED OUT: its length equals `count` for the same text and tracked
    files, because a list that disagreed with the census would pay down debt the census still
    counts. A glob key stands for each tracked file it matches (at least one, the key itself when
    none match), as `count` weights it.

    Args:
        pyproject_text: the pyproject's text.
        tracked: the tracked file paths, relative to the pyproject; omitted, every key is one file.

    Returns:
        the pairs in table order, rules in list order; None when `count` would answer None.

    """
    table = _table(pyproject_text)
    if table is None or not all(isinstance(rules, list) for rules in table.values()):
        return None
    pairs: list[tuple[str, str]] = []
    for key, rules in table.items():
        files = [path for path in tracked or () if fnmatch.fnmatchcase(path, key)]
        for file in files if _GLOB.search(key) and files else [key]:
            pairs.extend((file, str(rule)) for rule in cast("list[object]", rules))
    return pairs


def new_globs(head_text: str, work_text: str) -> list[str] | None:
    """Name the glob keys the working pyproject has and HEAD's did not.

    ⚑ JUDGED AGAINST HEAD'S KEYS, so the house `tests/*` globs that exist already stay (W2387).

    Returns:
        the new glob keys in order; None when either text is unread.

    """
    head, work = _table(head_text), _table(work_text)
    if head is None or work is None:
        return None
    return [key for key in work if _GLOB.search(key) and key not in head]

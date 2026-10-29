# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The kinds of ratchet file a repository carries, and how to read each one's value (W1906).

The operator saw a habit of adding ratchets and baselines and not paying them down, and ruled that
the existence of a nonzero ratchet is a priority marker (host transcript 695f3e0a, line 92679). A
marker has to be measured, so this is the registry the census (W1907) walks: which file names are
ratchet state, and what number each one holds.

⚑ A VALUE IS THE COUNT OF RECORDED DEBT. A baseline records what is still owed, so its value is how
many entries it holds and its floor is 0. A JSON file is read by its leaves: a number, a string or
a boolean is one entry, a list or an object is the sum of its parts, null is nothing, so an empty
`{}` is 0. A NUMBER IS NOT ITS VALUE: a ruff baseline's `file -> rule -> count` keeps the count
out of the key on purpose (two instances of a rule in a file are one debt), and a line number or a
hash in another shape would inflate the sum into nonsense (a first reading of gabion's baselines
summed to 799,536). A text file is read by its lines: every non-blank line that is not a `#`
comment is one entry.

⚑ A FILE THAT CANNOT BE READ IS UNREAD, NOT ZERO. A baseline that fails to parse answers None, never
0: a census that read an unparseable file as clean would show debt paid down by breaking the file,
the green-over-nothing shape this distribution exists to refuse (state.BaselineState.UNREAD).

⚑ THE KINDS ARE NAMES, AND A NAME IS A LOWER BOUND. A ratchet kept inside a file of another name
(a per-file-ignores table, a declared-defect list) is not found here, and the census says so.
"""

import json
import re
from pathlib import Path
from typing import cast

FLOOR = 0
_KINDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("preview", re.compile(r"^ratchet-preview\.txt$")),
    # ⚑ `rebaselines.json` is the file of DECLARED RISES (W2024), not recorded debt: matched by the
    # bare pattern it read as a ratchet of 5 (its five fields) and a repository that declared its
    # first rise looked like it had been born with debt. `(?<!re)` leaves every other baseline.
    ("baseline", re.compile(r"(?<!re)baseline.*\.(?:json|txt|tsv)$")),
    # ⚑ `debtplan.json` is the debt-plan tool's CONFIG (its exclusions), not recorded debt: matched
    # by the old pattern it read as a ratchet of 3 and made mtools look behind (W1955).
    ("debt", re.compile(r"debt(?!plan).*\.json$")),
    ("allowlist", re.compile(r"allowlist.*\.txt$")),
)


def kind_of(name: str) -> str | None:
    """Say which kind of ratchet file a file name is.

    Returns:
        `preview`, `baseline`, `debt` or `allowlist`; None for any other name.

    """
    return next((kind for kind, pattern in _KINDS if pattern.search(name)), None)


_LEAVES: frozenset[type] = frozenset({str, int, float, bool})


def _weight(node: object) -> int:
    # The entry count of a parsed JSON node: every scalar leaf is one entry, null is none, and so is
    # an empty string or false (W1979: a baseline's empty means no debt; a numeric 0 still counts).
    if node is False or (isinstance(node, str) and not node):
        return 0
    if type(node) in _LEAVES:
        return 1
    if isinstance(node, list):
        return sum(_weight(item) for item in cast("list[object]", node))
    if isinstance(node, dict):
        return sum(_weight(item) for item in cast("dict[str, object]", node).values())
    return 0


KIND_NAMES = tuple(name for name, _pattern in _KINDS)


def value_of(path: Path) -> int | None:
    """Read how much debt a ratchet file records.

    Returns:
        the count of recorded entries (see the module docstring); None when the file is a link,
        cannot be read, or is a JSON file that does not parse.

    """
    if path.is_symlink():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if path.suffix == ".json":
        try:
            parsed: object = json.loads(text)
        except ValueError:
            return None
        return _weight(parsed)
    lines = (line.strip() for line in text.splitlines())
    entries = [line for line in lines if line and not line.startswith("#")]
    # ⚑ A TAB-SEPARATED TABLE'S FIRST LINE IS ITS HEADER, NOT DEBT (W1992): 70 rows read 70.
    return len(entries) - 1 if path.suffix == ".tsv" and entries else len(entries)


def _counts(node: object) -> list[int] | None:
    # The integers of an object of objects of non-negative integers, or None for any other shape.
    if not isinstance(node, dict) or not node:
        return None
    found: list[int] = []
    for inner in cast("dict[str, object]", node).values():
        if not isinstance(inner, dict) or not inner:
            return None
        for count in cast("dict[str, object]", inner).values():
            if type(count) is not int or count < 0:
                return None
            found.append(count)
    return found


def sum_of(path: Path) -> int | None:
    """Sum the counts of a file-rule-count baseline (W1922).

    ⚑ ONLY THAT SHAPE. An entry count stays flat while a count inside a key falls (5 findings to 2
    of one rule in one file), so ruff's and mypy's baselines (`{file: {rule: count}}`) also report
    the sum of their counts. Any other file's numbers may be line numbers or hashes, whose sum is
    nonsense, so it answers None and keeps the entry count alone.

    Returns:
        the sum; None when the file is a link, is not JSON, or is not an object of non-empty
        objects of non-negative integers.

    """
    if path.suffix != ".json" or path.is_symlink():
        return None
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    counts = _counts(parsed)
    return None if counts is None else sum(counts)

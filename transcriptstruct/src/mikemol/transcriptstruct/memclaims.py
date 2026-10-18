# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List the operator quotes and rulings a memory file claims (mtools:W1542, W1541).

⚑ A MEMORY NOTE IS TESTIMONY ABOUT THE OPERATOR, NOT THE OPERATOR (github-8f, 2026-10-18, after
el-openglo swarmed on a stale note): the operator asked that every memory file be audited against
the transcript. This is the first step and it only reads: it lists what the note CLAIMS the
operator said, so a later step can look each claim up. It judges nothing and finds no record.

⚑ TWO KINDS OF CLAIM: a `quote` is a double-quoted passage of some length on a line that also
names the operator, and a `ruling` is a line that names the operator beside a date and quotes
nothing (`operator ruling 2026-10-02`). A line with a quote is one claim, never two.

⚑ A `description:` LINE IS QUOTED WHOLE, which would make every description a quote of itself, so
its wrapping quotes are removed first and a dated description reads as a ruling.
CONSUMED BY: the memory audit (`memaudit`).
"""

import re
from dataclasses import dataclass

_OPERATOR = re.compile(r"\boperator\b", re.IGNORECASE)
_DATE = re.compile(r"\b20[0-9]{2}-[0-9]{2}-[0-9]{2}\b")
_QUOTE = re.compile(r'"([^"\n]{20,})"')
_QUOTE_KIND = "quote"
_RULING_KIND = "ruling"
_DESCRIPTION = "description:"


@dataclass(frozen=True)
class Claim:
    """One thing a memory note says the operator said or ruled."""

    line: int
    kind: str
    text: str


def _unwrapped(raw: str) -> str:
    """Remove the quotes a `description:` value is wrapped in, leaving other lines as they are.

    Returns:
        the line, or a description's value without its wrapping quotes.

    """
    stripped = raw.strip()
    if not stripped.startswith(_DESCRIPTION):
        return raw
    return stripped.removeprefix(_DESCRIPTION).strip().strip('"')


def claims(text: str) -> list[Claim]:
    """List the claims of a memory file, in line order, one per line at most.

    Returns:
        the claims; a line naming the operator with a quote is a `quote` claim carrying the first
        quoted passage, and one naming the operator beside a date alone is a `ruling` claim
        carrying the whole line.

    """
    found: list[Claim] = []
    for number, original in enumerate(text.splitlines(), start=1):
        raw = _unwrapped(original)
        if not _OPERATOR.search(raw):
            continue
        quoted = _QUOTE.search(raw)
        if quoted is not None:
            found.append(Claim(number, _QUOTE_KIND, quoted.group(1)))
        elif _DATE.search(raw):
            found.append(Claim(number, _RULING_KIND, raw.strip()))
    return found

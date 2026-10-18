# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List the operator quotes and rulings a memory file claims (mtools:W1542, W1549, W1541).

⚑ A MEMORY NOTE IS TESTIMONY ABOUT THE OPERATOR, NOT THE OPERATOR (github-8f, 2026-10-18, after
el-openglo swarmed on a stale note): the operator asked that every memory file be audited against
the transcript. This is the first step and it only reads: it lists what the note CLAIMS the
operator said, so a later step can look each claim up. It judges nothing and finds no record.

⚑ THREE KINDS OF CLAIM. A `quote` is a double-quoted passage of some length on a line that also
names the operator. A `relayed` claim is such a quote on a line that says it was relayed, via a
peer or paraphrased: it is testimony, and is looked up all the same but reported as RELAYED when
no record carries it, never as a miss of the operator's own words. A `ruling` is a line that names
the operator beside a date and quotes nothing (`operator ruling 2026-10-02`). A line with a quote
is one claim, never two.

⚑ FRONTMATTER IS NOT THE OPERATOR'S TEXT (github-8f, 2026-10-18, W1549): only the `description:`
line of the frontmatter can claim anything, and only as a dated `ruling` (its wrapping quotes are
removed first); a quote inside the frontmatter, or any other frontmatter line, is skipped.
CONSUMED BY: the memory audit (`memaudit`).
"""

import re
from dataclasses import dataclass

_OPERATOR = re.compile(r"\boperator\b", re.IGNORECASE)
_DATE = re.compile(r"\b20[0-9]{2}-[0-9]{2}-[0-9]{2}\b")
_QUOTE = re.compile(r'"([^"\n]{20,})"')
_RELAYED = re.compile(r"\b(?:relayed|relays?|via|paraphras\w*)\b", re.IGNORECASE)
_QUOTE_KIND = "quote"
_RELAYED_KIND = "relayed"
_RULING_KIND = "ruling"
_DESCRIPTION = "description:"
_FENCE = "---"


@dataclass(frozen=True)
class Claim:
    """One thing a memory note says the operator said or ruled."""

    line: int
    kind: str
    text: str


def _unwrapped(raw: str) -> str:
    """Remove the quotes a `description:` value is wrapped in.

    Returns:
        the description's value without its wrapping quotes.

    """
    return raw.strip().removeprefix(_DESCRIPTION).strip().strip('"')


def _claim(number: int, raw: str, *, frontmatter: bool) -> Claim | None:
    """Read one line as a claim, or as nothing.

    Returns:
        the claim, or None when the line claims nothing or is frontmatter other than a dated
        description.

    """
    line = raw
    if frontmatter:
        if not raw.strip().startswith(_DESCRIPTION):
            return None
        line = _unwrapped(raw)
    if not _OPERATOR.search(line):
        return None
    quoted = None if frontmatter else _QUOTE.search(line)
    if quoted is not None:
        kind = _RELAYED_KIND if _RELAYED.search(line) else _QUOTE_KIND
        return Claim(number, kind, quoted.group(1))
    if _DATE.search(line):
        return Claim(number, _RULING_KIND, line.strip())
    return None


def claims(text: str) -> list[Claim]:
    """List the claims of a memory file, in line order, one per line at most.

    Returns:
        the claims; a line naming the operator with a quote is a `quote` (or `relayed`) claim
        carrying the first quoted passage, and one naming the operator beside a date alone is a
        `ruling` claim carrying the whole line.

    """
    found: list[Claim] = []
    inside = False
    for number, raw in enumerate(text.splitlines(), start=1):
        if raw.strip() == _FENCE:
            inside = number == 1
            continue
        got = _claim(number, raw, frontmatter=inside)
        if got is not None:
            found.append(got)
    return found

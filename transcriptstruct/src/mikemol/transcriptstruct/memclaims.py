# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""List the operator quotes and rulings a memory file claims (mtools:W1542, W1549, W1551, W1541).

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

⚑ A QUOTE MARK IS PAIRED BY ITS SHAPE, NOT BY ITS POSITION (github-8f, W1551): a regex over
double-quoted spans paired the closing mark of one quote with the opening mark of the next and
handed back the words BETWEEN them. An opening mark follows no letter or digit and precedes no
space; a closing mark follows no space and precedes no letter or digit; a mark that fits neither
role, or a closing mark with nothing open, is skipped. Curly quotes read as straight ones and an
escaped quote mark as a plain one.
CONSUMED BY: the memory audit (`memaudit`).
"""

import re
from dataclasses import dataclass

_OPERATOR = re.compile(r"\boperator\b", re.IGNORECASE)
_DATE = re.compile(r"\b20[0-9]{2}-[0-9]{2}-[0-9]{2}\b")
_MARK = re.compile(r'"')
_RELAYED = re.compile(r"\b(?:relayed|relays?|via|paraphras\w*)\b", re.IGNORECASE)
_QUOTE_KIND = "quote"
_RELAYED_KIND = "relayed"
_RULING_KIND = "ruling"
_DESCRIPTION = "description:"
_FENCE = "---"
_MIN_QUOTE = 20
_BLANK = " "


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


def first_quote(line: str) -> str | None:
    """Take the first long double-quoted passage of a line, pairing marks by their shape.

    Returns:
        the passage between an opening and a closing mark, or None when the line has none of at
        least twenty characters.

    """
    text = line.replace('\\"', '"').replace("“", '"').replace("”", '"')
    opened: int | None = None
    for found in _MARK.finditer(text):
        at = found.start()
        before = text[at - 1] if at else _BLANK
        after = text[at + 1] if at + 1 < len(text) else _BLANK
        if opened is None:
            if not before.isalnum() and not after.isspace():
                opened = at
        elif not before.isspace() and not after.isalnum():
            passage = text[opened + 1 : at]
            if len(passage) >= _MIN_QUOTE:
                return passage
            opened = None
    return None


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
    quoted = None if frontmatter else first_quote(line)
    if quoted is not None:
        kind = _RELAYED_KIND if _RELAYED.search(line) else _QUOTE_KIND
        return Claim(number, kind, quoted)
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

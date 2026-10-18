# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Flag the lines of a memory file that grant a permission or lift a rule (mtools:W1543, W1547).

⚑ A NOTE THAT GRANTS IS THE ONE THAT HURTS WHEN STALE: el-openglo swarmed on a note that said
swarming was lifted, after a later ruling had withdrawn it. A grant is a line saying something is
allowed, authorized, lifted or may be done, so these lines go first in a reviewer's queue. The
match is a word list the operator named (swarm, unattended, may, allowed) widened by its near
neighbours; it over-flags on purpose, because a missed grant is the costly error and a reviewer
reads the row.

⚑ POLARITY (github-8f, 2026-10-18, W1547): the host's no-swarming note drew four GRANT rows from
bare words, because a restriction names the same words a grant does. A line is read in clauses
(split at `. ; ! ?` and at but, however, except, unless), and a grant word in a clause that also
carries a negation anywhere in it (no, not, never, nor, without, cannot, or any `n't`) is a
RESTRICTION and is not flagged (so are only, exceed and limit). A short quoted phrase of up to forty
characters is a MENTION, not a use: the note naming the "swarm this" the operator sometimes says
grants nothing by naming it. Round two (W1553): a grant word that is a NOUN, in `allowed set`,
`allow-lists` or `permission rule`, names a thing and grants nothing. A clause can still hide a
grant behind a negation; that is the price of a word-level reader, and the word is still on the
line a reviewer opens.
CONSUMED BY: the memory audit (`memaudit`).
"""

import re
from dataclasses import dataclass
from typing import cast

from mikemol.transcriptstruct.memclaims import quote_spans, straight

_WORDS = (
    "swarm",
    "swarms",
    "swarming",
    "unattended",
    "allowed",
    "allow",
    "authorized",
    "authorised",
    "permitted",
    "lifted",
    "lift",
    "may",
)
_PHRASES = ("permission to", "grant permission", "grants permission", "granted permission")
_GRANT = re.compile(r"\b(" + "|".join((*_WORDS, *_PHRASES)) + r")\b", re.IGNORECASE)
_LINK = re.compile(r"\[\[[^\]\n]*\]\]")
_IDENTIFIER = re.compile(r"^\s*name:")
_NEGATION = re.compile(
    r"\b(?:no|not|never|nor|without|cannot|only|exceed|limit)\b|\bat most\b|n't\b", re.IGNORECASE
)
_MENTION_MAX = 40
_CLAUSE = re.compile(r"[.;!?]|\b(?:but|however|except|unless)\b", re.IGNORECASE)
_NOUN = re.compile(
    r"\b(?:allow(?:ed)?[- ](?:sets?|lists?)|allowlists?|permissions?[- ](?:rules?|prompts?|denials?"
    r"|classifier|settings?))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Grant:
    """One line of a memory file that reads as a permission or a lifted rule."""

    line: int
    words: tuple[str, ...]
    text: str


def _unmentioned(raw: str) -> str:
    """Blank the short quoted phrases of a line, which name words and do not use them.

    ⚑ MARKS ARE PAIRED BY SHAPE (W1551), so the gap between one long quote and the next is never
    mistaken for a quote of its own. A phrase of at most `_MENTION_MAX` characters in double or
    single quotes is a mention; a long quoted utterance is kept, since it may be the operator's
    grant.

    Returns:
        the line with each short quoted phrase replaced by spaces.

    """
    text = _LINK.sub(" ", straight(raw))
    hidden = [False] * len(text)
    for mark in ('"', "'"):
        for start, end in quote_spans(text, mark):
            if end - start - 1 <= _MENTION_MAX:
                hidden[start : end + 1] = [True] * (end + 1 - start)
    return "".join(" " if gone else char for char, gone in zip(text, hidden, strict=True))


def _granted(raw: str) -> list[str]:
    """Take the grant words of the clauses of a line that carry no negation.

    Returns:
        the matched words, in order, with repeats.

    """
    found: list[str] = []
    for clause in _CLAUSE.split(_unmentioned(raw)):
        if not _NEGATION.search(clause):
            bare = _NOUN.sub(" ", clause)
            found.extend(cast("list[str]", _GRANT.findall(bare)))
    return found


def grants(text: str) -> list[Grant]:
    """List the lines of a memory file that carry an unnegated grant word, in line order.

    Returns:
        one `Grant` per matching line with the distinct words it matched, lower-cased and sorted.

    """
    found: list[Grant] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if _IDENTIFIER.match(raw):
            continue
        words = sorted({word.lower() for word in _granted(raw)})
        if words:
            found.append(Grant(number, tuple(words), raw.strip()))
    return found

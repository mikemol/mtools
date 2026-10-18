# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Match a memory note's claimed operator words to the operator's actual utterances (W1544, W1541).

⚑ A CLAIM IS WARRANTED ONLY BY A RECORD, AND A LATER RECORD CAN SUPERSEDE IT (github-8f, 2026-10-18,
after el-openglo swarmed on a note recording a permission the operator had since withdrawn). This
takes the claims `memclaims` lists and a list of the operator's utterances (`Utterance`: where it
is, its uuid, its time, its text) and says, per claim, whether a record carries the words, and
whether a later utterance on the same subject exists. It reads no file: the caller supplies the
utterances, so the same matcher serves cards and memory notes.

⚑ THE MATCH IS EXACT, THEN LOOSE, AND NEVER INVENTED: a quote is warranted when its words,
lower-cased with runs of space collapsed, are a substring of an utterance; a quote with no such
utterance is UNWARRANTED, not guessed at. A later utterance is POSSIBLY SUPERSEDED evidence only
when it shares `OVERLAP` or more of the note's key terms, so a reviewer reads it; it is never
proof. Terms are the note's own words of five letters or more, minus the stop words below.
CONSUMED BY: the memory audit (`memaudit`).
"""

import re
from dataclasses import dataclass
from typing import cast

from mikemol.transcriptstruct.memclaims import Claim

OVERLAP = 3
SHARE = 0.3
LONG = 2000
_PASTED = "<pasted_content"
UNWARRANTED = "UNWARRANTED"
WARRANTED = "WARRANTED"
DATED = "DATED"
RELAYED = "RELAYED"
_WORDS_KINDS = frozenset({"quote", "relayed"})
_WORD = re.compile(r"[a-z]{5,}")
_SPACE = re.compile(r"\s+")
_STOP = frozenset(
    {
        "about",
        "after",
        "again",
        "always",
        "before",
        "being",
        "could",
        "every",
        "never",
        "other",
        "should",
        "their",
        "there",
        "these",
        "those",
        "which",
        "while",
        "would",
        "operator",
    }
)


@dataclass(frozen=True)
class Utterance:
    """One thing the operator said: where it is, when, and its words."""

    path: str
    line: int
    uuid: str
    at: str
    text: str


@dataclass(frozen=True)
class Finding:
    """What the transcript says about one claim."""

    claim: Claim
    status: str
    record: Utterance | None


def _when(utterance: Utterance) -> str:
    return utterance.at


def _pasted(utterance: Utterance) -> bool:
    return _PASTED in utterance.text or len(utterance.text) > LONG


def _rank(scored: tuple[float, Utterance]) -> tuple[float, str]:
    return scored[0], scored[1].at


def normal(text: str) -> str:
    """Lower-case text and collapse every run of whitespace to one space.

    Returns:
        the normalized text.

    """
    return _SPACE.sub(" ", text.lower()).strip()


def terms(text: str) -> frozenset[str]:
    """Take the key words of a note: those of five letters or more that are not stop words.

    Returns:
        the distinct words, lower-cased.

    """
    words = cast("list[str]", _WORD.findall(text.lower()))
    return frozenset(w for w in words if w not in _STOP)


def warrant_for(claim: Claim, utterances: list[Utterance]) -> Finding:
    """Find the utterance that carries a claimed quote.

    ⚑ ONLY A QUOTE CAN BE FOUND BY ITS WORDS: a ruling claim has none of its own, so it is
    DATED for the caller to look up by date and subject, apart from a quote nobody said. A
    relayed quote (via a peer, paraphrased) is looked up too, and is RELAYED when no record
    carries it: testimony, not a miss of the operator's own words (W1549).

    Returns:
        WARRANTED with the earliest matching utterance; else UNWARRANTED (a quote), RELAYED (a
        relayed quote) or DATED (a ruling), each with no record.

    """
    wanted = normal(claim.text)
    if claim.kind in _WORDS_KINDS:
        for found in sorted(utterances, key=_when):
            if wanted in normal(found.text):
                return Finding(claim, WARRANTED, found)
    status = {"quote": UNWARRANTED, "relayed": RELAYED}.get(claim.kind, DATED)
    return Finding(claim, status, None)


def superseded_by(
    note_terms: frozenset[str], since: str, utterances: list[Utterance]
) -> list[Utterance]:
    """List the later utterances that share the note's subject, best first.

    ⚑ SCORED BY THE SHARE OF THE NOTE'S TERMS (github-8f, 2026-10-18, W1548): one huge pasted
    record matched unrelated notes because it contained everything, so an utterance with a
    `<pasted_content` block or over `LONG` characters is skipped, and the rest must share at least
    `OVERLAP` terms AND `SHARE` of the note's terms. Best share first, newest breaking a tie.

    Returns:
        the utterances made after `since` that clear both bars.

    """
    if not note_terms:
        return []
    scored = [
        (len(note_terms & terms(u.text)) / len(note_terms), u)
        for u in utterances
        if u.at > since and not _pasted(u)
    ]
    kept = [pair for pair in scored if pair[0] * len(note_terms) >= OVERLAP and pair[0] >= SHARE]
    return [u for _share, u in sorted(kept, key=_rank, reverse=True)]

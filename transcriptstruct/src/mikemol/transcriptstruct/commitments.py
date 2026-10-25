# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Find the statements of known-needed, unpersisted work an assistant made (W1931, github:W44).

The operator's ask (host transcript 695f3e0a, line 94427): an automated mechanism that watches
transcripts for "a thing I knew I needed to do, said I had not done, and did not persist a means of
follow-through", with a debt ledger against it. This is the sensor. The statement is encouraged,
never penalised (line 94534: "I still need to X"), so the sensor must be precise and cheap.

⚑ PRECISION WAS MEASURED BY HAND FIRST (the card's evidence, 2026-10-24): over a day of one
session's transcript nine lines matched the loose phrase list and only three were commitments. Four
were USER-role records quoting a peer's message, two were assistant summaries reporting another
card's status. So: ASSISTANT RECORDS ONLY, text blocks only; a sentence that quotes a cross-session
message is skipped; and the phrases are the ones that were measured to carry a commitment.

⚑ A ROW IS ONE SENTENCE. The sentence holding the phrase, with the card cites (`W123`,
`repo:W123`) and repo-relative file names it names, so the resolver can ask whether a card carries
it. A sentence that already names a card is still a row: attachment is the resolver's first test.

⚑ THE EXTRACTOR KNOWS NO REPOSITORY: the caller says which session and repository the transcript
belongs to, and the extractor stamps them on each row.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from mikemol.transcriptstruct.blocks import blocks
from mikemol.transcriptstruct.records import AssistantRecord, Record

# The canonical form is first: the operator's own phrasing (host line 94534).
FAMILIES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("canonical", re.compile(r"\bI still need to\b", re.IGNORECASE)),
    ("not-yet", re.compile(r"\bI (?:have not|haven't) yet\b|\bI did not (?:yet )?re-?run\b")),
    ("still-to-do", re.compile(r"\bstill to do\b")),
    ("next-step", re.compile(r"\bnext I will\b|\bI'll\b[^.]{0,80}(?<!not )\blater\b")),
)
# ⚑ THE STATUS FAMILY IS MEASURED AND LEFT OUT (W1931, 2026-10-25): `remains open` and `not done`
# matched 49 of the 108 sentences of one session's transcript, nearly all reports of a card's
# state ("W1646 is not done.") that the card already carries, and some of another party's state
# or unrelated senses. A status report is attached by its cite; it is not a new commitment.
# A phrase inside quotation marks or backticks is a MENTION of the phrase, not a statement.
_MENTION = re.compile(r"[\"\u201c\u2018`]\s*(?:I still need to|next I will)", re.IGNORECASE)
# A sentence ends at ./!/? followed by space or the end, so a file name (x.py) is not split.
_SENTENCE = re.compile(r"[^\n]+?(?:[.!?](?=\s|$)|$)")
_CITE = re.compile(r"\b(?:[a-z][a-z0-9-]*:)?W\d+\b")
_FILE = re.compile(r"[\w./-]+\.(?:py|md|json|toml|sh|bazel|rego|tsv)\b")
_QUOTING = "cross-session-message"


@dataclass(frozen=True, slots=True)
class Commitment:
    """One statement: where it was made, what it said, which family, and what it names."""

    line: int
    uuid: str
    session: str
    repo: str
    family: str
    text: str
    names: tuple[str, ...]
    at: str = ""


def _spans(pattern: re.Pattern[str], text: str) -> list[str]:
    # The slices of `text` the pattern matches, taken by span so each one is a plain str.
    return [text[found.start() : found.end()] for found in pattern.finditer(text)]


def _names(sentence: str) -> tuple[str, ...]:
    unique: list[str] = []
    for item in [*_spans(_CITE, sentence), *_spans(_FILE, sentence)]:
        if item not in unique:
            unique.append(item)
    return tuple(unique)


def _family(sentence: str) -> str | None:
    if _MENTION.search(sentence):
        return None
    return next((name for name, pattern in FAMILIES if pattern.search(sentence)), None)


def extract(records: Iterable[Record], session: str, repo: str) -> list[Commitment]:
    """Read the commitments the assistant records of a transcript make.

    Returns:
        one row per sentence of an assistant text block that carries a measured phrase, in
        transcript order; user-role records, tool output and a sentence quoting a cross-session
        message give none.

    """
    found: list[Commitment] = []
    for record in records:
        if not isinstance(record, AssistantRecord) or record.is_sidechain:
            continue
        uuid = str(record.raw.get("uuid", ""))
        for block in blocks(record):
            if block.kind != "text":
                continue
            for sentence in _spans(_SENTENCE, block.text):
                family = _family(sentence)
                if family is None or _QUOTING in sentence:
                    continue
                said = sentence.strip()
                stamp = str(record.raw.get("timestamp", ""))
                row = Commitment(
                    record.line, uuid, session, repo, family, said, _names(said), stamp
                )
                found.append(row)
    return found

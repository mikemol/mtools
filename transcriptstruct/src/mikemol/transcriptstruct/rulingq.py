# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 10: ask the rulings ledger what the operator said about a card or topic (mtools:W1387).

⚑⚑ THE ANSWER IS THE OPERATOR'S OWN WORDS, NEWEST FIRST. The ledger (stage 9) holds one PROV-O
entity per operator utterance; a query returns the entities whose needle matches, ordered by the
time they were said, latest first, because a later ruling supersedes an earlier one and a reader
acting on a card needs the current word before the history. Nothing is summarised: the needle is
whole, and the entity's IRI (`file#uuid`) is the citation a warrant needs.

⚑ A PATTERN IS A REGULAR EXPRESSION, CASE-INSENSITIVE, SEARCHED IN THE NEEDLE. A card symbol
(`W1386`) and a topic (`freeze|unfreeze`) are the same kind of question. An empty ledger, or a
pattern that matches nothing, is an empty answer the caller prints as such, never an error: it
says "no ruling touches this", which is a finding.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True, slots=True)
class Ruling:
    """One ledger entity, flattened for a reader: where it came from, when, and what was said."""

    iri: str
    said_at: str
    line: int | None
    session: str | None
    needle: str


def _ruling(entity: dict[str, object]) -> Ruling:
    stamp = cast("dict[str, object]", entity["prov:generatedAtTime"])
    line = entity.get("mtools:line")
    session = entity.get("mtools:session")
    return Ruling(
        str(entity["@id"]),
        str(stamp["@value"]),
        line if isinstance(line, int) else None,
        session if isinstance(session, str) else None,
        str(entity.get("mtools:needle", "")),
    )


def rulings(ledger: Path, pattern: str, limit: int | None = None) -> list[Ruling]:
    """Find the rulings whose text matches `pattern`, newest first.

    Returns:
        the matching rulings ordered by the time they were said, latest first, at most `limit`;
        empty when the ledger is absent or nothing matches.

    """
    if not ledger.is_file():
        return []
    wanted = re.compile(pattern, re.IGNORECASE)
    found = [
        r
        for r in (
            _ruling(cast("dict[str, object]", json.loads(line)))
            for line in ledger.read_text(encoding="utf-8").split("\n")
            if line.strip()
        )
        if wanted.search(r.needle)
    ]
    found.sort(key=lambda r: r.said_at, reverse=True)
    return found if limit is None else found[:limit]

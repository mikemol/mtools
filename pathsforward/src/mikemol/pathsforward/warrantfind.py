# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the transcript citations a card's evidence text carries (W2076, for W1863).

A card that quotes the operator should carry a warrant, and most carry only a date. This is the
pure first half of finding them: from the evidence text, the citations that have a CHECKABLE form,
and the decision that a card has none.

⚑ A CITATION IS `host <8 hex> line <n>`, WITH A UUID WHEN ONE FOLLOWS IT (the form the host's
reviewers write: `host 695f3e0a line 109815, uuid 53079d0f-ccac-4e25-b783-9f7b8912463c`). A bare
uuid with no line is a citation too (it can be verified by uuid alone), kept with an empty session
and no line. A date is NOT a citation: nothing checks it.

⚑ PURE, NO I/O: the verify and attach halves reuse `warrant.read` and `warrant.attach`.

CONSUMED BY: nothing yet (W1863's finder).
"""

import re
from dataclasses import dataclass

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_SESSION_LINE = re.compile(r"\bhost\s+(?P<session>[0-9a-f]{8})\s+line\s+(?P<line>\d+)")
_UUID_AT = re.compile(rf"\b(?P<uuid>{_UUID})\b")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?!\d)")


@dataclass(frozen=True)
class Cite:
    """One checkable citation: the session prefix, the uuid and the line, each empty or None."""

    session: str
    uuid: str
    line: int | None


def cites(evidence: str) -> list[Cite]:
    """Find the transcript citations in a card's evidence text.

    A `host <session> line <n>` citation takes the first uuid between its end and the next
    citation's start; a uuid no citation claimed stands alone.

    Returns:
        the citations in text order; empty when the text has no checkable form.

    """
    marks = list(_SESSION_LINE.finditer(evidence))
    found: list[Cite] = []
    claimed: set[tuple[int, int]] = set()
    for at, mark in enumerate(marks):
        end = marks[at + 1].start() if at + 1 < len(marks) else len(evidence)
        uuid = _UUID_AT.search(evidence, mark.end(), end)
        if uuid is not None:
            claimed.add(uuid.span())
        found.append(Cite(mark["session"], uuid["uuid"] if uuid else "", int(mark["line"])))
    alone = [m for m in _UUID_AT.finditer(evidence) if m.span() not in claimed]
    return [*found, *(Cite("", m["uuid"], None) for m in alone)]


def unresolved(evidence: str) -> bool:
    """Say whether a card's evidence cites only dates, with nothing a reader can check.

    Returns:
        True when the text names a date and no checkable citation; False otherwise, including for
        a text with no date at all (nothing is claimed that needs a warrant).

    """
    return bool(_DATE.search(evidence)) and not cites(evidence)

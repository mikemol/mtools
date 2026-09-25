# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Report which finding-key ordinals are taken, so a filer stops reusing one.

Moved from substrate (N-a row 6).

⚑⚑⚑ THREE INDEPENDENT AGENTS MADE THE SAME MISTAKE. Keys are `<family>-<letter><ordinal>-<slug>`,
and registration refuses only an EXACT duplicate — so two findings sharing an ordinal but not a
slug both register, and the ordinal stops identifying or sorting. Each time, an agent read the
roster, computed max-plus-one, and filed with no exclusion against a concurrent filer: a
read-modify-write with no compare-and-swap.

⚑ SO THIS REPORTS THE TAKEN SET RATHER THAN SUGGESTING A NEXT NUMBER. A suggestion goes stale
between the read and the write, which is the defect itself one layer on.

⚑ THE KEYS ARE READ AS TEXT, NOT IMPORTED: the question is about key SPELLING, which the source
text answers directly, and importing a roster would inherit whatever freezes it.

⚑⚑ NO DEFAULT LEDGER. Substrate's copy read `ROOT / ".claude/agents/findings.py"` when no path was
given, `ROOT` derived from `__file__`; installed, that names a file inside `site-packages`. Every
reader takes the ledger's path, and only a CLI resolves it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# A witness key as the roster spells it: family, a letter-and-ordinal, an optional slug.
_KEY = re.compile(r'^\s*"([a-z]+)-([A-Z])(\d+)(?:-([a-z0-9-]+))?"\s*:', re.MULTILINE)

# What the render says about its own scope, after the rows. Each element parenthesised, because
# inside a collection an implicit concatenation and a forgotten comma are the same bytes.
_SCOPE = (
    (
        "   ⚑ AN ORDINAL IS NOT AN IDENTIFIER ONCE IT COLLIDES. The full key stays unique, so "
        "nothing was overwritten — but the number no longer sorts or names, and a filer reading "
        "max-plus-one keeps reusing one."
    ),
    (
        "   ⚑ NO NEXT NUMBER IS SUGGESTED. A suggestion goes stale between the read and the "
        "write, which is the read-modify-write defect one layer on."
    ),
)


@dataclass(frozen=True, slots=True)
class Ordinal:
    """One family-and-number, and every slug filed under it."""

    family: str
    letter: str
    number: int
    slugs: tuple[str, ...]

    @property
    def collided(self) -> bool:
        """Whether more than one finding shares this ordinal."""
        return len(self.slugs) > 1

    @property
    def label(self) -> str:
        """The ordinal as a filer would type it."""
        return f"{self.family}-{self.letter}{self.number}"


def _position(item: Ordinal) -> tuple[str, str, int]:
    """Return the sort key: family, then letter, then number.

    Returns:
        the key.

    """
    return (item.family, item.letter, item.number)


def _weight(item: Ordinal) -> tuple[int, str]:
    """Return the collision sort key: most-collided first, then label.

    Returns:
        the key.

    """
    return (-len(item.slugs), item.label)


def ordinals(ledger: Path) -> list[Ordinal]:
    """Return every ordinal in the ledger, with the slugs filed under it.

    ⚑ AN UNSLUGGED KEY IS STILL AN OCCUPANT: a bare `family-O12` holds its ordinal exactly as a
    slugged one does, so it is carried with an empty slug — a reader that dropped it would report
    a taken ordinal as free.

    Returns:
        the ordinals, sorted by family, letter and number.

    """
    text = ledger.read_text(encoding="utf-8", errors="replace")
    seen: dict[tuple[str, str, int], list[str]] = {}
    for match in _KEY.finditer(text):
        family, letter, number, slug = match.groups()
        seen.setdefault((family, letter, int(number)), []).append(slug or "")
    rows = [
        Ordinal(family, letter, number, tuple(sorted(slugs)))
        for (family, letter, number), slugs in seen.items()
    ]
    return sorted(rows, key=_position)


def taken(family: str, letter: str, ledger: Path) -> set[int]:
    """Return the ordinals already used in one family-and-letter series.

    Returns:
        the taken numbers.

    """
    return {o.number for o in ordinals(ledger) if o.family == family and o.letter == letter}


def collisions(ledger: Path) -> list[Ordinal]:
    """Return every ordinal naming more than one finding.

    Returns:
        the collided ordinals.

    """
    return [o for o in ordinals(ledger) if o.collided]


def render(ledger: Path) -> str:
    """Render the collision census, most-collided first.

    Returns:
        the report.

    """
    rows = collisions(ledger)
    total = len(ordinals(ledger))
    out = [f"{len(rows)} collided ordinal(s) over {total} in the ledger"]
    for row in sorted(rows, key=_weight):
        out.append(f"  {row.label:<12} {len(row.slugs)} findings")
        out.extend(f"      {slug or '(no slug)'}" for slug in row.slugs)
    out.extend(_SCOPE)
    return "\n".join(out)

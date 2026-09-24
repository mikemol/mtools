# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The witness contract: a witness YIELDS rows — parts as they are found, the verdict last.

Moved from substrate's `substrate/witness_row.py` (N-a row 3); its suite is ported to
`tests/test_witness_row.py`. substrate extracted it from a module mid-migration between two
contracts and kept only the live half (user, 2026-08-05: *"Witnesses return rowsets. They should
yield rows rather than return."*): a witness yields `part(...)` rows as it finds them and one
`verdict(...)` row last, rather than returning a code and depositing figures in module globals.

⚑⚑ THE VERDICT TRAILS ITS PARTS, AND THAT IS FORCED: a witness knows `open`/`closed` only after
it has finished looking, and a verdict emitted first would be the count-before-the-walk defect.

⚑ THERE IS NO `size` ON A VERDICT, DELIBERATELY. The collector counts what it forwarded; a
witness that also declared a size would reintroduce the second derivation whose disagreement the
retired reconciliation existed to catch. Under one walk the count IS what was forwarded, so a
truncation has to be a visible early return rather than an invisible slice.

⚑ THE STATE SPELLING IS CASE-SENSITIVE AND IS NOT NORMALISED (the letter's one contract detail):
`OPEN` is uppercase and `closed` is not, and `is_open` is `state != CLOSED`.

substrate's `__main__` block (a `speak()` usage text and exit 2) is not ported: it was a CLI for
a module with no modes, and a package module has no `__main__` invocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The two row kinds. A reader dispatches on this, so they are constants, not bare strings.
VERDICT, PART = "verdict", "part"

# The states a verdict may carry. ⚑ `OPEN` IS UPPERCASE AND `closed` IS NOT: an open item is the
# one that wants attention.
OPEN, CLOSED = "OPEN", "closed"


@dataclass(frozen=True)
class Part:
    """One emitted part of an item — yielded as it is FOUND, never collected.

    ⚑ `route` is what makes a row usable by the graph rather than by a reader only: a witness's
    per-provider routes were once discarded at the boundary, surviving only inside a string.
    """

    key: str
    name: str
    route: str | None = None
    detail: dict[str, str] = field(default_factory=dict)

    kind: str = PART


@dataclass(frozen=True)
class Verdict:
    """The item's own row, trailing its parts."""

    key: str
    state: str
    why: str
    detail: dict[str, str] = field(default_factory=dict)

    kind: str = VERDICT

    @property
    def is_open(self) -> bool:
        """Report whether this verdict is open.

        ⚑ Keyed on the state, not on truthiness: an unrecognised state reads as OPEN, because an
        unknown state must never read as resolved.

        Returns:
            True for any state but exactly `closed`.

        """
        return self.state != CLOSED


def part(
    key: str, name: str, route: str | None = None, detail: dict[str, str] | None = None
) -> Part:
    """Build one part row, with its own copy of `detail`.

    Returns:
        the part.

    """
    return Part(key=key, name=name, route=route, detail=dict(detail or {}))


def opened(key: str, why: str, detail: dict[str, str] | None = None) -> Verdict:
    """Build an OPEN verdict row.

    Returns:
        the verdict.

    """
    return Verdict(key=key, state=OPEN, why=why, detail=dict(detail or {}))


def closed(key: str, why: str, detail: dict[str, str] | None = None) -> Verdict:
    """Build a closed verdict row.

    Returns:
        the verdict.

    """
    return Verdict(key=key, state=CLOSED, why=why, detail=dict(detail or {}))

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Drop the waits another wait implies: the transitive reduction of a plan's order.

`Row.waits_on` lists every debt file in an import closure, so a file that waits on a file that waits
on a third also lists the third. A wait implied by another wait adds an edge and no order, and the
edge costs a card a longer `blocked_on` and a graph a line to draw. What is left when the implied
waits are dropped orders the files exactly as the closure did.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.debtplan.rows import Row


def direct_waits(rows: Sequence[Row]) -> dict[str, tuple[str, ...]]:
    """Reduce each file's waits to the ones no other wait of the same file implies.

    The waits must already be transitive and acyclic, as a plan makes them: then a file `g` is
    implied exactly when some other wait `h` of the same file itself waits on `g`.

    Returns:
        For each file, its direct waits, sorted. A file that waits on nothing maps to an empty
        tuple.

    """
    by = {row.file: set(row.waits_on) for row in rows}
    return {
        file: tuple(sorted(g for g in waits if not any(g in by[h] for h in waits if h != g)))
        for file, waits in by.items()
    }

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The records `funcnames` returns, apart from the module that needs SQLAlchemy (mtools:W1359).

⚑ THE RECORDS LIVE WHERE THEIR READERS CAN IMPORT THEM WITHOUT THE EXTRA. `funcnames` raises on
import when the optional `sqlalchemy` extra is absent, so the driver names `FuncCalls` only for a
type and imports the module itself lazily; with the type in `funcnames` that annotation needed a
`TYPE_CHECKING` guard, which the Codon target cannot have. Both import these records from here.
"""

from dataclasses import dataclass, field

from mikemol.pycodemod.core import Skip


@dataclass(frozen=True, slots=True, order=True)
class FuncCall:
    """One `func.<name>(...)` call: where, in which function, and whether Core translates it."""

    path: str
    line: int
    caller: str
    name: str
    kind: str


@dataclass(frozen=True, slots=True)
class FuncCalls:
    """The graded calls found, and the files that could not be read."""

    rows: list[FuncCall] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)

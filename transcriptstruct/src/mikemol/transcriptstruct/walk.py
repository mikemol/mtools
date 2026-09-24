# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 2: the lossless walk — every string anywhere in a record, with the path that reaches it.

The typed decoders (records, and later blocks and provenance) read the fields they KNOW. A
field they do not know is invisible to them, and invisibility is exactly how three attachment
shapes hid from the old reader. This walk knows no fields at all: it descends every dict and
list and yields each leaf string with its path, so a string exists in the output if and only if
it exists in the input.

⚑ It is the backstop, not the reader. A later stage subtracts the paths the decoders claimed from
the paths this walk yields; the remainder is the UNDECODED population, reported with a count,
never dropped.

Paths are tuples of dict keys (str) and list indices (int), from the envelope's root. Dict keys
are walked in insertion order, which for parsed JSON is file order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

type Path = tuple[str | int, ...]


@dataclass(frozen=True, slots=True)
class Leaf:
    """One string in a record, and the path from the root that reaches it."""

    path: Path
    text: str


def strings(value: object, path: Path = ()) -> Iterator[Leaf]:
    """Walk `value` depth-first, in document order.

    Yields:
        Each string reachable from `value`, with its path from the root. A non-string scalar
        (number, bool, null) is not a string and yields nothing.

    """
    if isinstance(value, str):
        yield Leaf(path, value)
    elif isinstance(value, dict):
        for key, child in cast("dict[str, object]", value).items():
            yield from strings(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(cast("list[object]", value)):
            yield from strings(child, (*path, index))


def render(path: Path) -> str:
    """Spell a path the way a person greps a transcript for it.

    Returns:
        `a.b[2].c` for the path `("a", "b", 2, "c")`; the empty string for the root.

    """
    out = ""
    for step in path:
        out += f"[{step}]" if isinstance(step, int) else (f".{step}" if out else step)
    return out

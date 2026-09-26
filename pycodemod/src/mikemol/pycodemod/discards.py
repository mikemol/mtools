# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Which calls of a function USE its return value and which DISCARD it.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`discards`, `_bare_calls`; W43). A
guard that returns its verdict instead of raising is inert when its caller writes the bare
statement: the complaint prints and the work runs anyway. Finding the call cannot see that, and
checking what goes in cannot either. Both sides are reported, so a list of the broken ones never
reads as the whole population.

⚑ A call DISCARDS its value when it is a bare expression statement, awaited or not. Anything else
(assigned, returned, tested, passed on, walrus-bound) USES it: coarse in the safe direction.

What moved and what did not:

⚑⚑⚑ A DOTTED QUERY FINDS ITS DISCARDS. The origin keyed bare calls by the callee's last name
segment and looked the query up whole, so `ratchet.check_argv` never matched. MEASURED
2026-09-26 on the origin: a bare `ratchet.check_argv(1)` was reported as USING the value, and
the discarded list was empty. Both sides now come from `sites.scan`, which reads a dotted target
as its receiver spelling.

⚑⚑ `await f()` AS A STATEMENT DISCARDS. The origin required the statement's value to be the call
itself, so an awaited call read as used (measured).

⚑⚑ TWO CALLS ON ONE LINE ARE TWO CALLS. The origin joined by (path, line), so in
`check(5); y = check(6)` the used call vanished from the used list (measured). Calls are now
joined on their start position, line and column, from the same libcst walk as `sites.scan`.

⚑ A FILE THAT CANNOT BE READ OR PARSED is reported in `skipped`; the origin's `except Exception`
dropped it from both sides.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from mikemol.pycodemod.sites import Skip, scan

if TYPE_CHECKING:
    from collections.abc import Sequence

type Where = tuple[str, int, int]


@dataclass(frozen=True, slots=True)
class Discards:
    """The calls that use the value, the calls that discard it, and the files not read."""

    using: list[Where] = field(default_factory=list)
    dropped: list[Where] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


class _Bare(cst.CSTVisitor):
    """Collect the start position of every call that is a whole expression statement."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.starts: set[tuple[int, int]] = set()

    @override
    def visit_Expr(self, node: cst.Expr) -> None:
        """Record a statement whose value is a call, or an awaited call."""
        value = node.value
        if isinstance(value, cst.Await):
            value = value.expression
        if isinstance(value, cst.Call):
            start = self.get_metadata(PositionProvider, value).start
            self.starts.add((start.line, start.column))


def _bare_starts(path: str) -> set[tuple[int, int]]:
    """Return the start positions of a file's bare-statement calls; empty if it will not parse.

    Returns:
        (line, column) of each discarding call.

    """
    try:
        module = cst.parse_module(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, cst.ParserSyntaxError):
        return set()
    visitor = _Bare()
    MetadataWrapper(module).visit(visitor)
    return visitor.starts


def discards(name: str, paths: Sequence[str]) -> Discards:
    """Return every call of `name` in `paths`, split by whether its return value is used.

    Returns:
        the using and discarding call positions (path, line, column), with the skipped files.

    """
    sites = scan(paths, name)
    out = Discards(skipped=list(sites.skipped))
    bare: dict[str, set[tuple[int, int]]] = {}
    for key in sorted(sites.facts):
        path, line, column = key[0], key[1], key[2]
        if path not in bare:
            bare[path] = _bare_starts(path)
        target = out.dropped if (line, column) in bare[path] else out.using
        target.append((path, line, column))
    return out

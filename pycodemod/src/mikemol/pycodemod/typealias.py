# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The PEP 695 `type X = ...` statement rewritten as a plain alias `X = ...`.

⚑⚑ CODON HAS NO `type` STATEMENT AND NO `typing.TypeAlias` (probed on 0.20.3, mtools:W1339): a plain
assignment `Row = tuple[int, str]` compiles and runs there, and mypy reads it as an implicit alias,
so it is the one spelling both worlds accept. 68 modules of this tree carry a type statement, and
eight of them hold it in a `TYPE_CHECKING` block that the hoist (`typingblocks`) could not move.

    type Row = tuple[int, str]    ->    Row = tuple[int, str]

⚑ A STATEMENT WITH TYPE PARAMETERS IS LISTED, NOT REWRITTEN: `type Pair[T] = tuple[T, T]` has no
plain spelling that keeps `T` generic in both worlds, so it is a worklist row with its line.

⚑ THE ALIAS IS NOW EVALUATED AT RUN TIME: the right-hand side was lazy under `type` and is eager as
an assignment, so a name it uses must exist when the line runs. A caller checks that with the
project's tests; the verb only changes the statement.
"""

from dataclasses import dataclass
from typing import override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

_KEPT = "a type statement with type parameters has no plain alias spelling"


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, how many statements became aliases, and those left."""

    text: str
    rewritten: int
    kept: tuple[tuple[int, str], ...]


class _Rewriter(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.rewritten = 0
        self.kept: list[tuple[int, str]] = []

    @override
    def leave_TypeAlias(
        self, original_node: cst.TypeAlias, updated_node: cst.TypeAlias
    ) -> cst.BaseSmallStatement:
        """Turn a parameterless type statement into an assignment.

        Returns:
            the assignment, or the statement unchanged when it has type parameters.

        """
        if updated_node.type_parameters is not None:
            line = self.get_metadata(PositionProvider, original_node).start.line
            self.kept.append((line, _KEPT))
            return updated_node
        self.rewritten += 1
        return cst.Assign(
            targets=[cst.AssignTarget(target=updated_node.name)], value=updated_node.value
        )


def plan(text: str) -> Planned:
    """Rewrite every `type X = ...` statement in `text` that has no type parameters.

    Returns:
        the Planned text; unchanged with `rewritten` 0 when there is none.

    """
    rewriter = _Rewriter()
    changed = MetadataWrapper(cst.parse_module(text)).visit(rewriter)
    if not rewriter.rewritten:
        return Planned(text, 0, tuple(rewriter.kept))
    return Planned(changed.code, rewriter.rewritten, tuple(sorted(rewriter.kept)))

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Module-level `if TYPE_CHECKING:` import blocks turned into real imports.

⚑⚑ CODON HAS NO `TYPE_CHECKING`, AND A TYPE-ONLY IMPORT IS ONLY A CYCLE-BREAKER THAT IS RARELY ONE.
Of 453 modules in this tree 346 carry the block; in a leaf module its imports are plain imports that
sit under a guard for no reason, and every annotation that names them must then be quoted once the
`from __future__ import annotations` line goes. So the order is: this verb first, then the future
import (W1357), and almost nothing is left to quote.

    if TYPE_CHECKING:                 ->    from collections.abc import Sequence
        from collections.abc import Sequence

⚑ ONLY A BLOCK OF NOTHING BUT IMPORTS AND WITH NO `else` IS HOISTED. A block that holds anything
else, or an `else`, is a worklist row with its line: it is doing something this verb cannot prove
harmless. The `TYPE_CHECKING` import itself is left for the project's own unused-import fix, which
the judge runs.

⚑ WHAT IT CANNOT SEE IS AN IMPORT CYCLE: hoisting `from pkg.b import B` into `pkg.a` when `pkg.b`
imports `pkg.a` fails at import time, and neither mypy nor ruff reads that. The caller runs the
project's tests as the judge's second check (`cli_typedargs` `selftest`), which fails the file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

if TYPE_CHECKING:
    from collections.abc import Sequence

_KEPT = "a TYPE_CHECKING block that holds more than imports, or an else, is left as it is"


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, how many blocks were hoisted, and the blocks that were not."""

    text: str
    hoisted: int
    kept: tuple[tuple[int, str], ...]


def is_checking(stmt: cst.BaseStatement) -> bool:
    """Say whether a statement is `if TYPE_CHECKING:` or `if typing.TYPE_CHECKING:`.

    Returns:
        True for such an `if` at any level the caller passes.

    """
    if not isinstance(stmt, cst.If):
        return False
    test = stmt.test
    if isinstance(test, cst.Name):
        return test.value == "TYPE_CHECKING"
    return isinstance(test, cst.Attribute) and test.attr.value == "TYPE_CHECKING"


def _type_like(value: cst.BaseExpression) -> bool:
    # A name, a dotted name, a subscript of those, a `|` of those, or a list or tuple of them.
    if isinstance(value, (cst.Name, cst.Attribute)):
        return True
    if isinstance(value, cst.Subscript):
        return _type_like(value.value) and all(
            isinstance(s.slice, cst.Index) and _type_like(s.slice.value) for s in value.slice
        )
    if isinstance(value, cst.BinaryOperation):
        return (
            isinstance(value.operator, cst.BitOr)
            and _type_like(value.left)
            and _type_like(value.right)
        )
    if isinstance(value, (cst.List, cst.Tuple)):
        return all(_type_like(element.value) for element in value.elements)
    return False


def _hoistable(item: cst.BaseSmallStatement) -> bool:
    # An import, or a plain one-name alias (`Row = tuple[int, str]`, what a type statement becomes).
    if isinstance(item, (cst.Import, cst.ImportFrom)):
        return True
    return (
        isinstance(item, cst.Assign)
        and len(item.targets) == 1
        and isinstance(item.targets[0].target, cst.Name)
        and _type_like(item.value)
    )


def _only_imports(block: cst.If) -> bool:
    body = block.body
    if not isinstance(body, cst.IndentedBlock) or block.orelse is not None:
        return False
    return all(
        isinstance(line, cst.SimpleStatementLine) and all(_hoistable(item) for item in line.body)
        for line in body.body
    )


def _is_import_line(stmt: cst.BaseStatement) -> bool:
    return isinstance(stmt, cst.SimpleStatementLine) and all(
        isinstance(item, (cst.Import, cst.ImportFrom)) for item in stmt.body
    )


def _split(block: cst.If) -> tuple[list[cst.SimpleStatementLine], list[cst.SimpleStatementLine]]:
    # The block's lines as (imports, everything else); every line is a SimpleStatementLine here.
    lines = [line for line in block.body.body if isinstance(line, cst.SimpleStatementLine)]
    return [x for x in lines if _is_import_line(x)], [x for x in lines if not _is_import_line(x)]


def _carry(lines: list[cst.SimpleStatementLine], blank: Sequence[cst.EmptyLine]) -> None:
    # Give the first line the blank lines and comments the `if` had.
    if lines:
        carried: list[cst.EmptyLine] = [*blank, *lines[0].leading_lines]
        lines[0] = lines[0].with_changes(leading_lines=carried)


def plan(text: str) -> Planned:
    """Replace every import-only `if TYPE_CHECKING:` block at module level by its contents.

    ⚑ THE IMPORTS GO UP TO THE IMPORT SECTION: after the last import that precedes the block, so a
    block that sat below some code does not leave module-level imports under it (ruff E402). Its
    aliases stay where the block was, after the imports they name.

    Returns:
        the Planned text; unchanged with `hoisted` 0 when there is no such block.

    """
    wrapper = MetadataWrapper(cst.parse_module(text))
    module = wrapper.module
    positions = wrapper.resolve(PositionProvider)
    body: list[cst.SimpleStatementLine | cst.BaseCompoundStatement] = []
    kept: list[tuple[int, str]] = []
    hoisted = 0
    anchor = -1
    for stmt in module.body:
        if not is_checking(stmt) or not isinstance(stmt, cst.If):
            body.append(stmt)
            anchor = len(body) - 1 if _is_import_line(stmt) else anchor
        elif _only_imports(stmt):
            imports, others = _split(stmt)
            if anchor < 0:
                _carry(imports or others, stmt.leading_lines)
                body.extend(imports)
                anchor = len(body) - 1 if imports else anchor
            else:
                _carry(others, stmt.leading_lines)
                body[anchor + 1 : anchor + 1] = imports
                anchor += len(imports)
            body.extend(others)
            hoisted += 1
        else:
            kept.append((positions[stmt].start.line, _KEPT))
            body.append(stmt)
    if not hoisted:
        return Planned(text, 0, tuple(kept))
    return Planned(module.with_changes(body=body).code, hoisted, tuple(kept))

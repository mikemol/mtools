# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the type-statement rewrite (mtools:W1339): a plain alias, or a listed leftover.

⚑ THE CONTROLS ARE WHAT MUST STAY: a statement with type parameters is listed and its text kept, a
module with no type statement comes back byte for byte, and an alias already written plainly is not
touched. The block hoist is shown taking a block that holds imports and the alias this verb leaves.
"""

from __future__ import annotations

from mikemol.pycodemod import typealias, typingblocks

_TWO = 2


def test_a_type_statement_becomes_a_plain_alias() -> None:
    """`type Row = ...` is `Row = ...`, wherever the statement sits."""
    source = "type Row = tuple[int, str]\n\ndef f(r: Row) -> int:\n    return r[0]\n"
    planned = typealias.plan(source)
    assert planned.rewritten == 1
    assert "Row = tuple[int, str]\n" in planned.text
    assert "type Row" not in planned.text


def test_a_type_statement_inside_a_block_is_rewritten_too() -> None:
    """The aliases of a `TYPE_CHECKING` block are statements like any other."""
    source = "if TYPE_CHECKING:\n    type A = int\n    type B = str\n"
    planned = typealias.plan(source)
    assert planned.rewritten == _TWO
    assert "    A = int\n    B = str\n" in planned.text


def test_a_statement_with_type_parameters_is_listed_and_left() -> None:
    """`type Pair[T] = ...` has no plain spelling that keeps T generic; its line is named."""
    source = "type Plain = int\ntype Pair[T] = tuple[T, T]\n"
    planned = typealias.plan(source)
    assert planned.rewritten == 1
    assert [line for line, _ in planned.kept] == [_TWO]
    assert "type Pair[T] = tuple[T, T]" in planned.text


def test_a_recursive_alias_is_listed_and_left_because_it_cannot_name_itself() -> None:
    """`type Json = dict[str, Json] | int` would be a NameError as an assignment: line named."""
    source = "type Json = dict[str, Json] | int\ntype Plain = str\n"
    planned = typealias.plan(source)
    assert planned.rewritten == 1
    assert [line for line, _ in planned.kept] == [1]
    assert "type Json = dict[str, Json] | int" in planned.text
    assert "Plain = str\n" in planned.text


def test_a_module_without_a_type_statement_is_returned_unchanged() -> None:
    """A plain alias is already the target spelling; nothing is rewritten."""
    source = "Row = tuple[int, str]\n"
    planned = typealias.plan(source)
    assert planned.rewritten == 0
    assert planned.text == source


def test_the_hoist_then_takes_a_block_of_imports_and_the_alias() -> None:
    """After the rewrite the block holds imports and one plain alias, and the hoist moves it."""
    source = (
        "from typing import TYPE_CHECKING\n\n"
        "if TYPE_CHECKING:\n    from collections.abc import Callable\n\n"
        "    type Parse = Callable[[str], int]\n"
    )
    rewritten = typealias.plan(source).text
    hoisted = typingblocks.plan(rewritten)
    assert hoisted.hoisted == 1
    assert "if TYPE_CHECKING" not in hoisted.text
    assert "\nParse = Callable[[str], int]\n" in hoisted.text

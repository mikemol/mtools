# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the TYPE_CHECKING hoist (mtools:W1343): imports become real, the rest is kept.

⚑ THE CONTROLS ARE WHAT MUST STAY: a block with an `else`, a block that holds a statement that is
no import, and a module with no guard all come back with their text intact.
"""

from __future__ import annotations

from mikemol.pycodemod import typingblocks

_HEAD = "from typing import TYPE_CHECKING\n\n"


def test_an_import_only_block_is_replaced_by_its_imports() -> None:
    """The `if` goes and both imports stay, at module level."""
    source = _HEAD + "if TYPE_CHECKING:\n    from a import B\n    import c\n\nx = 1\n"
    planned = typingblocks.plan(source)
    assert planned.hoisted == 1
    assert "if TYPE_CHECKING" not in planned.text
    assert "\nfrom a import B\nimport c\n" in planned.text
    assert not planned.kept


def test_the_attribute_form_of_the_guard_is_hoisted_too() -> None:
    """`if typing.TYPE_CHECKING:` is the same guard."""
    source = "import typing\n\nif typing.TYPE_CHECKING:\n    from a import B\n"
    planned = typingblocks.plan(source)
    assert planned.hoisted == 1
    assert "from a import B" in planned.text
    assert "if typing" not in planned.text


def test_a_block_with_an_else_or_a_non_import_is_listed_and_left() -> None:
    """Neither is provably harmless to hoist; each is a worklist row with its line."""
    with_else = _HEAD + "if TYPE_CHECKING:\n    from a import B\nelse:\n    B = None\n"
    with_code = _HEAD + 'if TYPE_CHECKING:\n    from a import B\n    X = len("a")\n'
    for source in (with_else, with_code):
        planned = typingblocks.plan(source)
        assert planned.hoisted == 0
        assert planned.text == source
        assert [line for line, _ in planned.kept] == [3]


def test_a_module_without_the_guard_is_returned_unchanged() -> None:
    """No block, nothing hoisted, text byte for byte."""
    source = "from a import B\n\nx = B\n"
    planned = typingblocks.plan(source)
    assert planned.hoisted == 0
    assert planned.text == source
    assert not planned.kept

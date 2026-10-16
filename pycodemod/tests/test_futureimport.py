# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the future-import verb (mtools:W1326): the import goes, forward names are quoted.

⚑ THE CONTROLS ARE WHAT MUST STAY: a class already defined is not quoted, a name in base position
is listed and left, an import that names another feature is kept, and a module without the import
comes back byte for byte.
"""

from __future__ import annotations

from mikemol.pycodemod import futureimport

_FUTURE = "from __future__ import annotations\n"
_TWO = 2
_LATER = "\n\nclass Later:\n    pass\n"


def test_the_import_is_removed_and_a_later_class_in_an_annotation_is_quoted() -> None:
    """`Later` is defined below the def that names it, so it becomes a string; `int` is not."""
    source = _FUTURE + "def f(x: Later, n: int) -> Later:\n    return x\n" + _LATER
    planned = futureimport.plan(source)
    assert planned.removed
    assert "__future__" not in planned.text
    assert 'def f(x: "Later", n: int) -> "Later":' in planned.text
    assert planned.quoted == _TWO


def test_a_class_naming_itself_is_quoted_and_one_already_defined_is_not() -> None:
    """Inside its own body a class is not yet defined; after it, a use needs no quotes."""
    source = (
        _FUTURE
        + "class A:\n    def me(self) -> A:\n        return self\n\n"
        + "def g(a: A) -> A:\n    return a\n"
    )
    planned = futureimport.plan(source)
    assert 'def me(self) -> "A":' in planned.text
    assert "def g(a: A) -> A:" in planned.text
    assert planned.quoted == 1


def test_a_name_in_base_position_is_listed_and_left_unquoted() -> None:
    """`Later.Inner` and `Later[int]` cannot be quoted at the base; they are named."""
    source = _FUTURE + "def f(x: Later.Inner, y: Later[int]) -> None:\n    pass\n" + _LATER
    planned = futureimport.plan(source)
    assert [name for _, name in planned.unhandled] == ["Later", "Later"]
    assert {line for line, _ in planned.unhandled} == {2}
    assert planned.quoted == 0
    assert "x: Later.Inner" in planned.text


def test_an_import_naming_another_feature_and_a_module_without_one_are_left_alone() -> None:
    """Only the sole `annotations` import goes; no import means the text is returned unchanged."""
    mixed = "from __future__ import annotations, division\nx = 1\n"
    plain = "x = 1\n"
    assert not futureimport.plan(mixed).removed
    assert futureimport.plan(mixed).text == mixed
    assert futureimport.plan(plain).text == plain

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the future-import verb (mtools:W1326, W1353): the import goes, annotations quoted.

⚑ THE CONTROLS ARE WHAT MUST STAY: an annotation naming a class already defined or a run-time
import is not quoted, an annotation holding a quote is listed and left, an import that names another
feature is kept, and a module without the import comes back byte for byte.
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


def test_a_pending_name_in_base_position_quotes_the_whole_annotation() -> None:
    """`Later.Inner` and `Later[int] | None` become one string each; nothing is left over."""
    source = _FUTURE + "def f(x: Later.Inner, y: Later[int] | None) -> None:\n    pass\n" + _LATER
    planned = futureimport.plan(source)
    assert 'x: "Later.Inner"' in planned.text
    assert 'y: "Later[int] | None"' in planned.text
    assert planned.quoted == _TWO
    assert not planned.unhandled


def test_an_annotation_holding_a_quote_is_listed_with_its_line_and_left_alone() -> None:
    """A string inside the annotation would need escapes; it is named for the caller instead."""
    source = _FUTURE + 'def f(x: Literal["a"] | Later) -> None:\n    pass\n' + _LATER
    planned = futureimport.plan(source)
    assert planned.unhandled == ((2, 'Literal["a"] | Later'),)
    assert planned.quoted == 0
    assert 'x: Literal["a"] | Later' in planned.text


def test_a_name_imported_only_under_type_checking_is_quoted_and_a_real_import_is_not() -> None:
    """`Seq` and `numpy` exist only for the checker, so their annotations are quoted; `Path` not."""
    source = (
        _FUTURE
        + "from pathlib import Path\n\n"
        + "from typing import TYPE_CHECKING\n\n"
        + "if TYPE_CHECKING:\n    from collections.abc import Sequence as Seq\n    import numpy\n\n"
        + "def f(a: Seq[int], b: Path, c: numpy.ndarray) -> None:\n    pass\n"
    )
    planned = futureimport.plan(source)
    assert 'a: "Seq[int]"' in planned.text
    assert "b: Path" in planned.text
    assert 'c: "numpy.ndarray"' in planned.text
    assert not planned.unhandled


def test_an_import_naming_another_feature_and_a_module_without_one_are_left_alone() -> None:
    """Only the sole `annotations` import goes; no import means the text is returned unchanged."""
    mixed = "from __future__ import annotations, division\nx = 1\n"
    plain = "x = 1\n"
    assert not futureimport.plan(mixed).removed
    assert futureimport.plan(mixed).text == mixed
    assert futureimport.plan(plain).text == plain

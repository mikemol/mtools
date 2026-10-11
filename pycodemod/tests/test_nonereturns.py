# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `nonereturns`: `-> None` only where the text proves it, everything else a row.

W975. ⚑ THE PLAIN DEF IS THE POSITIVE CONTROL: every refusal below is a def of the same shape that
differs in exactly the one thing the refusal names.
"""

from __future__ import annotations

from mikemol.pycodemod import nonereturns

THIRD = 3


def _why(source: str) -> list[tuple[str, str]]:
    return [(name, why) for _line, name, why in nonereturns.plan(source).worklist]


def test_a_def_with_no_valued_return_is_annotated() -> None:
    """The control: a plain def, a bare return, a method and an async def all take `-> None`."""
    source = (
        "def plain(x):\n    print(x)\n\n"
        "def bare(x):\n    if x:\n        return\n    print(x)\n\n"
        "class C:\n    def method(self):\n        self.a = 1\n\n"
        "async def coro():\n    await go()\n"
    )
    planned = nonereturns.plan(source)
    assert planned.sites == THIRD + 1
    assert planned.text.count(" -> None:") == THIRD + 1
    assert "def plain(x) -> None:" in planned.text
    assert planned.worklist == ()


def test_a_valued_return_is_left_alone_and_named() -> None:
    """`return X` and `return None` both carry a value expression."""
    source = "def f():\n    return 1\n\ndef g():\n    return None\n"
    planned = nonereturns.plan(source)
    assert planned.text == source
    assert _why(source) == [("f", "returns a value"), ("g", "returns a value")]


def test_a_nested_def_or_lambda_return_is_not_the_outer_defs() -> None:
    """The inner function returns a value; the outer one returns nothing and is annotated."""
    source = "def outer():\n    def inner():\n        return 1\n    f = lambda: 2\n    inner()\n"
    planned = nonereturns.plan(source)
    assert "def outer() -> None:" in planned.text
    assert _why(source) == [("inner", "returns a value")]


def test_a_generator_is_left_alone() -> None:
    """A yield, or a yield from, makes the def a generator whatever its returns say."""
    source = "def g():\n    yield 1\n\ndef h():\n    yield from g()\n"
    assert _why(source) == [("g", "generator"), ("h", "generator")]


def test_an_abstract_method_and_an_overload_are_left_alone() -> None:
    """Their bodies promise nothing about the implementation."""
    source = (
        "class A:\n    @abstractmethod\n    def f(self):\n        pass\n\n"
        "    @typing.overload\n    def g(self):\n        pass\n"
    )
    assert _why(source) == [("f", "abstract or overload"), ("g", "abstract or overload")]


def test_a_stub_body_is_left_alone_but_a_docstring_and_pass_is_not() -> None:
    """`...` and `raise NotImplementedError` mean an override fills it in; `pass` is a no-op."""
    source = (
        "def stub():\n    ...\n\n"
        "def todo():\n    raise NotImplementedError\n\n"
        "def todo2():\n    '''doc'''\n    raise NotImplementedError('later')\n\n"
        "def hook():\n    '''doc'''\n    pass\n"
    )
    planned = nonereturns.plan(source)
    assert _why(source) == [
        ("stub", "stub body"),
        ("todo", "stub body"),
        ("todo2", "stub body"),
    ]
    assert "def hook() -> None:" in planned.text
    assert planned.sites == 1


def test_a_def_that_already_has_a_return_annotation_is_untouched() -> None:
    """Neither changed nor listed."""
    source = "def f() -> int:\n    return 1\n\ndef g() -> None:\n    pass\n"
    planned = nonereturns.plan(source)
    assert (planned.text, planned.sites, planned.worklist) == (source, 0, ())


def test_the_worklist_rows_carry_the_defs_line_numbers() -> None:
    """A refusal is findable: `line, name, why`."""
    source = "x = 1\n\n\ndef f():\n    return 1\n"
    assert nonereturns.plan(source).worklist == ((4, "f", "returns a value"),)


def test_a_yield_inside_a_lambda_does_not_make_the_outer_def_a_generator() -> None:
    """The lambda is its own scope: the outer def returns nothing and is annotated."""
    source = "def outer():\n    f = lambda: (yield)\n    f()\n"
    assert "def outer() -> None:" in nonereturns.plan(source).text

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the builtin names Codon 0.20.3 does not define (W1462).

⚑ THE CONTROLS ARE THE NEAREST ACCEPTED SHAPES: the builtins Codon does define are not flagged, a
`property` or `staticmethod` in a decorator position (which Codon compiles) is not flagged while a
bare use of either is, and a name the module binds itself (a parameter, a function, an import)
shadows the builtin and is left alone.
"""

from __future__ import annotations

import ast

from mikemol.hooks import websubset_builtins


def _names(source: str) -> list[str]:
    rows = websubset_builtins.undefined_names(ast.parse(source))
    return [row[2].split("`")[1] for row in rows]


def test_the_measured_missing_builtins_are_flagged_where_they_are_read() -> None:
    """frozenset, callable, classmethod and an except clause on ImportError each give a row."""
    source = (
        "x = frozenset([1])\n"
        "y = callable(print)\n"
        "class K:\n"
        "    @classmethod\n"
        "    def c(cls): ...\n"
        "try:\n"
        "    pass\n"
        "except ImportError:\n"
        "    pass\n"
    )
    assert sorted(_names(source)) == ["ImportError", "callable", "classmethod", "frozenset"]


def test_the_builtins_codon_does_define_are_not_flagged() -> None:
    """The control: a spread of names the measurement found FINE raises nothing."""
    source = "a = [len(x) for x in set(range(3))]\nb = isinstance(a, list)\nprint(dict(), str(1))\n"
    assert _names(source) == []


def test_property_and_staticmethod_are_allowed_as_decorators_and_not_otherwise() -> None:
    """Codon compiles them as decorators (probed), but a bare read of either is undefined."""
    decorated = (
        "class K:\n    @property\n    def p(self): ...\n    @staticmethod\n    def s(): ...\n"
    )
    assert _names(decorated) == []
    assert _names("x = property\ny = staticmethod(len)\n") == ["property", "staticmethod"]


def test_a_name_the_module_binds_itself_is_left_alone() -> None:
    """A parameter, a function, a loop target and an import named like a missing builtin."""
    source = (
        "def f(vars):\n"
        "    return vars\n"
        "def dir():\n"
        "    return dir\n"
        "from os import exit\n"
        "for compile in range(2):\n"
        "    print(compile, exit)\n"
    )
    assert _names(source) == []


def test_a_decorator_name_is_only_exempt_in_the_decorator_position() -> None:
    """A property used as a decorator in one place and read bare in another is flagged once."""
    source = "class K:\n    @property\n    def p(self): ...\nz = property\n"
    assert _names(source) == ["property"]


def test_the_exempt_decorators_are_themselves_in_the_missing_list() -> None:
    """The exemption only means something for names the list holds."""
    assert websubset_builtins.DECORATOR_OK <= websubset_builtins.UNDEFINED

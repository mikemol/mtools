# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the keyword-only marker drop (mtools:W1340): the marker goes, the rest stays.

⚑ THE CONTROLS ARE WHAT MUST STAY: a `*args` marker, a signature whose default order would break,
and a signature with no marker. The result must still parse, which is checked by parsing it.
"""

from __future__ import annotations

import ast

from mikemol.pycodemod import kwonly

_TWO = 2


def test_a_bare_star_is_dropped_and_the_parameters_behind_it_stay_in_order() -> None:
    """`def run(path, *, write, root=None)` loses only the marker."""
    planned = kwonly.plan("def run(path, *, write, root=None):\n    return path\n")
    assert planned.dropped == 1
    assert "def run(path, write, root=None):" in planned.text
    ast.parse(planned.text)


def test_a_marker_first_in_the_list_and_one_before_kwargs_both_go() -> None:
    """`(*, a)` and `(x, *, a, **rest)` keep `**rest` last."""
    planned = kwonly.plan("def f(*, a):\n    pass\n\ndef g(x, *, a, **rest):\n    pass\n")
    assert planned.dropped == _TWO
    assert "def f(a):" in planned.text
    assert "def g(x, a, **rest):" in planned.text
    ast.parse(planned.text)


def test_a_lambda_with_a_bare_star_loses_it_too() -> None:
    """The marker is the same node in a lambda."""
    planned = kwonly.plan("h = lambda x, *, y: x + y\n")
    assert planned.dropped == 1
    assert "lambda x, y:" in planned.text


def test_a_star_args_marker_and_an_unmarked_signature_are_untouched() -> None:
    """`*args` is not bare and a plain signature has nothing to drop."""
    source = "def f(a, *rest, b):\n    pass\n\ndef g(a, b=1):\n    pass\n"
    planned = kwonly.plan(source)
    assert planned.dropped == 0
    assert planned.text == source


def test_a_keyword_only_parameter_without_a_default_after_a_default_is_listed_and_left() -> None:
    """`def f(a, b=1, *, c)` has no plain spelling: the line is named and the text kept."""
    source = "def f(a, b=1, *, c):\n    pass\n"
    planned = kwonly.plan(source)
    assert planned.dropped == 0
    assert planned.text == source
    assert [line for line, _ in planned.kept] == [1]

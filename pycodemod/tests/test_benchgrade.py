# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W2113: the benchmark grader names each hand annotation exact, narrower, none or differ."""

import ast

from mikemol.pycodemod import benchgrade

_BEFORE = """
def a(text):
    return text.strip()

def b(sink):
    sink.write(1)

def c(n):
    return n + 1

def d(table):
    return len(table)

class K:
    def m(self, fn):
        return fn(1)
"""
_AFTER = """
def a(text: str): ...
def b(sink: Sink): ...
def c(n: int): ...
def d(table: Sized): ...
class K:
    def m(self, fn: Callable[[int], int]): ...
def e(x: int): ...
"""


def test_each_hand_annotation_is_graded_against_the_form_narrowing_names() -> None:
    """Exact, a named Protocol as exact, none for an operand, exact for Sized and Callable."""
    graded = benchgrade.grade(_BEFORE, _AFTER)
    assert graded == {
        "a.text": "exact",
        "b.sink": "exact",
        "c.n": "none",
        "d.table": "exact",
        "K.m.fn": "exact",
    }


def test_a_concrete_class_over_a_protocol_is_narrower_and_a_mismatch_differs() -> None:
    """`sink: str` beats the Protocol (narrower); `text: int` is not a str (differ)."""
    after = "def b(sink: str): ...\ndef a(text: int): ...\n"
    graded = benchgrade.grade(_BEFORE, after)
    assert graded == {"b.sink": "narrower", "a.text": "differ"}
    assert benchgrade.totals(graded) == {"exact": 0, "narrower": 1, "none": 0, "differ": 1}


def test_head_reads_subscripts_strings_and_attributes() -> None:
    """`NDArray[...]`, `"Sink"` and `np.ndarray` each name their outer class."""
    heads = [
        benchgrade.head(ast.parse(text, mode="eval").body)
        for text in ("NDArray[float]", '"Sink"', "np.ndarray", "3")
    ]
    assert heads == ["NDArray", "Sink", "ndarray", ""]

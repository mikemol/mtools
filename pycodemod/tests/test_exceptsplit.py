# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the except-tuple split (mtools:W1342): one clause per exception, same body.

⚑ THE CONTROLS ARE WHAT MUST STAY: a single-exception clause and a bare `except:` are untouched, a
tuple holding anything but plain names is listed and left, and the split text means what the
original meant (read from the parsed tree: the same bodies under the same exceptions, in order).
"""

from __future__ import annotations

import ast

from mikemol.pycodemod import exceptsplit

_TWO = 2
_THREE = 3
_TRY = "try:\n    pass\n"
_TUPLE = _TRY + "except (OSError, ValueError):\n    caught = 1\n"


def _handlers(text: str) -> list[ast.ExceptHandler]:
    return [
        h for node in ast.walk(ast.parse(text)) if isinstance(node, ast.Try) for h in node.handlers
    ]


def test_a_tuple_handler_becomes_one_clause_per_exception_with_the_same_body_and_name() -> None:
    """Both clauses keep `as exc` and the body; the tuple is gone."""
    source = _TRY + "except (OSError, ValueError) as exc:\n    log(exc)\n"
    planned = exceptsplit.plan(source)
    assert planned.split == 1
    assert "except OSError as exc:\n    log(exc)\nexcept ValueError as exc:\n    log(exc)\n" in (
        planned.text
    )


def test_dotted_names_are_plain_and_each_handler_of_a_try_is_split_in_place() -> None:
    """`json.JSONDecodeError` splits; a later single clause keeps its place."""
    source = _TRY + "except (json.JSONDecodeError, KeyError):\n    a()\nexcept OSError:\n    b()\n"
    planned = exceptsplit.plan(source)
    assert planned.split == 1
    order = [line for line in planned.text.splitlines() if line.startswith("except")]
    assert order == ["except json.JSONDecodeError:", "except KeyError:", "except OSError:"]


def test_a_single_clause_and_a_bare_except_are_left_alone() -> None:
    """Already the target spelling: nothing is split, the text comes back byte for byte."""
    source = _TRY + "except OSError:\n    a()\nexcept:\n    b()\n"
    planned = exceptsplit.plan(source)
    assert planned.split == 0
    assert planned.text == source


def test_a_tuple_with_a_call_or_a_starred_element_is_listed_and_left() -> None:
    """Splitting `(make(), B)` or `(*errors, B)` is not a text move; the line is named."""
    called = _TRY + "except (make(), ValueError):\n    a()\n"
    starred = _TRY + "except (*errors, ValueError):\n    a()\n"
    for source in (called, starred):
        planned = exceptsplit.plan(source)
        assert planned.split == 0
        assert planned.text == source
        assert [line for line, _ in planned.kept] == [_THREE]


def test_the_split_tree_has_the_same_bodies_under_the_same_exceptions_in_order() -> None:
    """Read from the parsed trees: two clauses where there was a tuple, each with the one body."""
    before = _handlers(_TUPLE)
    after = _handlers(exceptsplit.plan(_TUPLE).text)
    assert len(before) == 1
    assert len(after) == _TWO
    assert [ast.unparse(h.type) for h in after if h.type] == ["OSError", "ValueError"]
    wanted = ast.dump(ast.Module(before[0].body, []))
    assert [ast.dump(ast.Module(h.body, [])) for h in after] == [wanted, wanted]

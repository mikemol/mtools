# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the except-tuple rewrite (mtools:W1342): two exact forms, by position.

⚑ THE CONTROLS ARE WHAT MUST STAY: a single-exception clause and a bare `except:` are untouched, a
tuple holding anything but plain names is listed and left, a tuple that is NOT last keeps its later
sibling able to catch (so it is split into clauses, never widened to `except Exception`), and the
result means what the original meant (read from the parsed tree).
"""

from __future__ import annotations

import ast

from mikemol.pycodemod import exceptsplit

_TWO = 2
_THREE = 3
_TRY = "try:\n    pass\n"


def _handlers(text: str) -> list[ast.ExceptHandler]:
    return [
        h for node in ast.walk(ast.parse(text)) if isinstance(node, ast.Try) for h in node.handlers
    ]


def test_the_last_tuple_handler_becomes_one_clause_with_the_test_moved_inside() -> None:
    """`except Exception as exc:` guards the tuple, re-raises the rest, and keeps the body once."""
    source = _TRY + "except (OSError, ValueError) as exc:\n    log(exc)\n"
    planned = exceptsplit.plan(source)
    assert planned.split == 1
    assert planned.text.endswith(
        "except Exception as exc:\n"
        "    if not isinstance(exc, (OSError, ValueError)):\n"
        "        raise\n"
        "    log(exc)\n"
    )


def test_a_tuple_with_a_later_sibling_is_split_into_clauses_so_the_sibling_still_catches() -> None:
    """`json.JSONDecodeError` splits; the later `OSError` clause keeps its place and its reach."""
    source = _TRY + "except (json.JSONDecodeError, KeyError):\n    a()\nexcept OSError:\n    b()\n"
    planned = exceptsplit.plan(source)
    assert planned.split == 1
    order = [line for line in planned.text.splitlines() if line.startswith("except")]
    assert order == ["except json.JSONDecodeError:", "except KeyError:", "except OSError:"]
    assert "Exception" not in planned.text


def test_a_base_exception_name_widens_the_one_clause_form_to_base_exception() -> None:
    """A tuple naming `KeyboardInterrupt` is not narrowed to `Exception`; no `as` gets a name."""
    planned = exceptsplit.plan(_TRY + "except (KeyboardInterrupt, OSError):\n    a()\n")
    assert "except BaseException as caught:" in planned.text
    assert "isinstance(caught, (KeyboardInterrupt, OSError))" in planned.text


def test_a_single_clause_and_a_bare_except_are_left_alone() -> None:
    """Already the target spelling: nothing is rewritten, the text comes back byte for byte."""
    source = _TRY + "except OSError:\n    a()\nexcept:\n    b()\n"
    planned = exceptsplit.plan(source)
    assert planned.split == 0
    assert planned.text == source


def test_a_tuple_with_a_call_or_a_starred_element_is_listed_and_left() -> None:
    """Rewriting `(make(), B)` or `(*errors, B)` is not a text move; the line is named."""
    called = _TRY + "except (make(), ValueError):\n    a()\n"
    starred = _TRY + "except (*errors, ValueError):\n    a()\n"
    for source in (called, starred):
        planned = exceptsplit.plan(source)
        assert planned.split == 0
        assert planned.text == source
        assert [line for line, _ in planned.kept] == [_THREE]


def test_the_one_clause_tree_keeps_the_body_after_a_bare_reraise_guard() -> None:
    """Read from the parsed tree: one handler, its first statement the guard, the body after it."""
    handlers = _handlers(
        exceptsplit.plan(_TRY + "except (OSError, ValueError):\n    caught_it = 1\n").text
    )
    assert len(handlers) == 1
    guard, body = handlers[0].body
    assert isinstance(guard, ast.If)
    assert isinstance(guard.body[0], ast.Raise)
    assert guard.body[0].exc is None
    assert ast.unparse(body) == "caught_it = 1"


def test_the_clause_form_tree_has_the_same_body_under_each_exception_in_order() -> None:
    """Read from the parsed tree: two clauses where there was a tuple, each with the one body."""
    source = _TRY + "except (OSError, ValueError):\n    caught_it = 1\nexcept KeyError:\n    pass\n"
    after = _handlers(exceptsplit.plan(source).text)
    assert [ast.unparse(h.type) for h in after if h.type] == [
        "OSError",
        "ValueError",
        "KeyError",
    ]
    bodies = [ast.unparse(h.body[0]) for h in after[:_TWO]]
    assert bodies == ["caught_it = 1", "caught_it = 1"]

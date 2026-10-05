# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.referents`: the tokens an expression mentions.

The first six arms are transcribed from the origin selftest (the extractor group); the arms
marked AUTHORED are fresh, covering branches the origin never exercised.
"""

from __future__ import annotations

import ast
from typing import cast

from mikemol.pycodemod import referents as ref


def test_referents_of_none_raises_where_the_origin_returned_the_empty_set() -> None:
    """W664 (declared): `referents(None)` is a `TypeError` here; the origin's was `set()`.

    A caller passes the empty tuple for no expression, so `None` is a bug it should see rather than
    an empty referent set that reads as "mentions nothing".
    """
    raised = False
    try:
        ref.referents(cast("ast.AST", None))
    except TypeError:
        raised = True
    assert raised
    assert ref.referents(()) == set()


def test_referents_names_attributes_keywords_and_identifier_strings() -> None:
    """Names, attributes, keywords and identifier strings are all referents."""
    got = ref.referents(ast.parse('f(row["core_id"], sys.argv, key=lim) or 17'))
    assert sorted(got) == ["argv", "core_id", "f", "key", "lim", "row", "sys"]


def test_numeric_constant_is_not_a_referent() -> None:
    """A numeric constant contributes nothing."""
    assert "17" not in ref.referents(ast.parse("x or 17"))


def test_non_identifier_string_is_not_a_referent() -> None:
    """A SQL blob contributes nothing; only the call name stays."""
    assert ref.referents(ast.parse('g("select * from t")')) == {"g"}


def test_dotted_string_contributes_each_part() -> None:
    """A dotted identifier string yields each part."""
    assert sorted(ref.referents(ast.parse('h("a.b")'))) == ["a", "b", "h"]


def test_over_long_token_is_dropped() -> None:
    """A token one past the bound spells nothing."""
    assert ref.token_parts("z" * (ref.MAX_TOKEN + 1)) == ()


def test_string_and_attribute_are_one_referent() -> None:
    """The string "terms" and the attribute .terms are the same referent."""
    both = ref.referents(ast.parse('q("terms")')) & ref.referents(ast.parse("x.terms"))
    assert both == {"terms"}


def test_token_at_the_bound_is_kept() -> None:
    """AUTHORED: the bound is inclusive, so a token of exactly MAX_TOKEN survives."""
    assert ref.token_parts("z" * ref.MAX_TOKEN) == ("z" * ref.MAX_TOKEN,)


def test_token_parts_refuses_non_strings_and_empty() -> None:
    """AUTHORED: an int, None, bytes and the empty string spell nothing."""
    assert [ref.token_parts(v) for v in (17, None, b"abc", "")] == [()] * 4


def test_token_parts_refuses_any_bad_dotted_part() -> None:
    """AUTHORED: one non-identifier part voids the whole string."""
    assert [ref.token_parts(v) for v in ("a..b", "a.1b", ".a", "a-b")] == [()] * 4


def test_token_parts_splits_a_dotted_identifier() -> None:
    """AUTHORED: the positive path returns the parts in order."""
    assert ref.token_parts("x.y.z") == ("x", "y", "z")


def test_referents_accepts_a_sequence_of_nodes() -> None:
    """AUTHORED: a list of nodes is unioned, and a repeated token is one referent."""
    nodes = [ast.parse("a.b").body[0], ast.parse("c(b)").body[0]]
    assert ref.referents(nodes) == {"a", "b", "c"}


def test_keyword_unpacking_has_no_name() -> None:
    """AUTHORED: `**kw` is a keyword with no arg, contributing only the name `kw`."""
    assert ref.referents(ast.parse("f(**kw)")) == {"f", "kw"}

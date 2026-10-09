# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `orempty`: a cast around `X or <empty>` becomes the project's typed narrowers."""

from __future__ import annotations

from mikemol.pycodemod import orempty

HELPERS = orempty.Helpers(module="checks.jsonio")
THREE = 3

SOURCE = """\
from __future__ import annotations

from typing import cast

Json = dict[str, object]


def f(doc: Json) -> int:
    data = cast("Json", doc.get("data") or {})
    rows = cast("list[Json]", data.get("rows") or [])
    names = cast("list[object]", data.get("names") or [])
    other = cast("dict[str, str]", data.get("o") or {})
    return len(rows) + len(names) + len(other)
"""

REWRITTEN = """\
from __future__ import annotations

from typing import cast
from checks.jsonio import as_list, as_object

Json = dict[str, object]


def f(doc: Json) -> int:
    data = as_object(doc.get("data"))
    rows = [as_object(each) for each in as_list(data.get("rows"))]
    names = as_list(data.get("names"))
    other = cast("dict[str, str]", data.get("o") or {})
    return len(rows) + len(names) + len(other)
"""


def test_the_three_shapes_are_rewritten_and_the_import_added() -> None:
    """⚑ Json, list[Json] and list[object] casts become helpers; the import follows the last."""
    got = orempty.plan(SOURCE, HELPERS)
    assert got.text == REWRITTEN
    assert got.sites == THREE
    assert got.needs == ("as_list", "as_object")


def test_a_cast_to_another_type_is_left_alone() -> None:
    """⚑ `dict[str, str]` needs its values narrowed too, so it is not a site here."""
    got = orempty.plan(SOURCE, HELPERS)
    assert 'cast("dict[str, str]", data.get("o") or {})' in got.text


def test_a_source_with_no_site_is_returned_unchanged() -> None:
    """⚑ Nothing matched: the text is byte-identical, sites is 0, no import appears."""
    text = "from typing import cast\n\nx = cast(int, 3)\n"
    got = orempty.plan(text, HELPERS)
    assert got.text == text
    assert got.sites == 0
    assert got.needs == ()


def test_a_type_and_literal_that_disagree_are_left_alone() -> None:
    """⚑ `cast("Json", X or [])` is not provable as an object, so it stays."""
    text = 'from typing import cast\n\nx = cast("Json", a or [])\n'
    got = orempty.plan(text, HELPERS)
    assert got.text == text
    assert got.sites == 0


def test_the_helper_names_are_the_callers() -> None:
    """⚑ A project names its own helpers; nothing here assumes `as_object`."""
    helpers = orempty.Helpers(module="pkg.narrow", object_fn="obj", list_fn="seq")
    text = 'from typing import cast\n\nx = cast("Json", a or {})\n'
    got = orempty.plan(text, helpers)
    assert got.text == "from typing import cast\nfrom pkg.narrow import obj\n\nx = obj(a)\n"
    assert got.needs == ("obj",)

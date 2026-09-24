# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 2: the walk yields every string in a record, and only strings.

Every fixture is SYNTHETIC and built inline. Real transcript excerpts are held by substrate's
operator and do not enter this tree.
"""

from __future__ import annotations

from mikemol.transcriptstruct.records import AttachmentRecord, parse_line
from mikemol.transcriptstruct.walk import Leaf, render, strings

_HIDDEN = "synthetic directive the typed reader never looks for"


def test_a_string_nested_in_an_unknown_field_is_yielded_with_its_path() -> None:
    """A string under a field no decoder knows is still found, at the path that reaches it.

    ⚑ This is the backstop's whole job: the old reader was blind to three shapes because it
    read only the fields it knew. The walk knows none, so it cannot be blind to one.
    """
    env = {"type": "novel", "deep": {"list": [0, {"note": _HIDDEN}]}}
    assert list(strings(env)) == [
        Leaf(("type",), "novel"),
        Leaf(("deep", "list", 1, "note"), _HIDDEN),
    ]


def test_non_string_scalars_yield_nothing() -> None:
    """Numbers, booleans and null are not strings: a record of only scalars yields no leaves."""
    assert list(strings({"a": 1, "b": True, "c": None, "d": [2.5]})) == []


def test_leaves_come_in_document_order() -> None:
    """Keys are walked in file order and list items in index order, so output order is stable."""
    env = {"z": "first", "a": ["second", "third"], "m": "fourth"}
    assert [leaf.text for leaf in strings(env)] == ["first", "second", "third", "fourth"]


def test_the_walk_reaches_an_attachment_prompt_through_record_raw() -> None:
    """A decoded attachment's `raw` walks to its prompt: stage 1 and stage 2 compose."""
    line = (
        '{"type": "attachment", "message": null,'
        ' "attachment": {"type": "queued_command", "prompt": "' + _HIDDEN + '"}}'
    )
    record = parse_line(line, 1)
    assert isinstance(record, AttachmentRecord)
    assert Leaf(("attachment", "prompt"), _HIDDEN) in list(strings(record.raw))


def test_render_spells_a_path_as_it_is_grepped() -> None:
    """`("a", "b", 2, "c")` renders as `a.b[2].c`, and the root as the empty string."""
    assert render(("a", "b", 2, "c")) == "a.b[2].c"
    assert not render(())


def test_a_path_that_starts_with_an_index_renders_without_a_leading_dot() -> None:
    """A top-level list's leaf renders `[0].x`, not `.[0].x` or `0.x`."""
    assert render((0, "x")) == "[0].x"

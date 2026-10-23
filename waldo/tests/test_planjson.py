# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The typed JSON boundary narrows without raising and gives empty for what is not there (W1845).

⚑ ABSENT IS EMPTY, NEVER A GUESS: a missing key, a non-object step, or a value of the wrong shape
reads as an empty object or list (or None for a parse), so a policy verdict that finds nothing
reads as nothing.
"""

from mikemol.waldo import planjson

_DOC = {"result": [{"expressions": [{"value": ["a", "b"]}]}], "n": 3}


def test_a_text_is_parsed_only_when_it_is_json_and_an_object_only_when_it_is_one() -> None:
    """Not JSON is None; JSON that is not an object is None for parse_object, a value for parse."""
    assert planjson.parse("{") is None
    assert planjson.parse("[1, 2]") == [1, 2]
    assert planjson.parse_object("[1, 2]") is None
    assert planjson.parse_object('{"a": 1}') == {"a": 1}


def test_a_value_is_viewed_as_a_list_or_an_object_or_empty() -> None:
    """The right shape passes through; any other is the empty one."""
    assert planjson.as_list([1]) == [1]
    assert planjson.as_list({"a": 1}) == []
    assert planjson.as_object({"a": 1}) == {"a": 1}
    assert planjson.as_object([1]) == {}


def test_a_path_is_followed_through_objects_and_a_broken_step_is_empty() -> None:
    """list_at and obj_at follow nested objects and give empty at the first missing or odd step."""
    assert planjson.list_at(_DOC, "result") == _DOC["result"]
    assert planjson.obj_at(_DOC, "missing") == {}
    assert planjson.list_at(_DOC, "n", "deeper") == []
    assert planjson.list_at(_DOC, "result", "deeper") == []
    assert planjson.list_at(None, "result") == []

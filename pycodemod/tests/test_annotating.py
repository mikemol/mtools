# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The annotating planner writes observed types into the gaps and touches nothing else."""

from mikemol.pycodemod import annotating
from mikemol.pycodemod.observed import Signature

_SOURCE = (
    "class Box:\n"
    "    def put(self, key, value=1, *, tag):  # kept\n"
    "        return key\n"
    "\n"
    "def total(items: list[int], extra):\n"
    "    return 1\n"
)
_SEEN = {
    "Box.put": Signature(
        params={"key": {"str"}, "value": {"int"}, "tag": {"None", "str"}}, returns={"str"}
    ),
    "total": Signature(params={"items": {"list[int]"}, "extra": {"int"}}, returns={"int"}),
}
_PUT = "    def put(self, key: str, value: int=1, *, tag: str | None) -> str:  # kept\n"
_TOTAL = "def total(items: list[int], extra: int) -> int:\n"
_SITES = 6


def test_gaps_are_filled_in_place_and_comments_stay() -> None:
    """Parameters with and without defaults and the return get their observed types."""
    planned = annotating.plan(_SOURCE, _SEEN)
    lines = planned.text.splitlines(keepends=True)
    assert lines[1] == _PUT
    assert lines[4] == _TOTAL
    assert planned.sites == _SITES


def test_a_written_annotation_is_never_replaced() -> None:
    """`items` already says `list[int]`; a different observation leaves it alone."""
    seen = {"total": Signature(params={"items": {"str"}}, returns=set())}
    planned = annotating.plan(_SOURCE, seen)
    assert "items: list[int]" in planned.text
    assert planned.sites == 0


def test_a_type_that_needs_an_import_goes_to_the_worklist() -> None:
    """`numpy.ndarray` is not written, and is listed with the parameter's name."""
    seen = {"total": Signature(params={"extra": {"numpy.ndarray"}}, returns={"int"})}
    planned = annotating.plan(_SOURCE, seen)
    assert "extra:" not in planned.text
    assert ("total(extra)", "the observed type needs an import") in planned.worklist
    assert "-> int" in planned.text


def test_a_function_the_run_never_reached_is_untouched() -> None:
    """No observation, no edit, no worklist entry."""
    planned = annotating.plan(_SOURCE, {})
    assert planned.text == _SOURCE
    assert planned.worklist == ()

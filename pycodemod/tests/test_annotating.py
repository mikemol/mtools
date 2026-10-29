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


_EXIT_SOURCE = (
    "class Guard:\n"
    "    def __exit__(self, kind, value, tb):\n"
    "        return False\n"
    "\n"
    "    def __aexit__(self, kind, value, tb):\n"
    "        return None\n"
)


def test_an_exit_observed_returning_bool_is_a_candidate_not_an_annotation() -> None:
    """W1924 (el-openglo's first annotate run): a run that saw only False must not write `-> bool`.

    mypy refuses it for an `__exit__` that always returns False, and the observer keeps types, not
    values; the site goes to the worklist, while the same exit observed returning None is annotated.
    """
    seen = {
        "Guard.__exit__": Signature(params={}, returns={"bool"}),
        "Guard.__aexit__": Signature(params={}, returns={"None"}),
    }
    planned = annotating.plan(_EXIT_SOURCE, seen)
    assert "def __exit__(self, kind, value, tb):" in planned.text
    assert "def __aexit__(self, kind, value, tb) -> None:" in planned.text
    assert ("Guard.__exit__()", "an observed bool return of an exit may be Literal[False]") in (
        planned.worklist
    )


def test_a_traceback_observed_by_name_goes_to_the_worklist_not_bare() -> None:
    """The observer spells a traceback `types.TracebackType`, a dotted name needing an import."""
    seen = {"Guard.__exit__": Signature(params={"tb": {"types.TracebackType"}}, returns=set())}
    planned = annotating.plan(_EXIT_SOURCE, seen)
    assert "tb:" not in planned.text
    assert ("Guard.__exit__(tb)", "the observed type needs an import") in planned.worklist


def test_a_function_the_run_never_reached_is_untouched() -> None:
    """No observation, no edit, no worklist entry."""
    planned = annotating.plan(_SOURCE, {})
    assert planned.text == _SOURCE
    assert planned.worklist == ()

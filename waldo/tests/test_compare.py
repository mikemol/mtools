# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the refuse-with-diff core: allowed superset, required rows, action order.

W1055. ⚑ THE CLEAN PLAN IS THE POSITIVE CONTROL: a plan inside the set is clean, so a refused plan
means something, and the converged case (a row absent from the plan) is clean too, which is the
reason the declared set is a superset and not an exact match.
"""

from __future__ import annotations

import pytest

from mikemol.waldo.compare import (
    ChangeShapeError,
    Diff,
    change_of,
    changes_from,
    compare,
    render,
    shown,
)

_NS = 'module.w45.kubernetes_namespace_v1.throwaway["amr-skills"]'
_SA = 'module.w45.kubernetes_service_account_v1.peer["amr-skills"]'
_JOB = 'module.forgejo.kubernetes_job_v1.forgejo_admin["forgejo"]'
_CREATE = change_of(_NS, ["create"])
_UPDATE_JOB = change_of(_JOB, ["update"])
_ONE = 1


def test_a_plan_inside_the_allowed_set_is_clean() -> None:
    """The positive control: every planned change is allowed, nothing is required."""
    diff = compare({_CREATE, _UPDATE_JOB}, set(), {_CREATE})
    assert diff.clean()
    assert not render(diff)


def test_an_already_converged_row_is_simply_absent_and_still_clean() -> None:
    """The allowed set is a superset: allowed rows missing from the plan are not a difference."""
    assert compare({_CREATE, _UPDATE_JOB}, set(), set()).clean()


def test_a_planned_change_outside_the_set_is_extra() -> None:
    """A row the plan makes that nobody allowed is refused and printed with a plus."""
    diff = compare({_CREATE}, set(), {_CREATE, _UPDATE_JOB})
    assert not diff.clean()
    assert diff.extra == (_UPDATE_JOB,)
    assert render(diff) == [f"+ {_JOB} update"]


def test_the_same_address_with_other_actions_is_extra() -> None:
    """Allowing a create does not allow a delete of the same address."""
    delete = change_of(_NS, ["delete"])
    diff = compare({_CREATE}, set(), {delete})
    assert diff.extra == (delete,)


def test_a_required_change_the_plan_lacks_is_missing() -> None:
    """Only required rows must be present; the diff prints it with a minus."""
    diff = compare({_CREATE, _UPDATE_JOB}, {_CREATE}, {_UPDATE_JOB})
    assert diff.missing == (_CREATE,)
    assert render(diff) == [f"- {_NS} create"]


def test_missing_lines_precede_extra_lines() -> None:
    """The printed diff reads required-but-absent first, then planned-but-undeclared."""
    diff = compare(set(), {_CREATE}, {_UPDATE_JOB})
    assert render(diff) == [f"- {_NS} create", f"+ {_JOB} update"]


def test_action_order_inside_a_replace_is_not_a_difference() -> None:
    """Delete then create and create then delete are one change."""
    forward = change_of(_NS, ["create", "delete"])
    backward = change_of(_NS, ["delete", "create"])
    assert forward == backward
    assert compare({forward}, set(), {backward}).clean()


def test_a_replace_renders_its_actions_joined_with_plus() -> None:
    """A two-action change prints as create+delete in the diff and in the planned rows."""
    replace = change_of(_SA, ["delete", "create"])
    assert render(Diff((), (replace,))) == [f"+ {_SA} create+delete"]
    assert shown({replace, _CREATE}) == [f"create {_NS}", f"create+delete {_SA}"]


def test_rows_are_read_into_a_set_and_an_absent_list_is_empty() -> None:
    """Parsed rows become changes; None is the empty set, not an error."""
    rows = [{"address": _NS, "actions": ["create"]}, {"address": _JOB, "actions": ["update"]}]
    assert changes_from(rows) == {_CREATE, _UPDATE_JOB}
    assert changes_from(None) == set()


@pytest.mark.parametrize(
    "rows",
    [
        "not a list",
        ["not an object"],
        [{"actions": ["create"]}],
        [{"address": "", "actions": ["create"]}],
        [{"address": _NS}],
        [{"address": _NS, "actions": []}],
        [{"address": _NS, "actions": "create"}],
        [{"address": _NS, "actions": ["create", _ONE]}],
    ],
)
def test_a_malformed_row_is_refused_not_skipped(rows: object) -> None:
    """A row that is not an address with a list of text actions raises, naming where."""
    with pytest.raises(ChangeShapeError, match="changes"):
        changes_from(rows)


def test_a_value_that_is_not_a_list_is_named_as_such() -> None:
    """A string or a number where rows belong is refused as a non-list, not read row by row."""
    with pytest.raises(ChangeShapeError, match="expected a list of change rows"):
        changes_from("create")


def test_the_error_names_the_row_that_is_wrong() -> None:
    """The index of the bad row is in the message so a set file can be fixed."""
    rows = [{"address": _NS, "actions": ["create"]}, {"address": _JOB}]
    with pytest.raises(ChangeShapeError, match=r"allowed\[1\]"):
        changes_from(rows, "allowed")

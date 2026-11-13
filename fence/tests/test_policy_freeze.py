# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the freeze keys of a guard row: action, resume_samples, max_frozen_samples, on_cap.

⚑ THE LEGACY ROW IS THE NEGATIVE CONTROL: a row with no `action` must still read as the one-shot
signal every host file written before W2356 declares, or the guard on this host would run UNGUARDED.
"""

from __future__ import annotations

import pytest

from mikemol.fence import policy

_GOOD: dict[str, object] = {
    "name": "kine-latency",
    "reading": "promql",
    "endpoint": "vmsingle-http",
    "query": "up",
    "above": 4.0,
    "samples": 6,
    "interval_s": 30,
    "signal": "SIGINT",
    "target": "bazel",
}
_FREEZE: dict[str, object] = {
    "action": "freeze",
    "resume_samples": 4,
    "max_frozen_samples": 40,
    "on_cap": "kill",
}


def _faults(**changes: object) -> list[str]:
    """Parse a freeze row with the given keys changed (a value of None drops the key).

    Returns:
        the problems the parser reports.

    """
    row = {k: v for k, v in {**_GOOD, **_FREEZE, **changes}.items() if v is not None}
    with pytest.raises(policy.PolicyError) as caught:
        policy.parse({"guard": [row]})
    return caught.value.problems


def test_a_row_with_no_action_is_the_one_shot_signal() -> None:
    """The legacy file keeps its meaning: action signal, no freeze counts."""
    (spec,) = policy.parse({"guard": [_GOOD]})
    assert (spec.row.action, spec.row.resume_hold, spec.row.max_frozen, spec.row.on_cap) == (
        "signal",
        0,
        0,
        "",
    )


def test_a_freeze_row_carries_its_four_keys_into_the_row() -> None:
    """The positive control: each freeze key lands where the watcher reads it."""
    (spec,) = policy.parse({"guard": [{**_GOOD, **_FREEZE}]})
    row = spec.row
    assert (row.action, row.resume_hold, row.max_frozen, row.on_cap) == ("freeze", 4, 40, "kill")


@pytest.mark.parametrize("key", ["resume_samples", "max_frozen_samples", "on_cap"])
def test_a_freeze_row_missing_a_key_names_it(key: str) -> None:
    """No default stands in for a freeze limit, least of all the cap's action."""
    assert any(f"needs key {key!r}" in line for line in _faults(**{key: None}))


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"action": "pause"}, "action must be one of"),
        ({"on_cap": "ignore"}, "on_cap must be one of"),
        ({"resume_samples": 0}, "'resume_samples' must be an integer of at least 1"),
        ({"max_frozen_samples": True}, "'max_frozen_samples' must be an integer of at least 1"),
    ],
)
def test_a_wrong_freeze_value_is_named(change: dict[str, object], fragment: str) -> None:
    """Each wrong value says which key and what it wanted."""
    assert any(fragment in line for line in _faults(**change))


def test_a_signal_row_may_not_carry_a_freeze_key() -> None:
    """`on_cap` on a signal row would read as a cap that never fires."""
    with pytest.raises(policy.PolicyError) as caught:
        policy.parse({"guard": [{**_GOOD, "on_cap": "kill"}]})
    assert any("only applies to action = 'freeze'" in line for line in caught.value.problems)

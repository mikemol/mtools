# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the guard policy: a declared row is read whole, and every fault is named (W921).

⚑ THE VALID ROW IS THE POSITIVE CONTROL: without it, "a wrong row is refused" cannot be told from a
parser that refuses everything.
"""

from __future__ import annotations

import signal
from typing import TYPE_CHECKING

import pytest

from mikemol.fence import policy

if TYPE_CHECKING:
    from pathlib import Path

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
_TOML = """
[[guard]]
name = "kine-latency"
reading = "promql"
endpoint = "vmsingle-http"
query = 'histogram_quantile(0.99, sum by (le) (rate(x_bucket[5m])))'
above = 4.0
samples = 6
interval_s = 30
signal = "SIGINT"
target = "bazel"
"""


def _fault(**changes: object) -> list[str]:
    """Parse one row with the given keys changed (a value of None drops the key).

    Returns:
        the problems the parser reports.

    """
    row = {**_GOOD, **changes}
    row = {k: v for k, v in row.items() if v is not None}
    with pytest.raises(policy.PolicyError) as caught:
        policy.parse({"guard": [row]})
    return caught.value.problems


def test_a_valid_row_is_read_into_a_spec() -> None:
    """The positive control: every key lands where the watcher reads it."""
    (spec,) = policy.parse({"guard": [_GOOD]})
    assert (spec.endpoint, spec.query) == ("vmsingle-http", "up")
    row = spec.row
    assert (row.name, row.above, row.hold, row.interval_s) == ("kine-latency", 4.0, 6, 30.0)
    assert (row.signal, row.target) == (int(signal.SIGINT), "bazel")


def test_a_policy_with_no_guard_table_declares_none() -> None:
    """An empty document, or one with other tables only, is no guard and no error."""
    assert policy.parse({}) == []
    assert policy.parse({"other": {}}) == []


def test_a_missing_file_is_no_guard_and_a_toml_file_is_read(tmp_path: Path) -> None:
    """Absent means none; present is parsed."""
    assert policy.load(tmp_path / "absent.toml") == []
    path = tmp_path / "guards.toml"
    path.write_text(_TOML, encoding="utf-8")
    assert [spec.row.name for spec in policy.load(path)] == ["kine-latency"]


def test_a_file_that_is_not_toml_is_a_problem_naming_the_file(tmp_path: Path) -> None:
    """The policy exists and is wrong."""
    path = tmp_path / "guards.toml"
    path.write_text("[[guard\n", encoding="utf-8")
    with pytest.raises(policy.PolicyError) as caught:
        policy.load(path)
    assert str(path) in caught.value.problems[0]


def test_every_missing_key_is_named() -> None:
    """No default stands in for a limit: each absent key is a problem of its own."""
    found = _fault(above=None, samples=None, target=None)
    assert any("missing key 'above'" in line for line in found)
    assert any("missing key 'samples'" in line for line in found)
    assert any("missing key 'target'" in line for line in found)


def test_an_unknown_key_is_a_problem_so_a_typo_cannot_guard_less() -> None:
    """`sample = 6` instead of `samples` is refused, not ignored."""
    found = _fault(sample=6)
    assert any("unknown key 'sample'" in line for line in found)


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"reading": "graphite"}, "reading must be one of"),
        ({"above": "high"}, "'above' must be a number"),
        ({"above": True}, "'above' must be a number"),
        ({"samples": 0}, "'samples' must be an integer of at least 1"),
        ({"samples": 2.5}, "'samples' must be an integer of at least 1"),
        ({"samples": True}, "'samples' must be an integer of at least 1"),
        ({"interval_s": 0}, "'interval_s' must be a positive number"),
        ({"signal": "SIGNOPE"}, "'signal' must name a signal"),
        ({"target": ""}, "'target' must be a non-empty string"),
        ({"endpoint": 7}, "'endpoint' must be a non-empty string"),
    ],
)
def test_a_wrong_value_is_named(change: dict[str, object], fragment: str) -> None:
    """Each wrong value is a problem that says which key and what it wanted."""
    assert any(fragment in line for line in _fault(**change))


def test_every_table_is_checked_and_all_problems_come_together() -> None:
    """Two bad tables report both; a good one beside them is not lost to the first fault."""
    bad_one = {**_GOOD, "samples": 0}
    bad_two = {**_GOOD, "signal": "SIGNOPE"}
    with pytest.raises(policy.PolicyError) as caught:
        policy.parse({"guard": [_GOOD, bad_one, bad_two]})
    assert len(caught.value.problems) == len(["samples", "signal"])
    assert "guard #2" in caught.value.problems[0]
    assert "guard #3" in caught.value.problems[1]


def test_a_guard_that_is_not_an_array_of_tables_is_refused() -> None:
    """`guard = 3` or a non-table element is a problem, not a crash."""
    for doc in ({"guard": 3}, {"guard": [3]}):
        with pytest.raises(policy.PolicyError):
            policy.parse(doc)

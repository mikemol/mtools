# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""luthen's gate CPU series become the cost table, paired only where all three agree (W1997).

⚑ THE CONTROLS: a target one series lacks, another repo's row, a non-test label and a torn row are
each left out, never filled in.
"""

from mikemol.importdag import series
from mikemol.importdag.cost import Measured


def _resp(rows: list[dict[str, object]]) -> dict[str, object]:
    return {"status": "success", "data": {"resultType": "vector", "result": rows}}


def _row(repo: str, target: str, value: str) -> dict[str, object]:
    return {"metric": {"repo": repo, "target": target}, "value": [1.0, value]}


def _trio(value: str) -> list[dict[str, object]]:
    """Build a test target, a non-test label and another repo's test, all with one value.

    Returns:
        the three rows.

    """
    return [
        _row("mtools", "//hooks:test_a", value),
        _row("mtools", "//hooks:lint", value),
        _row("other", "//hooks:test_b", value),
    ]


def test_three_series_join_into_measured_by_test_path() -> None:
    """A target all three name is priced under its test path, with its sample count."""
    t = "//hooks:test_watchdog"
    got = series.table(
        "mtools",
        _resp([_row("mtools", t, "1.5")]),
        _resp([_row("mtools", t, "4.0")]),
        _resp([_row("mtools", t, "9")]),
    )
    assert got == {"tests/test_watchdog.py": Measured(1.5, 4.0, 9)}


def test_missing_series_other_repo_non_test_and_torn_rows_are_left_out() -> None:
    """Each way a row can lie leaves the target out of the table."""
    torn: dict[str, object] = {"metric": {"repo": "mtools", "target": "//hooks:test_c"}}
    med = _resp([*_trio("1"), {**torn, "value": [1.0]}])
    both = _resp([*_trio("2"), {**torn, "value": [1.0, "2"]}])
    assert series.table("mtools", med, both, _resp([])) == {}
    count = _resp([*_trio("3"), {**torn, "value": [1.0, "3"]}])
    assert series.table("mtools", med, both, count) == {"tests/test_a.py": Measured(1.0, 2.0, 3)}
    assert series.table("mtools", {}, {}, {}) == {}

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The outcome -> column map: declared total, every cell in exactly one column (W374)."""

from itertools import product, starmap

from mikemol.pytestspec import outcomes


def test_the_declared_map_is_total_and_functional() -> None:
    """Every verdict x expect x disposition cell lands in exactly one known column."""
    assert outcomes.problems(outcomes.RULES) == []
    cells = product(outcomes.VERDICTS, outcomes.EXPECTS, outcomes.DISPOSED)
    landed = set(starmap(outcomes.column, cells))
    assert landed <= set(outcomes.OUTCOME_COLUMNS)


def test_a_gap_is_reported() -> None:
    """Dropping a rule leaves cells in no column, and the check names them."""
    found = outcomes.problems(outcomes.RULES[1:])
    assert found
    assert all("lands in 0 columns" in p for p in found)


def test_an_overlap_is_reported() -> None:
    """A rule duplicated under another column puts its cells in two, and the check names them."""
    first = outcomes.RULES[0]
    clash = (first[0], first[1], first[2], outcomes.ADMITTED)
    found = outcomes.problems((*outcomes.RULES, clash))
    assert found
    assert all("lands in 2 columns" in p for p in found)


def test_an_unknown_column_is_reported() -> None:
    """A rule naming a column the line does not print is refused."""
    first = outcomes.RULES[0]
    renamed = (first[0], first[1], first[2], "nowhere")
    assert "unknown column 'nowhere'" in outcomes.problems((renamed, *outcomes.RULES[1:]))

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `trend`: a ratchet's value at past commits and its direction (W1908)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet import trend

if TYPE_CHECKING:
    from pathlib import Path

_NAME = "ratchet-preview.txt"
_TWO = 2
_THREE = 3
_FOUR = 4


def _text(count: int) -> str:
    return "".join(f"entry-{n}\n" for n in range(count))


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([40, 30, 10], trend.FALLING),
        ([10, 30, 40], trend.RISING),
        ([7, 7, 7], trend.FLAT),
        ([5], trend.UNKNOWN),
        ([None, None], trend.UNKNOWN),
        ([], trend.UNKNOWN),
    ],
)
def test_the_direction_is_read_from_the_ends_of_the_values_that_were_read(
    values: list[int | None], expected: str
) -> None:
    """Falling, rising and flat go by first and last; fewer than two readings is unknown."""
    assert trend.direction(values) == expected


def test_a_noisy_middle_commit_does_not_flip_the_direction() -> None:
    """Ends, not steps: 40, 90, 10 is paydown overall, whatever the middle commit held."""
    assert trend.direction([40, 90, 10]) == trend.FALLING


def test_a_revision_that_cannot_be_read_is_skipped_not_counted_as_zero() -> None:
    """None between two readings is skipped; read as 0 it would make 40 then 40 look rising."""
    assert trend.direction([40, None, 40]) == trend.FLAT
    assert trend.direction([None, 40, 10]) == trend.FALLING


def test_a_revision_is_counted_by_the_census_rule_under_the_files_own_name(
    tmp_path: Path,
) -> None:
    """The text a revision held is read by kinds.value_of: a preview file counts its entries."""
    assert trend.value_at(_NAME, _text(_THREE), tmp_path) == _THREE
    assert trend.value_at(_NAME, None, tmp_path) is None


def test_history_pairs_each_revision_with_its_value_in_the_order_given(
    tmp_path: Path,
) -> None:
    """A revision that does not hold the file keeps None in its place, never a dropped row."""
    held = {"old": _text(_FOUR), "mid": None, "new": _text(_TWO)}
    series = trend.history(_NAME, ["old", "mid", "new"], held.get, tmp_path)
    assert series == [("old", _FOUR), ("mid", None), ("new", _TWO)]
    assert trend.direction([value for _rev, value in series]) == trend.FALLING

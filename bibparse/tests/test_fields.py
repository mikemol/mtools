# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `fields`: one field per entry, `_type`, and the empty-population refusal."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.bibparse.edges import DuplicateKeyError
from mikemol.bibparse.fields import EmptyPopulationError, field_values

if TYPE_CHECKING:
    from pathlib import Path

# The entry counts the fixtures below are written to have, named so a test reads its population.
THREE_ENTRIES = 3
TWO_ENTRIES = 2


def _bib(path: Path, text: str) -> Path:
    """Write `text` to `path`.

    Returns:
        `path`.

    """
    path.write_text(text, encoding="utf-8")
    return path


def test_a_field_is_read_only_from_the_entries_that_set_it(tmp_path: Path) -> None:
    """Entries without the field are in the population but not in the values."""
    bib = _bib(
        tmp_path / "w.bib",
        "@misc{a, check = {cmd:one}, claim = {x}}\n"
        "@misc{b, claim = {no check here}}\n"
        "@misc{c, check = {cmd:two}}\n",
    )
    reading = field_values([bib], "check")
    assert reading.values == {"a": "cmd:one", "c": "cmd:two"}
    assert reading.population == THREE_ENTRIES
    assert list(reading.values) == ["a", "c"]


def test_the_entry_type_is_the_type_field_for_every_entry(tmp_path: Path) -> None:
    """`_type` answers what `bibstruct --field _type` answered, for each entry."""
    bib = _bib(tmp_path / "w.bib", "@misc{a, claim = {x}}\n@article{b, claim = {y}}\n")
    reading = field_values([bib], "_type")
    assert reading.values == {"a": "misc", "b": "article"}
    assert reading.population == TWO_ENTRIES


def test_a_field_no_entry_sets_reads_empty_over_a_real_population(tmp_path: Path) -> None:
    """Zero values over two entries is an answer ("none set it"), not a refusal."""
    bib = _bib(tmp_path / "w.bib", "@misc{a, claim = {x}}\n@misc{b, claim = {y}}\n")
    reading = field_values([bib], "check")
    assert reading.values == {}
    assert reading.population == TWO_ENTRIES


def test_no_entries_at_all_is_a_refusal_not_a_clean_file(tmp_path: Path) -> None:
    """A path list that parses to nothing is a broken search."""
    bib = _bib(tmp_path / "w.bib", "% only a comment\n")
    with pytest.raises(EmptyPopulationError, match="path list is wrong"):
        field_values([bib], "check")
    with pytest.raises(EmptyPopulationError):
        field_values([], "check")


def test_the_population_spans_every_given_bib(tmp_path: Path) -> None:
    """Two bibs compose into one population, in the order given."""
    first = _bib(tmp_path / "a.bib", "@misc{a, check = {cmd:one}}\n")
    second = _bib(tmp_path / "b.bib", "@misc{b, check = {cmd:two}}\n@misc{c, claim = {z}}\n")
    reading = field_values([first, second], "check")
    assert reading.values == {"a": "cmd:one", "b": "cmd:two"}
    assert reading.population == THREE_ENTRIES


def test_a_key_defined_twice_is_refused_not_last_wins(tmp_path: Path) -> None:
    """A repeated key would silently replace a claim and its check."""
    first = _bib(tmp_path / "a.bib", "@misc{a, check = {cmd:one}}\n")
    second = _bib(tmp_path / "b.bib", "@misc{a, check = {cmd:other}}\n")
    with pytest.raises(DuplicateKeyError):
        field_values([first, second], "check")

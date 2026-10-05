# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ledger reader: one shape accepted, everything else refused by name."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.debtplan.ledger import LedgerError, parse_ledger, read_ledger

if TYPE_CHECKING:
    from pathlib import Path

BIG = 10**12


def test_a_ledger_of_file_to_count_is_read() -> None:
    """Each file path maps to its count of findings."""
    assert parse_ledger('{"a.py": 2, "b.py": 1}', "ledger") == {"a.py": 2, "b.py": 1}


def test_an_empty_ledger_is_an_empty_plan_not_a_refusal() -> None:
    """An object with no rows is a repository with nothing to pay down."""
    assert parse_ledger("{}", "ledger") == {}


def test_a_large_count_is_kept_exactly() -> None:
    """The count is an integer, not narrowed to a smaller type."""
    assert parse_ledger(f'{{"a.py": {BIG}}}', "ledger") == {"a.py": BIG}


def test_text_that_is_not_json_is_refused_naming_the_source() -> None:
    """The refusal says which ledger and that it is not JSON."""
    with pytest.raises(LedgerError, match=r"mine\.json: not valid JSON"):
        parse_ledger("{not json", "mine.json")


def test_a_json_array_is_refused() -> None:
    """A ledger is an object of rows, and an array is something else."""
    with pytest.raises(LedgerError, match=r"mine\.json: expected a JSON object .*list"):
        parse_ledger('["a.py"]', "mine.json")


@pytest.mark.parametrize("bad", ["0", "-3", "1.5", "true", '"2"', "null"])
def test_a_count_that_is_not_a_positive_integer_is_refused_naming_the_row(bad: str) -> None:
    """Zero, negative, float, boolean, string and null counts name the row they came in."""
    row = r"mine\.json: the row 'a\.py' must be a positive integer"
    with pytest.raises(LedgerError, match=row):
        parse_ledger(f'{{"ok.py": 1, "a.py": {bad}}}', "mine.json")


def test_the_refusal_quotes_the_value_it_refused() -> None:
    """The value is in the message, so the reader sees what was wrong."""
    with pytest.raises(LedgerError, match=r"got 0$"):
        parse_ledger('{"a.py": 0}', "mine.json")


def test_read_ledger_reads_the_file_at_the_path(tmp_path: Path) -> None:
    """The file's text is parsed, and a refusal names the path."""
    good = tmp_path / "good.json"
    good.write_text('{"a.py": 4}', encoding="utf-8")
    assert read_ledger(good) == {"a.py": 4}
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(LedgerError, match=str(bad).replace(".", r"\.")):
        read_ledger(bad)


def test_a_missing_ledger_file_is_an_error_not_an_empty_ledger(tmp_path: Path) -> None:
    """An unreadable ledger must not read as nothing to pay down."""
    with pytest.raises(FileNotFoundError):
        read_ledger(tmp_path / "absent.json")

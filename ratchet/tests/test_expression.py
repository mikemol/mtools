# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A declared ratchet's value is the expression it names, and a table's debt is its columns (W1991).

⚑ THE FIXTURE IS EXACTLY linux-sources' letter-quotes SHAPE: a header and one row per letter with
four 0/1 failure columns, most rows all zero, one with a 1. Its entry count (the rows) stays when a
failure column flips to 0; the expressions must fall.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet import cli, declaration, expression, fleetcensus

if TYPE_CHECKING:
    from pathlib import Path

_HEADER = "letter\tmismatch\tjoined\tunjudged\tfreeform\n"
_COLUMNS = ["mismatch", "joined", "unjudged", "freeform"]
# `rows` is the entry count with a .tsv's HEADER NOT COUNTED (W1992: a header is not an entry, and
# `kinds.value_of` drops it): three data rows under a header read 3.
_ROWS = 3
_TWO_ONES = 2


def _table(path: Path, *rows: str) -> Path:
    path.write_text(_HEADER + "".join(rows), encoding="utf-8")
    return path


def _declare(repo: Path, row: dict[str, object]) -> None:
    body: dict[str, object] = {"ratchets": [row]}
    (repo / declaration.NAME).write_text(json.dumps(body), encoding="utf-8")


def test_a_table_is_counted_by_its_failure_columns_not_its_lines(tmp_path: Path) -> None:
    """Rows stays at the entry count; the two column expressions fall when a 1 becomes 0."""
    before = _table(tmp_path / "a.tsv", "a\t0\t0\t0\t0\n", "b\t0\t0\t1\t0\n", "c\t0\t1\t0\t0\n")
    after = _table(tmp_path / "b.tsv", "a\t0\t0\t0\t0\n", "b\t0\t0\t0\t0\n", "c\t0\t1\t0\t0\n")
    assert expression.evaluate(before, expression.ROWS) == _ROWS
    assert expression.evaluate(after, expression.ROWS) == _ROWS
    assert expression.evaluate(before, expression.SUM_OF_COLUMNS, _COLUMNS) == _TWO_ONES
    assert expression.evaluate(after, expression.SUM_OF_COLUMNS, _COLUMNS) == 1
    assert expression.evaluate(before, expression.ROWS_WHERE_NONZERO, _COLUMNS) == _TWO_ONES
    assert expression.evaluate(after, expression.ROWS_WHERE_NONZERO, _COLUMNS) == 1


def test_sum_and_rows_where_nonzero_differ_when_a_row_has_two_failures(tmp_path: Path) -> None:
    """A row failing two columns is two debts under the sum and one row under the other."""
    path = _table(tmp_path / "t.tsv", "a\t1\t1\t0\t0\n", "b\t0\t0\t0\t0\n")
    assert expression.evaluate(path, expression.SUM_OF_COLUMNS, _COLUMNS) == _TWO_ONES
    assert expression.evaluate(path, expression.ROWS_WHERE_NONZERO, _COLUMNS) == 1


def test_a_name_that_is_not_a_column_or_a_bad_cell_is_refused_loudly(tmp_path: Path) -> None:
    """An unknown column and a non-integer cell raise instead of reading as zero."""
    path = _table(tmp_path / "t.tsv", "a\t0\t0\t0\t0\n")
    with pytest.raises(expression.ExpressionError, match="unjudgd"):
        expression.evaluate(path, expression.SUM_OF_COLUMNS, ["unjudgd"])
    bad = _table(tmp_path / "bad.tsv", "a\tx\t0\t0\t0\n")
    with pytest.raises(expression.ExpressionError, match="not a non-negative integer"):
        expression.evaluate(bad, expression.SUM_OF_COLUMNS, _COLUMNS)
    empty = tmp_path / "empty.tsv"
    empty.write_text("# only a comment\n", encoding="utf-8")
    with pytest.raises(expression.ExpressionError, match="no header"):
        expression.evaluate(empty, expression.ROWS_WHERE_NONZERO, _COLUMNS)


def test_a_file_that_is_missing_is_unread_and_file_rule_count_is_the_sum(tmp_path: Path) -> None:
    """A missing table is None; the ruff-shaped baseline sums its counts."""
    assert expression.evaluate(tmp_path / "gone.tsv", expression.SUM_OF_COLUMNS, _COLUMNS) is None
    ruff = tmp_path / "ruff-baseline.json"
    ruff.write_text('{"a.py": {"E501": 2, "F401": 1}, "b.py": {"E501": 4}}', encoding="utf-8")
    assert expression.evaluate(ruff, expression.FILE_RULE_COUNT) == _TWO_ONES + 1 + 4


@pytest.mark.parametrize(
    "row",
    [
        {"path": "t.tsv", "kind": "baseline", "expression": "average"},
        {"path": "t.tsv", "kind": "baseline", "expression": "sum_of_columns"},
        {"path": "t.tsv", "kind": "baseline", "expression": "sum_of_columns", "columns": []},
        {"path": "t.tsv", "kind": "baseline", "expression": "rows", "columns": ["x"]},
        {"path": "t.tsv", "kind": "baseline", "columns": "x"},
        {"path": "t.tsv", "kind": "baseline", "expression": "rows_where_nonzero", "columns": [1]},
    ],
)
def test_a_declaration_whose_expression_and_columns_do_not_fit_is_refused(
    tmp_path: Path, row: dict[str, object]
) -> None:
    """An unknown expression, columns missing or given where they do not belong, or not names."""
    _declare(tmp_path, row)
    with pytest.raises(declaration.DeclarationError):
        declaration.read(tmp_path)


def test_the_census_uses_the_declared_expression_and_the_command_refuses_a_typo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The census value is the expression's; an unknown column is exit 1 naming the column."""
    _table(tmp_path / "t.tsv", "a\t0\t0\t1\t0\n", "b\t0\t0\t0\t0\n")
    good: dict[str, object] = {
        "path": "t.tsv",
        "kind": "baseline",
        "expression": "sum_of_columns",
        "columns": _COLUMNS,
    }
    _declare(tmp_path, good)
    assert [r.value for r in fleetcensus.census_repo(tmp_path)] == [1]
    _declare(tmp_path, {**good, "columns": ["unjudgd"]})
    assert cli.main(["census", "--repo", str(tmp_path)]) == 1
    assert "unjudgd" in capsys.readouterr().err

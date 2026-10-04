# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `grades_rec`: grade records join the metadata and the clamp reaches the graded."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.gradekit.cli import USAGE_STATUS, UsageError
from mikemol.gradekit.grades_rec import (
    base_row,
    grade_row,
    main,
    run,
    table,
    target_key,
    ungraded_row,
)
from mikemol.gradekit.jsonio import RecordError, as_list, as_record, check_json

if TYPE_CHECKING:
    from mikemol.grade.grade import Json, Record

META: list[Record] = [
    {"key": "a", "check": "cmd:x", "section": "S1", "rests-on": ["b"], "tier": "witness"},
    {"key": "b", "check": "cmd:x", "section": "S1", "rests-on": [], "tier": "witness"},
    {"key": "c", "check": "cmd:y", "section": "S2", "rests-on": [], "tier": "local"},
    {"key": "d", "check": "cmd:z", "section": "S2", "rests-on": ["c"], "tier": "witness"},
]
RECS: dict[str, Record] = {
    "a": {"claim": "a", "grade": "behavioral", "tests": ["t"], "why": "w", "baseline": "est"},
    "b": {"claim": "b", "grade": "vacuous"},
    "d": {"claim": "d", "grade": "behavioral"},
}


def _by_key(rows: list[Record]) -> dict[str, Record]:
    """Index table rows by key.

    Returns:
        The rows by their key.

    """
    return {str(row["key"]): row for row in rows}


def _parsed(text: str) -> list[Json]:
    """Parse one printed JSON list.

    Returns:
        The list, typed.

    """
    loaded: object = json.loads(text)
    return as_list(check_json(loaded, "out"), "out")


def test_target_key_is_the_file_name_before_the_grade_marker() -> None:
    """The key comes from the file name, not from anything inside the record."""
    assert target_key(Path("/x/key-graded__grade.grade.json")) == "key-graded"
    assert target_key(Path("/x/plain.json")) == "plain.json"


def test_base_row_keeps_exactly_the_four_descriptive_fields_in_order() -> None:
    """A row starts as key, check, section and rests-on, whatever else the metadata holds."""
    row = base_row(META[0], "m")
    assert list(row) == ["key", "check", "section", "rests-on"]
    assert row == {"key": "a", "check": "cmd:x", "section": "S1", "rests-on": ["b"]}
    with pytest.raises(RecordError, match="m: missing the field 'section'"):
        base_row({"key": "a", "check": "c", "rests-on": []}, "m")


def test_grade_row_adds_the_reading_with_empty_defaults() -> None:
    """The grade and justification join the row; a record without them reads as empty."""
    base: Record = {"key": "a"}
    full = grade_row(base, RECS["a"])
    assert full == {
        "key": "a",
        "grade": "behavioral",
        "tests": ["t"],
        "baseline": "est",
        "why": "w",
        "not_higher": "",
        "not_lower": "",
    }
    sparse = grade_row(base, {"grade": "vacuous"})
    assert sparse["tests"] == []
    assert (sparse["baseline"], sparse["why"]) == ("", "")
    assert base == {"key": "a"}
    with pytest.raises(RecordError, match="grade record: missing the field 'grade'"):
        grade_row(base, {})


def test_ungraded_row_says_why_in_terms_of_the_tier() -> None:
    """A row with no grade record is not graded, and the reason names its tier."""
    row = ungraded_row({"key": "c"}, "local")
    assert row == {
        "key": "c",
        "grade": "not graded",
        "why": "gated, not Δ-graded (no grade record; local tier)",
        "not_higher": "",
        "not_lower": "",
    }


def test_table_clamps_graded_claims_by_what_they_rest_on() -> None:
    """A behavioral claim resting on a vacuous one is clamped to vacuous and names it."""
    rows = _by_key(table(META, RECS))
    assert list(rows) == ["a", "b", "c", "d"]
    assert rows["a"]["grade"] == "behavioral"
    assert rows["a"]["effective_grade"] == "vacuous"
    assert rows["a"]["clamped_by"] == "b"
    assert rows["b"]["effective_grade"] == "vacuous"
    assert rows["b"]["clamped_by"] is None


def test_table_keeps_ungraded_claims_out_of_the_clamp_and_marks_them() -> None:
    """An ungraded claim has no effective grade, and an edge to it is an unresolved one."""
    rows = _by_key(table(META, RECS))
    assert rows["c"]["grade"] == "not graded"
    assert "effective_grade" not in rows["c"]
    assert rows["d"]["effective_grade"] == "behavioral"
    assert rows["d"]["unresolved"] == ["c"]
    assert rows["d"]["resolution"] == "truncated"


def test_table_lists_the_other_claims_sharing_a_check() -> None:
    """Claims with the same check name each other and never themselves."""
    rows = _by_key(table(META, RECS))
    assert rows["a"]["shared_with"] == ["b"]
    assert rows["b"]["shared_with"] == ["a"]
    assert rows["c"]["shared_with"] == []
    assert rows["d"]["shared_with"] == []


def test_table_reads_the_tier_of_an_ungraded_claim_only() -> None:
    """The tier is read for an ungraded claim only, as the original did."""
    graded_without_tier: Record = {"key": "a", "check": "c", "section": "s", "rests-on": []}
    assert table([graded_without_tier], {"a": {"grade": "vacuous"}})[0]["key"] == "a"
    with pytest.raises(RecordError, match=r"meta\[0\]: missing the field 'tier'"):
        table([graded_without_tier], {})


def _write(tmp_path: Path, name: str, value: Json) -> str:
    """Write a JSON file.

    Returns:
        The path as text.

    """
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return str(path)


def _files(tmp_path: Path) -> list[str]:
    """Write the metadata and the grade files of the shared scenario.

    Returns:
        The words for the command line.

    """
    words = [_write(tmp_path, "meta.json", [*META])]
    words.extend(_write(tmp_path, f"{key}__grade.grade.json", rec) for key, rec in RECS.items())
    return words


def test_run_keys_records_by_file_name_and_prints_one_json_line(tmp_path: Path) -> None:
    """The records are matched to the metadata by their file names."""
    text = run(_files(tmp_path))
    assert text.count("\n") == 1
    rows = [as_record(row, "row") for row in _parsed(text)]
    assert [row["key"] for row in rows] == ["a", "b", "c", "d"]
    assert rows[0]["effective_grade"] == "vacuous"
    assert rows[2]["grade"] == "not graded"


def test_run_with_only_the_metadata_grades_nothing(tmp_path: Path) -> None:
    """No grade file at all leaves every claim not graded."""
    rows = [as_record(row, "row") for row in _parsed(run(_files(tmp_path)[:1]))]
    assert [row["grade"] for row in rows] == ["not graded"] * 4


def test_run_wants_a_metadata_file_and_a_list_in_it(tmp_path: Path) -> None:
    """No arguments is a usage error and a metadata file that is not a list is refused."""
    with pytest.raises(UsageError, match="usage: mikemol-grades-rec"):
        run([])
    with pytest.raises(RecordError, match="expected a list, got dict"):
        run([_write(tmp_path, "m.json", {})])


def test_main_prints_the_table_and_reports_failures_as_status_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A good run prints the table; a usage error and a missing file each end in one line."""
    assert main(_files(tmp_path)) == 0
    captured = capsys.readouterr()
    assert (captured.err, len(_parsed(captured.out))) == ("", len(META))
    assert main([]) == USAGE_STATUS
    assert main([str(tmp_path / "absent.json")]) == USAGE_STATUS
    errors = capsys.readouterr().err.splitlines()
    assert [line.startswith("mikemol-grades-rec: ") for line in errors] == [True, True]


def test_main_without_arguments_reads_sys_argv_and_the_guard_exits_with_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no argv given main reads sys.argv; running the module as a script exits 0."""
    monkeypatch.setattr(sys, "argv", ["prog", *_files(tmp_path)])
    assert main() == 0
    assert len(_parsed(capsys.readouterr().out)) == len(META)
    monkeypatch.delitem(sys.modules, "mikemol.gradekit.grades_rec")
    with pytest.raises(SystemExit) as exited:
        cast("object", runpy.run_module("mikemol.gradekit.grades_rec", run_name="__main__"))
    assert exited.value.code == 0
    assert len(_parsed(capsys.readouterr().out)) == len(META)

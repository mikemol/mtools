# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `read_grade`: a calculation record becomes a grade with its whole justification."""

from __future__ import annotations

import json
import runpy
import sys
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.gradekit.cli import USAGE_STATUS, UsageError
from mikemol.gradekit.jsonio import RecordError, as_record, check_json
from mikemol.gradekit.read_grade import main, reading, run

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.grade.grade import Record


def _calc(tmp_path: Path, record: Record) -> str:
    """Write a calculation record to a file.

    Returns:
        The path as text.

    """
    path = tmp_path / "c.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return str(path)


def _parsed(text: str) -> Record:
    """Parse one printed JSON object.

    Returns:
        The object, typed.

    """
    loaded: object = json.loads(text)
    return as_record(check_json(loaded, "out"), "out")


def test_a_flipped_baseline_reads_behavioral_and_carries_every_justification() -> None:
    """The rung, the flipping tests, the baseline word and the reasons all travel."""
    got = reading({"claim": "k", "baseline": True, "sens": ["t1", "t2"]}, "w")
    assert list(got) == ["claim", "grade", "tests", "baseline", "why", "not_higher", "not_lower"]
    assert (got["claim"], got["grade"], got["tests"], got["baseline"]) == (
        "k",
        "behavioral",
        ["t1", "t2"],
        "established",
    )
    assert got["why"] == "falsifiable — corrupting 2 input(s) flips it red"
    assert "top tier" in str(got["not_higher"])
    assert "sensitive to 2 input(s)" in str(got["not_lower"])


def test_a_baseline_that_holds_with_no_flip_reads_indeterminate_with_empty_baseline() -> None:
    """The indeterminate branch has no baseline word, so it reads as empty text."""
    got = reading({"claim": "k", "baseline": 1, "sens": []}, "w")
    assert (got["grade"], got["tests"], got["baseline"]) == ("indeterminate", [], "")
    assert "counter-fixture" in str(got["why"])
    assert "counter-fixture" in str(got["not_higher"])
    assert "not provably vacuous" in str(got["not_lower"])


def test_a_failed_baseline_reads_broken_refuted_unless_it_was_unreachable() -> None:
    """The reachable field turns a refuted baseline into an unreachable one."""
    refuted = reading({"claim": "k", "baseline": False, "sens": []}, "w")
    assert (refuted["grade"], refuted["baseline"]) == ("broken", "refuted")
    assert "repo is not green" in str(refuted["why"])
    unreachable = reading({"claim": "k", "baseline": 0, "sens": [], "reachable": False}, "w")
    assert (unreachable["grade"], unreachable["baseline"]) == ("broken", "unreachable")
    assert "could not be REACHED" in str(unreachable["why"])
    reachable = reading({"claim": "k", "baseline": 0, "sens": [], "reachable": True}, "w")
    assert reachable["baseline"] == "refuted"


def test_a_record_missing_a_field_is_refused_by_name() -> None:
    """Each of claim, baseline and sens is required and named when absent."""
    for missing in ("claim", "baseline", "sens"):
        record: Record = {"claim": "k", "baseline": True, "sens": []}
        del record[missing]
        with pytest.raises(RecordError, match=f"missing the field '{missing}'"):
            reading(record, "w")
    with pytest.raises(RecordError, match=r"w\.sens: expected a list, got str"):
        reading({"claim": "k", "baseline": True, "sens": "x"}, "w")


def test_run_renders_one_line_of_default_spaced_json(tmp_path: Path) -> None:
    """The output is the record as one JSON line with the default separators."""
    path = _calc(tmp_path, {"claim": "k", "baseline": True, "sens": ["t"]})
    text = run([path])
    assert text.endswith("\n")
    assert text.count("\n") == 1
    assert text.startswith('{"claim": "k", "grade": "behavioral", "tests": ["t"]')


def test_run_wants_exactly_one_path(tmp_path: Path) -> None:
    """No path and two paths are both usage errors."""
    path = _calc(tmp_path, {"claim": "k", "baseline": True, "sens": []})
    with pytest.raises(UsageError, match="usage: mikemol-read-grade"):
        run([])
    with pytest.raises(UsageError, match="usage: mikemol-read-grade"):
        run([path, path])


def test_main_prints_the_record_and_returns_zero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A good file prints its grade record to standard output."""
    path = _calc(tmp_path, {"claim": "k", "baseline": True, "sens": ["t"]})
    status = main([path])
    captured = capsys.readouterr()
    assert (status, captured.err) == (0, "")
    assert _parsed(captured.out)["grade"] == "behavioral"


def test_main_reports_each_expected_failure_as_one_line_and_status_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A usage error, a missing file and a bad record each end in one line and status 2."""
    statuses = [
        main([]),
        main([str(tmp_path / "absent.json")]),
        main([_calc(tmp_path, {"claim": "k"})]),
    ]
    errors = capsys.readouterr().err.splitlines()
    assert statuses == [USAGE_STATUS] * 3
    assert [line.startswith("mikemol-read-grade: ") for line in errors] == [True] * 3
    assert "missing the field 'baseline'" in errors[2]


def test_main_without_arguments_reads_the_process_arguments_and_the_module_guard_runs_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no argv given, main reads sys.argv; running the module as a script exits with it."""
    path = _calc(tmp_path, {"claim": "k", "baseline": True, "sens": []})
    monkeypatch.setattr(sys, "argv", ["prog", path])
    assert main() == 0
    assert _parsed(capsys.readouterr().out)["grade"] == "indeterminate"
    monkeypatch.delitem(sys.modules, "mikemol.gradekit.read_grade")
    with pytest.raises(SystemExit) as exited:
        cast("object", runpy.run_module("mikemol.gradekit.read_grade", run_name="__main__"))
    assert exited.value.code == 0
    assert _parsed(capsys.readouterr().out)["claim"] == "k"

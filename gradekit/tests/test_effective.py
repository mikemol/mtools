# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `effective`: bib edges join grade files, and the clamp honours owner grades."""

from __future__ import annotations

import json
import runpy
import sys
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.gradekit.cli import USAGE_STATUS, UsageError
from mikemol.gradekit.effective import (
    COLUMNS,
    delegation,
    key_of,
    main,
    owner_grades,
    records,
    run,
    split_owners,
)
from mikemol.gradekit.jsonio import RecordError, as_list, as_record, check_json

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.grade.grade import Json, Record

BIB = """\
@misc{top,
  claim = {top claim},
  rests-on = {base, mid},
  check = {cmd:true},
}
@misc{base, claim = {base claim}, check = {cmd:true}}
@misc{mid, claim = {mid}, rests-on = {base}, check = {concept:lib-claim}}
@misc{far, claim = {far}, check = {result:other#their-claim}}
"""


def _project(root: Path, bib: str = BIB) -> Path:
    """Create a project directory holding a paper.toml and one bib.

    Returns:
        The project directory.

    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "paper.toml").write_text('[paper]\nwarrants = ["warrants.bib"]\n', encoding="utf-8")
    (root / "warrants.bib").write_text(bib, encoding="utf-8")
    return root


def _write(path: Path, value: Json) -> str:
    """Write a JSON file.

    Returns:
        The path as text.

    """
    path.write_text(json.dumps(value), encoding="utf-8")
    return str(path)


def _grades(tmp_path: Path, grades: dict[str, str]) -> list[str]:
    """Write one grade file per claim.

    Returns:
        The file paths, in claim order.

    """
    return [
        _write(tmp_path / f"{key}.json", {"claim": key, "grade": grade})
        for key, grade in grades.items()
    ]


def _parsed(text: str) -> Record:
    """Parse the printed report.

    Returns:
        The report object, typed.

    """
    loaded: object = json.loads(text)
    return as_record(check_json(loaded, "out"), "out")


def _claims(report: Record) -> dict[str, Record]:
    """Index a report's claims by key.

    Returns:
        The claim rows by key.

    """
    rows = [as_record(row, "claim") for row in as_list(report["claims"], "claims")]
    return {str(row["key"]): row for row in rows}


def test_delegation_reads_the_edge_a_crossing_check_names() -> None:
    """A concept check delegates to the library, a result check to a project and claim."""
    assert delegation("concept:lib-claim") == {
        "owner": "library",
        "claim": "lib-claim",
        "verb": "concept",
    }
    assert delegation("result:proj#claim") == {"owner": "proj", "claim": "claim", "verb": "result"}
    assert delegation("result:proj") == {"owner": "proj", "claim": None, "verb": "result"}
    assert delegation("cmd:true") is None
    assert delegation("") is None


def test_records_join_grade_files_to_the_edges_of_the_bibs(tmp_path: Path) -> None:
    """Rests-on and delegations come from the bib; the grade comes from the file."""
    project = _project(tmp_path / "p")
    files = _grades(tmp_path, {"top": "behavioral", "mid": "existence", "far": "imported"})
    got = {str(r["key"]): r for r in records(project, files)}
    assert got["top"] == {"key": "top", "grade": "behavioral", "rests-on": ["base", "mid"]}
    assert got["mid"]["rests-on"] == ["base"]
    assert got["mid"]["delegates_to"] == {
        "owner": "library",
        "claim": "lib-claim",
        "verb": "concept",
    }
    assert got["far"]["delegates_to"] == {
        "owner": "other",
        "claim": "their-claim",
        "verb": "result",
    }


def test_records_keep_a_claim_the_bibs_do_not_name_resting_on_nothing(tmp_path: Path) -> None:
    """A grade file for an unknown claim is kept, with no edges and no delegation."""
    project = _project(tmp_path / "p")
    got = records(project, _grades(tmp_path, {"ghost": "vacuous"}))
    assert got == [{"key": "ghost", "grade": "vacuous", "rests-on": []}]


def test_owner_grades_carry_the_pair_and_what_clamped_it(tmp_path: Path) -> None:
    """Both the self grade and the effective grade cross, with the clamp's name."""
    pinned: Record = {
        "key": "x",
        "grade": "behavioral",
        "effective_grade": "vacuous",
        "clamped_by": "y",
    }
    plain: Record = {"key": "z", "grade": "existence", "effective_grade": "existence"}
    owner = _write(tmp_path / "lib.json", {"claims": [pinned, plain]})
    other = _write(
        tmp_path / "o.json",
        {"claims": [{"key": "x", "grade": "imported", "effective_grade": "imported"}]},
    )
    got = owner_grades([f"library={owner}", f"other={other}"])
    assert got["library", "x"] == {
        "grade": "behavioral",
        "effective_grade": "vacuous",
        "clamped_by": "y",
    }
    assert got["library", "z"] == {
        "grade": "existence",
        "effective_grade": "existence",
        "clamped_by": None,
    }
    assert got["other", "x"] == {
        "grade": "imported",
        "effective_grade": "imported",
        "clamped_by": None,
    }
    assert sorted(got) == [("library", "x"), ("library", "z"), ("other", "x")]


def test_owner_grades_refuse_a_spec_without_an_equals_sign_and_a_bad_file(tmp_path: Path) -> None:
    """A spec must be project=file, and its file must hold a claims list of full rows."""
    with pytest.raises(UsageError, match=r"owner spec 'nofile' is not <project>=<file>"):
        owner_grades(["nofile"])
    assert owner_grades([]) == {}
    bad = _write(tmp_path / "bad.json", {"claims": [{"key": "x", "grade": "vacuous"}]})
    with pytest.raises(RecordError, match="missing the field 'effective_grade'"):
        owner_grades([f"p={bad}"])
    with pytest.raises(RecordError, match="missing the field 'claims'"):
        owner_grades([f"p={_write(tmp_path / 'e.json', {})}"])


def test_split_owners_cuts_at_the_first_option() -> None:
    """Words before the option stay; everything after it is a spec."""
    assert split_owners(["p", "g1", "--owners", "a=b", "c=d"]) == (["p", "g1"], ["a=b", "c=d"])
    assert split_owners(["p", "g1"]) == (["p", "g1"], [])
    assert split_owners(["--owners"]) == ([], [])
    assert split_owners(["p", "--owners", "--owners", "x"]) == (["p"], ["--owners", "x"])


def test_key_of_reads_the_key_and_the_columns_are_the_documented_seven() -> None:
    """The sort key is the record's key; the report prints seven named columns."""
    assert key_of({"key": "k", "grade": "vacuous"}) == "k"
    assert COLUMNS == (
        "key",
        "grade",
        "effective_grade",
        "clamp",
        "clamped_by",
        "clamp_path",
        "unresolved",
    )


def test_run_clamps_each_claim_by_what_it_rests_on(tmp_path: Path) -> None:
    """The weakest premise along rests-on pins the claim and is named."""
    project = _project(tmp_path / "proj")
    files = _grades(tmp_path, {"top": "behavioral", "base": "vacuous", "mid": "behavioral"})
    text = run([str(project), *files])
    report = _parsed(text)
    assert report["project"] == "proj"
    assert text == json.dumps(report, indent=2) + "\n"
    claims = _claims(report)
    assert list(claims) == ["base", "mid", "top"]
    assert list(claims["top"]) == list(COLUMNS)
    assert claims["top"]["grade"] == "behavioral"
    assert claims["top"]["effective_grade"] == "vacuous"
    assert claims["top"]["clamped_by"] == "base"
    assert claims["base"]["clamp"] == 0
    rungs_dropped = 3  # behavioral to vacuous, by the ladder's ranks 3 and 0
    assert claims["top"]["clamp"] == rungs_dropped
    assert claims["top"]["unresolved"] == []


def test_run_clamps_a_delegating_claim_by_the_owners_effective_grade(tmp_path: Path) -> None:
    """The owner's effective grade is the bound, not its self grade."""
    project = _project(tmp_path / "proj")
    files = _grades(tmp_path, {"mid": "behavioral", "base": "behavioral"})
    owner = _write(
        tmp_path / "lib.json",
        {"claims": [{"key": "lib-claim", "grade": "behavioral", "effective_grade": "existence"}]},
    )
    without = _claims(_parsed(run([str(project), *files])))
    with_owner = _claims(_parsed(run([str(project), *files, "--owners", f"library={owner}"])))
    assert without["mid"]["effective_grade"] == "behavioral"
    assert with_owner["mid"]["effective_grade"] == "existence"
    assert with_owner["mid"]["clamp"] == 1


def test_run_names_the_current_directory_when_the_project_has_no_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A project named by a bare dot reports that dot as its name."""
    project = _project(tmp_path / "proj")
    grade_files = _grades(tmp_path, {"base": "vacuous"})
    monkeypatch.chdir(project)
    assert _parsed(run([".", *grade_files]))["project"] == "."


def test_run_wants_a_project_directory(tmp_path: Path) -> None:
    """No arguments, and only owner specs, are both usage errors."""
    with pytest.raises(UsageError, match="usage: mikemol-effective"):
        run([])
    with pytest.raises(UsageError, match="usage: mikemol-effective"):
        run(["--owners", f"p={tmp_path}/x"])


def test_main_prints_the_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A good run prints the report to standard output and nothing to standard error."""
    project = _project(tmp_path / "proj")
    status = main([str(project), *_grades(tmp_path, {"base": "vacuous"})])
    captured = capsys.readouterr()
    assert (status, captured.err) == (0, "")
    assert list(_claims(_parsed(captured.out))) == ["base"]


def test_main_reports_the_bibparse_failures_and_bad_input_as_status_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each exception class from the bib layer ends in one named line, not a traceback."""
    grade_files = _grades(tmp_path, {"base": "vacuous"})
    no_toml = tmp_path / "empty"
    no_toml.mkdir()
    twice = _project(tmp_path / "twice", "@misc{base, claim = {a}}\n@misc{base, claim = {b}}\n")
    broken = _project(tmp_path / "broken", "@misc{base, claim = {unterminated\n")
    good = _project(tmp_path / "good")
    cases = [
        [str(no_toml), *grade_files],
        [str(twice), *grade_files],
        [str(broken), *grade_files],
        [str(good), str(tmp_path / "absent.json")],
        [str(good), _write(tmp_path / "noclaim.json", {"grade": "x"})],
        [],
    ]
    statuses = [main(words) for words in cases]
    lines = capsys.readouterr().err.splitlines()
    errors = [line for line in lines if line.startswith("mikemol-effective: ")]
    assert statuses == [USAGE_STATUS] * len(cases)
    assert len(errors) == len(cases)
    assert "no paper.toml" in errors[0]
    assert "defined TWICE" in errors[1]
    assert "warrants.bib" in errors[2]
    assert "absent.json" in errors[3]
    assert "missing the field 'claim'" in errors[4]


def test_main_without_arguments_reads_sys_argv_and_the_guard_exits_with_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no argv given main reads sys.argv; running the module as a script exits 0."""
    project = _project(tmp_path / "proj")
    words = [str(project), *_grades(tmp_path, {"base": "vacuous"})]
    monkeypatch.setattr(sys, "argv", ["prog", *words])
    assert main() == 0
    assert list(_claims(_parsed(capsys.readouterr().out))) == ["base"]
    monkeypatch.delitem(sys.modules, "mikemol.gradekit.effective")
    with pytest.raises(SystemExit) as exited:
        cast("object", runpy.run_module("mikemol.gradekit.effective", run_name="__main__"))
    assert exited.value.code == 0
    assert list(_claims(_parsed(capsys.readouterr().out))) == ["base"]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `verdict`: a compact record is written atomically; aggregates name offenders."""

from __future__ import annotations

import json
import runpy
import sys
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.gradekit.cli import USAGE_STATUS, UsageError
from mikemol.gradekit.jsonio import RecordError, as_record, read_json
from mikemol.gradekit.verdict import (
    VerdictError,
    account_tail,
    bad_set,
    cohere_word,
    dispatch,
    field_value,
    main,
    verdict_word,
    write_record,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.grade.grade import Json, Record

FAKE_COHERENCE = """\
import sys

sys.stderr.write("argv: " + " ".join(sys.argv[1:]) + "\\n")
sys.stderr.write("the residual\\n")
raise SystemExit(int(sys.argv[-1].rsplit("rc", 1)[-1]))
"""


def _json(path: Path, value: Json) -> str:
    """Write a JSON file.

    Returns:
        The path as text.

    """
    path.write_text(json.dumps(value), encoding="utf-8")
    return str(path)


def _rec(path: Path) -> Record:
    """Read a written record back.

    Returns:
        The record, typed.

    """
    return as_record(read_json(path), str(path))


def test_verdict_word_names_a_boolean() -> None:
    """True is pass and False is fail."""
    assert [verdict_word(ok=True), verdict_word(ok=False)] == ["pass", "fail"]


def test_account_tail_keeps_the_last_forty_non_blank_lines(tmp_path: Path) -> None:
    """Blank lines are dropped and only the last forty remain, in order."""
    path = tmp_path / "err.txt"
    path.write_text("\n".join(f"line {n}\n" for n in range(50)) + "   \n", encoding="utf-8")
    tail = account_tail(path)
    assert tail == [f"line {n}" for n in range(10, 50)]


def test_account_tail_of_a_missing_file_is_empty(tmp_path: Path) -> None:
    """An unreadable account file contributes nothing and is not an error."""
    assert account_tail(tmp_path / "absent.txt") == []


def test_write_record_is_compact_and_ends_in_a_newline(tmp_path: Path) -> None:
    """The bytes are the record with no spaces after separators, then one newline."""
    out = tmp_path / "v.json"
    write_record(out, "gate", "pass")
    assert out.read_text(encoding="utf-8") == '{"verb":"gate","verdict":"pass"}\n'


def test_write_record_carries_a_reason_only_when_there_is_one(tmp_path: Path) -> None:
    """A reason is the third key; an empty one is absent."""
    out = tmp_path / "v.json"
    write_record(out, "gate", "fail", "because")
    assert out.read_text(encoding="utf-8") == '{"verb":"gate","verdict":"fail","why":"because"}\n'


def test_write_record_folds_the_error_tail_in_on_a_non_pass_only(tmp_path: Path) -> None:
    """A failing record carries the account lines; a passing one never does."""
    err = tmp_path / "err.txt"
    err.write_text("first\n\nsecond\n", encoding="utf-8")
    failing = tmp_path / "f.json"
    passing = tmp_path / "p.json"
    write_record(failing, "cmd", "fail", account=err)
    write_record(passing, "cmd", "pass", account=err)
    assert _rec(failing)["account"] == ["first", "second"]
    assert "account" not in _rec(passing)


def test_write_record_omits_the_account_when_there_is_nothing_to_fold(tmp_path: Path) -> None:
    """An empty or unreadable account file leaves no account key."""
    empty = tmp_path / "empty.txt"
    empty.write_text("\n", encoding="utf-8")
    out = tmp_path / "v.json"
    write_record(out, "cmd", "fail", account=empty)
    assert "account" not in _rec(out)
    write_record(out, "cmd", "fail", account=tmp_path / "absent.txt")
    assert "account" not in _rec(out)
    write_record(out, "cmd", "fail", account=None)
    assert _rec(out) == {"verb": "cmd", "verdict": "fail"}


def test_bad_set_is_a_lower_cased_comma_list() -> None:
    """A literal list names the failing values, compared lower-cased."""
    assert bad_set("Fail,VACUOUS") == {"fail", "vacuous"}
    assert bad_set("fail") == {"fail"}


def test_bad_set_below_a_floor_is_derived_from_the_ladder() -> None:
    """The grades under the floor fail it; the floor itself and above do not."""
    assert bad_set("below:behavioral") == {"broken", "vacuous", "indeterminate", "existence"}
    assert bad_set("below:vacuous") == {"broken"}


def test_bad_set_refuses_a_floor_that_is_not_a_rung() -> None:
    """A typo in the floor must not grade everything green."""
    with pytest.raises(VerdictError, match="'bahavioral' is not a rung of the grade ladder"):
        bad_set("below:bahavioral")


def test_field_value_is_the_lower_cased_text_of_the_field(tmp_path: Path) -> None:
    """Strings are lower-cased, booleans read as their JSON-ish words, absent is none."""
    path = tmp_path / "r.json"
    path.write_text('{"verdict": "FAIL", "ok": true, "n": 3}', encoding="utf-8")
    assert field_value(path, "verdict") == "fail"
    assert field_value(path, "ok") == "true"
    assert field_value(path, "n") == "3"
    assert field_value(path, "absent") == "none"


def test_field_value_refuses_a_record_that_is_not_an_object(tmp_path: Path) -> None:
    """A list is not a record and the refusal names the file."""
    path = tmp_path / "r.json"
    path.write_text("[1]", encoding="utf-8")
    with pytest.raises(RecordError, match=r"r\.json: expected an object"):
        field_value(path, "verdict")


def test_cohere_word_keeps_cannot_run_apart_from_fail() -> None:
    """Zero passes, two cannot run, anything else fails."""
    assert [cohere_word(code) for code in (0, 1, 2, 3, 127)] == [
        "pass",
        "fail",
        "cannot-run",
        "fail",
        "fail",
    ]


def test_emit_records_the_three_verdict_words_and_fails_closed_on_any_other(
    tmp_path: Path,
) -> None:
    """The caller's word is recorded verbatim when valid; anything else is a fail."""
    out = tmp_path / "v.json"
    for word in ("pass", "fail", "cannot-run"):
        dispatch(["emit", "cmd", word, str(out)])
        assert _rec(out) == {"verb": "cmd", "verdict": word}
    dispatch(["emit", "cmd", "bogus", str(out)])
    assert _rec(out)["verdict"] == "fail"


def test_emit_folds_in_the_account_file_named_last(tmp_path: Path) -> None:
    """The check's own error tail rides a failing record; the last --account wins."""
    first = tmp_path / "a.txt"
    last = tmp_path / "b.txt"
    first.write_text("from a\n", encoding="utf-8")
    last.write_text("from b\n", encoding="utf-8")
    out = tmp_path / "v.json"
    dispatch(["emit", "cmd", "fail", str(out), "--account", str(first), "--account", str(last)])
    assert _rec(out)["account"] == ["from b"]
    dispatch(["emit", "cmd", "pass", str(out), "--account", str(last)])
    assert "account" not in _rec(out)


def test_exists_passes_iff_the_path_is_present(tmp_path: Path) -> None:
    """A present path passes and an absent one fails."""
    out = tmp_path / "v.json"
    dispatch(["exists", "file", str(tmp_path), str(out)])
    assert _rec(out) == {"verb": "file", "verdict": "pass"}
    dispatch(["exists", "file", str(tmp_path / "absent"), str(out)])
    assert _rec(out) == {"verb": "file", "verdict": "fail"}


def test_agg_passes_when_no_record_has_the_bad_value(tmp_path: Path) -> None:
    """Every record clear of the bad set passes, with no reason."""
    ok1 = _json(tmp_path / "a.json", {"verdict": "pass"})
    ok2 = _json(tmp_path / "b.json", {"verdict": "cannot-run"})
    out = tmp_path / "v.json"
    dispatch(["agg", "gate", str(out), "verdict", "fail", ok1, ok2])
    assert _rec(out) == {"verb": "gate", "verdict": "pass"}


def test_agg_names_every_offender_in_the_record(tmp_path: Path) -> None:
    """A failing aggregate lists each offending record by file name and value."""
    ok = _json(tmp_path / "ok.json", {"verdict": "pass"})
    bad1 = _json(tmp_path / "bad1.json", {"verdict": "fail"})
    bad2 = _json(tmp_path / "bad2.json", {"verdict": "FAIL"})
    out = tmp_path / "v.json"
    dispatch(["agg", "gate", str(out), "verdict", "fail", ok, bad1, bad2])
    assert _rec(out) == {
        "verb": "gate",
        "verdict": "fail",
        "why": "bad1.json=fail; bad2.json=fail",
    }


def test_agg_caps_the_reason_at_four_hundred_characters(tmp_path: Path) -> None:
    """A record is a verdict, not a transcript."""
    names = [_json(tmp_path / f"{'x' * 30}{n}.json", {"verdict": "fail"}) for n in range(30)]
    out = tmp_path / "v.json"
    dispatch(["agg", "gate", str(out), "verdict", "fail", *names])
    why = _rec(out)["why"]
    assert isinstance(why, str)
    limit = 400
    assert len(why) == limit


def test_agg_with_no_records_passes_and_a_floor_aggregates_over_the_ladder(tmp_path: Path) -> None:
    """No records cannot offend; a below-floor aggregate fails a record under the floor."""
    out = tmp_path / "v.json"
    dispatch(["agg", "gate", str(out), "verdict", "fail"])
    assert _rec(out)["verdict"] == "pass"
    weak = _json(tmp_path / "weak.json", {"grade": "vacuous"})
    strong = _json(tmp_path / "strong.json", {"grade": "behavioral"})
    dispatch(["agg", "adequacy", str(out), "grade", "below:behavioral", strong])
    assert _rec(out)["verdict"] == "pass"
    dispatch(["agg", "adequacy", str(out), "grade", "below:behavioral", strong, weak])
    assert _rec(out) == {"verb": "adequacy", "verdict": "fail", "why": "weak.json=vacuous"}


def test_agg_refuses_a_floor_that_is_not_a_rung(tmp_path: Path) -> None:
    """The refusal comes before any record is judged green."""
    rec = _json(tmp_path / "r.json", {"grade": "vacuous"})
    with pytest.raises(VerdictError, match="not a rung"):
        dispatch(["agg", "adequacy", str(tmp_path / "v.json"), "grade", "below:nope", rec])
    assert not (tmp_path / "v.json").exists()


def test_agree_passes_only_for_two_or_more_equal_outputs_none_failed(tmp_path: Path) -> None:
    """Byte-equal whole documents agree; one output, differing outputs and a failure do not."""
    same1 = tmp_path / "s1.txt"
    same2 = tmp_path / "s2.txt"
    diff = tmp_path / "d.txt"
    failed1 = tmp_path / "f1.txt"
    failed2 = tmp_path / "f2.txt"
    same1.write_text("a\nb\n", encoding="utf-8")
    same2.write_text("a\nb\n", encoding="utf-8")
    diff.write_text("a\nc\n", encoding="utf-8")
    failed1.write_text("x __FAIL__ x", encoding="utf-8")
    failed2.write_text("x __FAIL__ x", encoding="utf-8")
    out = tmp_path / "v.json"
    verdicts = []
    for produced in ([same1, same2], [same1], [same1, diff], [failed1, failed2], []):
        dispatch(["agree", "agree", str(out), *map(str, produced)])
        verdicts.append(_rec(out)["verdict"])
    assert verdicts == ["pass", "fail", "fail", "fail", "fail"]
    dispatch(["agree", "agree", str(out), str(same1), str(same2), str(same1)])
    assert _rec(out)["verdict"] == "pass"


def test_calc_passes_iff_the_baseline_holds(tmp_path: Path) -> None:
    """A truthy baseline passes; a false or absent one fails."""
    out = tmp_path / "v.json"
    got = []
    calcs: list[Record] = [
        {"baseline": True},
        {"baseline": 1},
        {"baseline": False},
        {"baseline": 0},
        {},
    ]
    for calc in calcs:
        dispatch(["calc", "pk", _json(tmp_path / "c.json", calc), str(out)])
        got.append(_rec(out)["verdict"])
    assert got == ["pass", "pass", "fail", "fail", "fail"]


def test_canary_passes_only_when_the_flip_flipped_and_the_identity_did_not(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Both directions are asserted, and a degraded harness is named on standard error."""
    out = tmp_path / "v.json"
    cases = [(True, False), (False, False), (True, True), (False, True)]
    got = []
    for pos, nul in cases:
        dispatch(
            [
                "canary",
                _json(tmp_path / "pos.json", {"flipped": pos}),
                _json(tmp_path / "nul.json", {"flipped": nul}),
                str(out),
            ],
        )
        got.append(_rec(out))
    assert got == [
        {"verb": "canary", "verdict": verdict} for verdict in ("pass", "fail", "fail", "fail")
    ]
    err = capsys.readouterr().err
    assert err.count("HARNESS DEGRADED") == len(cases) - 1
    assert "guaranteed-flip mutation flipped=False" in err
    assert "null identity flipped=True" in err


def test_canary_treats_a_missing_flipped_field_as_degraded(tmp_path: Path) -> None:
    """Only the boolean values count, not a truthy stand-in."""
    out = tmp_path / "v.json"
    dispatch(
        [
            "canary",
            _json(tmp_path / "p.json", {"flipped": 1}),
            _json(tmp_path / "n.json", {}),
            str(out),
        ],
    )
    assert _rec(out)["verdict"] == "fail"


def _coherence(tmp_path: Path) -> str:
    """Write a fake coherence script that echoes its arguments and exits with the last one's code.

    Returns:
        The script's path as text.

    """
    script = tmp_path / "coherence.py"
    script.write_text(FAKE_COHERENCE, encoding="utf-8")
    return str(script)


def test_cohere_passes_a_zero_exit_and_lets_the_error_output_through(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 0 is a pass with no reason; the child's standard error still reaches ours."""
    out = tmp_path / "v.json"
    dispatch(
        [
            "cohere",
            "coh",
            "proj",
            str(out),
            "calc-a.json",
            "calc-rc0",
            "--coherence",
            _coherence(tmp_path),
        ]
    )
    assert _rec(out) == {"verb": "coh", "verdict": "pass"}
    err = capsys.readouterr().err
    assert err == "argv: --from-calcs proj calc-a.json calc-rc0\nthe residual\n"


def test_cohere_carries_the_residual_in_the_record_and_keeps_cannot_run_apart(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 1 is a fail and exit 2 is cannot-run; both carry the stripped residual as the reason."""
    out = tmp_path / "v.json"
    script = _coherence(tmp_path)
    dispatch(["cohere", "coh", "proj", str(out), "c-rc1", "--coherence", script])
    refuted = _rec(out)
    dispatch(["cohere", "coh", "proj", str(out), "c-rc2", "--coherence", script])
    declined = _rec(out)
    assert refuted["verdict"] == "fail"
    assert declined["verdict"] == "cannot-run"
    assert refuted["why"] == "argv: --from-calcs proj c-rc1\nthe residual"
    assert declined["why"] == "argv: --from-calcs proj c-rc2\nthe residual"
    assert capsys.readouterr().err.count("the residual") == len((refuted, declined))


def test_cohere_keeps_the_last_two_thousand_characters_of_the_residual(tmp_path: Path) -> None:
    """The diagnosis is at the end, so the cap keeps the tail."""
    script = tmp_path / "loud.py"
    script.write_text(
        'import sys\nsys.stderr.write("A" * 3000 + "END")\nraise SystemExit(1)\n',
        encoding="utf-8",
    )
    out = tmp_path / "v.json"
    dispatch(["cohere", "coh", "proj", str(out), "--coherence", str(script)])
    why = _rec(out)["why"]
    assert isinstance(why, str)
    assert (len(why), why.endswith("AAAEND")) == (2000, True)


def test_cohere_defaults_to_the_paperkit_layout_under_the_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without --coherence the script is paperkit/coherence.py, relative to the cwd."""
    (tmp_path / "paperkit").mkdir()
    (tmp_path / "paperkit" / "coherence.py").write_text(FAKE_COHERENCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    dispatch(["cohere", "coh", "proj", "v.json", "c-rc2"])
    assert _rec(tmp_path / "v.json")["verdict"] == "cannot-run"


def test_dispatch_refuses_a_missing_or_unknown_command() -> None:
    """The usage line lists the commands."""
    with pytest.raises(UsageError, match=r"usage: mikemol-gradekit-verdict <emit\|exists\|agg"):
        dispatch([])
    with pytest.raises(UsageError, match=r"usage: mikemol-gradekit-verdict"):
        dispatch(["nope", "a"])


def test_dispatch_checks_the_number_of_arguments_per_command() -> None:
    """Fixed-arity commands want exactly their count; variadic ones want at least theirs."""
    with pytest.raises(UsageError, match="emit: expected exactly 3 arguments"):
        dispatch(["emit", "v", "pass"])
    with pytest.raises(UsageError, match="emit: expected exactly 3 arguments"):
        dispatch(["emit", "v", "pass", "out", "extra"])
    with pytest.raises(UsageError, match="agg: expected at least 4 arguments"):
        dispatch(["agg", "v", "out", "f"])
    with pytest.raises(UsageError, match="agree: expected at least 2 arguments"):
        dispatch(["agree", "v"])
    with pytest.raises(UsageError, match="cohere: expected at least 3 arguments"):
        dispatch(["cohere", "v", "p"])
    with pytest.raises(UsageError, match="canary: expected exactly 3 arguments"):
        dispatch(["canary", "a", "b"])


def test_dispatch_allows_each_option_only_on_its_own_command(tmp_path: Path) -> None:
    """--account belongs to emit and --coherence to cohere; elsewhere they are unknown."""
    out = str(tmp_path / "v.json")
    with pytest.raises(UsageError, match="unknown option '--account'"):
        dispatch(["exists", "v", str(tmp_path), out, "--account", "x"])
    with pytest.raises(UsageError, match="unknown option '--coherence'"):
        dispatch(["emit", "v", "pass", out, "--coherence", "x"])


def test_main_writes_the_record_and_returns_zero_whatever_the_verdict(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A failing verdict is data, not an exit status."""
    out = tmp_path / "v.json"
    assert main(["emit", "cmd", "fail", str(out)]) == 0
    assert _rec(out)["verdict"] == "fail"
    assert capsys.readouterr() == ("", "")


def test_main_reports_expected_failures_as_one_line_and_status_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Usage, unreadable, malformed and unknown-floor inputs each end in one named line."""
    rec = _json(tmp_path / "r.json", {"grade": "vacuous"})
    out = str(tmp_path / "v.json")
    cases = [
        [],
        ["calc", "pk", str(tmp_path / "absent.json"), out],
        ["calc", "pk", _json(tmp_path / "list.json", [1]), out],
        ["agg", "a", out, "grade", "below:nope", rec],
        ["emit", "cmd", "pass", str(tmp_path / "nodir" / "v.json")],
    ]
    statuses = [main(words) for words in cases]
    errors = capsys.readouterr().err.splitlines()
    assert statuses == [USAGE_STATUS] * len(cases)
    assert [line.startswith("mikemol-gradekit-verdict: ") for line in errors] == [True] * len(cases)
    assert "not a rung" in errors[3]


def test_main_without_arguments_reads_sys_argv_and_the_guard_exits_with_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no argv given main reads sys.argv; running the module as a script exits 0."""
    out = tmp_path / "v.json"
    monkeypatch.setattr(sys, "argv", ["prog", "emit", "cmd", "pass", str(out)])
    assert main() == 0
    assert _rec(out) == {"verb": "cmd", "verdict": "pass"}
    out.unlink()
    monkeypatch.delitem(sys.modules, "mikemol.gradekit.verdict")
    with pytest.raises(SystemExit) as exited:
        cast("object", runpy.run_module("mikemol.gradekit.verdict", run_name="__main__"))
    assert exited.value.code == 0
    assert _rec(out) == {"verb": "cmd", "verdict": "pass"}


def test_the_record_is_replaced_atomically_leaving_no_temporary_beside_it(tmp_path: Path) -> None:
    """Writing over an existing record replaces it and leaves only the record in the directory."""
    out = tmp_path / "v.json"
    out.write_text("old", encoding="utf-8")
    write_record(out, "cmd", "pass")
    assert [p.name for p in tmp_path.iterdir()] == ["v.json"]
    assert _rec(out) == {"verb": "cmd", "verdict": "pass"}

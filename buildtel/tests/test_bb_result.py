# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One target's result and its test counts, read from the service's answer and two blobs (W1750)."""

import pytest

from mikemol.buildtel import bb_result

_XML_SEVEN = '<testsuites><testsuite name="p" errors="0" failures="1" skipped="2" tests="7">'
_XML_ONE = '<testsuites><testsuite name="p" errors="0" failures="0" skipped="0" tests="1">'
_LOG_THREE = "Executing tests\n...\n3 passed in 0.20s\n"
_LOG_MIXED = "x\n== 1 failed, 3 passed, 2 skipped in 1.5s ==\n"
_URIS = {"test.xml": "bytestream://x/xml", "test.log": "bytestream://x/log"}
_THREE = 3
_FOUR = 4


def _answer(status: str = "PASSED", attempts: int = 1) -> dict[str, object]:
    outputs = [{"name": name, "uri": uri} for name, uri in _URIS.items()]
    event = {"testResult": {"status": status, "testActionOutput": outputs}}
    target = {
        "status": status,
        "testResultEvents": [event],
        "testSummary": {"totalRunDurationMillis": "2169", "attemptCount": attempts},
    }
    return {"targetGroups": [{"targets": [target]}]}


def _blobs(xml: str, log: str) -> bb_result.Blob:
    texts = {"test.xml": xml, "test.log": log}

    def blob(_invocation: str, _uri: str, name: str) -> str:
        return texts[name]

    return blob


def test_the_xml_tally_is_pass_fail_and_skip_with_errors_counted_as_failures() -> None:
    """Seven cases, one failure and two skips leave four passes."""
    counts = bb_result.xml_counts(_XML_SEVEN)
    assert counts is not None
    assert (counts.passed, counts.failed, counts.skipped) == (_FOUR, 1, 2)
    assert counts.source == "test.xml"


def test_an_xml_without_its_four_attributes_or_a_suite_reads_as_nothing() -> None:
    """A missing attribute is not a zero: it would say the target ran and found nothing."""
    assert bb_result.xml_counts("<testsuites></testsuites>") is None
    assert bb_result.xml_counts('<testsuite tests="3" failures="0">') is None


def test_the_log_summary_line_is_read_whole_or_mixed() -> None:
    """The last `N passed` style line wins, with failures, passes and skips."""
    plain = bb_result.log_counts(_LOG_THREE)
    mixed = bb_result.log_counts(_LOG_MIXED)
    assert plain is not None
    assert mixed is not None
    assert (plain.passed, plain.failed, plain.skipped) == (_THREE, 0, 0)
    assert (mixed.passed, mixed.failed, mixed.skipped) == (_THREE, 1, 2)
    assert bb_result.log_counts("no summary here") is None


def test_a_suite_of_many_cases_is_taken_at_its_word_and_a_single_case_yields_to_the_log() -> None:
    """tests=1 with a log saying 3 passed means the log has the real tally."""
    many = bb_result.xml_counts(_XML_SEVEN)
    one = bb_result.xml_counts(_XML_ONE)
    log = bb_result.log_counts(_LOG_THREE)
    assert bb_result.choose(many, log) == many
    assert bb_result.choose(one, log) == log
    assert bb_result.choose(one, None) == one
    assert bb_result.choose(None, None) is None


def test_a_result_carries_status_duration_attempts_and_the_counts_with_their_source() -> None:
    """The one-command answer to 'did these run?'."""
    got = bb_result.result_of(_answer(), "//a:t", (_blobs(_XML_SEVEN, _LOG_THREE), "inv"))
    assert got == {
        "label": "//a:t",
        "status": "PASSED",
        "duration_ms": 2169,
        "attempts": 1,
        "counts": {"passed": _FOUR, "failed": 1, "skipped": 2, "source": "test.xml"},
    }


def test_a_target_with_no_outputs_reports_null_counts_not_zeros() -> None:
    """A built target has no log: its counts are unknown, and the result says so."""
    answer = {"targetGroups": [{"targets": [{"status": "BUILT"}]}]}
    got = bb_result.result_of(answer, "//a:b", (_blobs("", ""), "inv"))
    assert got is not None
    assert got["counts"] is None
    assert got["status"] == "BUILT"


def test_an_answer_with_no_target_is_none() -> None:
    """The service's empty answer is 'no such target', not a crash."""
    assert bb_result.result_of({}, "//a:t", (_blobs("", ""), "inv")) is None


def test_main_prints_the_result_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    """The command line: invocation id and label in, one JSON object out."""

    def fetch(_invocation: str, _label: str) -> object:
        return _answer()

    code = bb_result.main(["inv", "//a:t"], fetch, _blobs(_XML_SEVEN, _LOG_THREE))
    shown = capsys.readouterr().out
    assert code == 0
    assert '"label": "//a:t"' in shown
    assert f'"passed": {_FOUR}' in shown


def test_main_refuses_a_bad_command_line_and_names_a_missing_target(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Usage is exit 2, and an invocation with no such target is exit 1 naming both."""

    def empty(_invocation: str, _label: str) -> object:
        return {}

    assert bb_result.main(["only-one"], empty, _blobs("", "")) == bb_result.EXIT_USAGE
    assert bb_result.main(["inv", "//a:t"], empty, _blobs("", "")) == bb_result.EXIT_NO_TARGET
    assert "no target //a:t in invocation inv" in capsys.readouterr().err


def test_main_says_the_service_did_not_answer(capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown label gets HTTP 500, and the message says so rather than 'unreachable'."""

    def refused(_invocation: str, _label: str) -> object:
        message = "HTTP 500"
        raise OSError(message)

    assert bb_result.main(["inv", "//a:t"], refused, _blobs("", "")) == bb_result.EXIT_UNREACHABLE
    assert "HTTP 500 (an unknown label gets HTTP 500)" in capsys.readouterr().err

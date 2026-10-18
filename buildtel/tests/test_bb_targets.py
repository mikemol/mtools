# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bb_targets`: an invocation's tests rank by duration and say what they cover."""

from __future__ import annotations

import http.server
import json
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import bb_records, bb_targets

if TYPE_CHECKING:
    from collections.abc import Iterator

_SLOW = "1850"
_FAST = "981"
_SLOW_MS = 1850
_FAST_MS = 981
_BUILT_TOTAL = 1324
_TEST_TOTAL = 3
_USAGE_EXIT = 2
_UNREACHABLE_EXIT = 3
_NOT_FOUND = 404
_MANY = 35


def _test(label: object, millis: object, status: object = "PASSED") -> object:
    """Build one test target as BuildBuddy's GetInvocation spells it.

    Returns:
        the target, with a `testSummary` carrying `totalRunDurationMillis`.

    """
    return {
        "metadata": {"label": label, "ruleType": "py_test rule", "testSize": "SMALL"},
        "status": status,
        "testSummary": {"overallStatus": status, "totalRunDurationMillis": millis},
    }


def _built(label: str) -> object:
    return {"metadata": {"label": label, "ruleType": "venv rule"}, "status": "BUILT"}


def _page(*groups: object) -> object:
    return {"invocation": [{"invocationId": "inv", "targetGroups": list(groups)}]}


def _group(targets: list[object], total: int) -> object:
    return {"status": "PASSED", "targets": targets, "totalCount": str(total)}


@dataclass
class _Service:
    """A local stand-in for BuildBuddy's web service: what it was sent, what it answers."""

    port: int = 0
    status: int = 200
    answer: object = field(default_factory=dict)
    seen: list[tuple[str, dict[str, object]]] = field(default_factory=list)


@pytest.fixture()
def service() -> Iterator[_Service]:
    """Serve one local HTTP endpoint that records each POST and answers with `answer`.

    Yields:
        the service handle, its `port` filled in.

    """
    state = _Service()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            sent: object = json.loads(self.rfile.read(length))
            if isinstance(sent, dict):
                state.seen.append((self.path, {str(k): v for k, v in sent.items()}))
            payload = json.dumps(state.answer).encode()
            self.send_response(state.status)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


def test_post_asks_for_the_invocation_by_id_and_returns_the_parsed_response(
    service: _Service,
) -> None:
    """The body is a lookup of the invocation id, the path is GetInvocation."""
    service.answer = _page()
    got = bb_targets.post("inv-1", host="127.0.0.1", port=service.port)
    assert got == service.answer
    assert service.seen == [(bb_targets.RPC, {"lookup": {"invocationId": "inv-1"}})]


def test_post_refuses_any_status_but_200(service: _Service) -> None:
    """A 404 is an OSError naming the status, never an empty response."""
    service.status = _NOT_FOUND
    with pytest.raises(OSError, match="HTTP 404"):
        bb_targets.post("inv-1", host="127.0.0.1", port=service.port)


def test_tests_rank_longest_first_and_a_built_target_is_listed_but_not_ranked() -> None:
    """Only a target with a testSummary has a duration; the others count toward `listed`."""
    page = _page(
        _group([_built("//a:venv")], _BUILT_TOTAL),
        _group([_test("//b:fast", _FAST), _test("//b:slow", _SLOW)], len(("b", "c"))),
    )
    report = bb_targets.parse(page)
    assert [(t.label, t.millis) for t in report.tests] == [
        ("//b:slow", _SLOW_MS),
        ("//b:fast", _FAST_MS),
    ]
    assert report.listed == _TEST_TOTAL


def test_the_report_states_how_many_targets_the_groups_hold_against_how_many_it_listed() -> None:
    """Each group is paged, so `total` sums the groups' counts and `listed` what came back."""
    page = _page(_group([_built("//a:venv")], _BUILT_TOTAL), _group([_test("//b:t", _SLOW)], 1))
    report = bb_targets.parse(page)
    assert (report.listed, report.total) == (len(("a", "b")), _BUILT_TOTAL + 1)


def test_equal_durations_order_by_label() -> None:
    """A tie is broken by label so the ranking is stable between runs."""
    page = _page(_group([_test("//z:t", _SLOW), _test("//a:t", _SLOW)], len(("a", "z"))))
    assert [t.label for t in bb_targets.parse(page).tests] == ["//a:t", "//z:t"]


def test_what_it_cannot_read_is_counted_unreadable_not_dropped() -> None:
    """A target that is no object or has no label, and a group that is no object, each count."""
    page = _page(
        _group(["not-a-target", {"testSummary": {}}, _test(None, _SLOW)], _TEST_TOTAL),
        "not-a-group",
    )
    report = bb_targets.parse(page)
    assert report.unreadable == _TEST_TOTAL + 1
    assert report.tests == []


def test_a_response_with_no_invocation_is_one_unreadable() -> None:
    """Neither an empty list nor a non-object response is a report of zero tests."""
    assert bb_targets.parse({"invocation": []}).unreadable == 1
    assert bb_targets.parse([1, 2]).unreadable == 1


def test_a_duration_that_is_not_digits_reads_as_zero_and_a_missing_status_as_unknown() -> None:
    """A protobuf int64 is a digit string; anything else is 0, and no status is `?`."""
    page = _page(_group([_test("//a:t", "-5", status=None)], 1))
    only = bb_targets.parse(page).tests[0]
    assert (only.millis, only.status) == (0, "?")


def test_main_prints_the_ranking_with_the_coverage_beside_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The report carries listed, total, unreadable, the count of tests and the ranked rows."""
    page = _page(_group([_test("//b:slow", _SLOW)], 1))
    assert bb_targets.main(["inv"], lambda _i: page) == 0
    report: object = json.loads(capsys.readouterr().out)
    assert report == {
        "listed": 1,
        "total": 1,
        "unreadable": 0,
        "tests_found": 1,
        "tests": [{"label": "//b:slow", "status": "PASSED", "millis": _SLOW_MS}],
    }


def test_main_lists_only_the_longest_thirty_and_says_how_many_it_found(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Thirty-five tests report as thirty, the slowest first, with the full count stated."""
    rows = [_test(f"//t:t{n}", str(n)) for n in range(_MANY)]
    assert bb_targets.main(["inv"], lambda _i: _page(_group(rows, _MANY))) == 0
    said = capsys.readouterr().out
    assert f'"tests_found": {_MANY}' in said
    assert '"label": "//t:t34"' in said
    assert '"label": "//t:t4"' not in said
    assert said.index('"//t:t34"') < said.index('"//t:t33"')


@pytest.mark.parametrize("argv", [[], ["-h"], ["a", "b"]])
def test_main_refuses_anything_but_one_invocation_id(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """No operand, a flag, or two operands is a usage error: exit 2, the usage line, no fetch."""

    def fetch(_i: str) -> object:
        pytest.fail("a usage error must not reach the service")

    assert bb_targets.main(argv, fetch) == _USAGE_EXIT
    assert capsys.readouterr().err == bb_targets.USAGE + "\n"


def test_main_reports_an_unreachable_service_with_exit_3(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An OSError from the fetch is exit 3 naming the endpoint, never a traceback."""

    def fetch(_i: str) -> object:
        msg = "boom"
        raise OSError(msg)

    assert bb_targets.main(["inv"], fetch) == _UNREACHABLE_EXIT
    assert f"{bb_records.HOST}" in capsys.readouterr().err

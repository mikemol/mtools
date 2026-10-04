# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bb_records`: pages fold into one tally that says how much it covers."""

from __future__ import annotations

import http.server
import json
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import bb_records

if TYPE_CHECKING:
    from collections.abc import Iterator

_CPU_ONE = 1_500_000_000
_CPU_TWO = 500_000_000
_PEAK_ONE = 4096
_PEAK_TWO = 1024
_SNIPPET_HEAD = 60
_USAGE_EXIT = 2
_UNREACHABLE_EXIT = 3
_NOT_FOUND = 404
_UNREADABLE = 3


def _record(worker: object, snippet: object, cpu: str = "", peak: str = "") -> object:
    """Build one execution record as BuildBuddy's JSON spells it.

    Returns:
        the record, with `usageStats` only when a figure is given.

    """
    meta: dict[str, object] = {"worker": worker}
    if cpu or peak:
        meta["usageStats"] = {"cpuNanos": cpu, "peakMemoryBytes": peak}
    return {"executedActionMetadata": meta, "commandSnippet": snippet}


@dataclass
class _Service:
    """A local stand-in for BuildBuddy's web service: what it was sent, what it answers."""

    port: int = 0
    status: int = 200
    answer: object = field(default_factory=dict)
    seen: list[tuple[str, dict[str, object]]] = field(default_factory=list)
    types: list[str] = field(default_factory=list)


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
            state.types.append(self.headers.get("Content-Type", ""))
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


def test_post_sends_the_invocation_lookup_and_returns_the_parsed_page(service: _Service) -> None:
    """The body names the invocation, the path is the RPC, and the answer comes back parsed."""
    service.answer = {"execution": [], "nextPageToken": ""}
    page = bb_records.post("inv-1", "", host="127.0.0.1", port=service.port)
    assert page == service.answer
    assert service.seen == [(bb_records.RPC, {"executionLookup": {"invocationId": "inv-1"}})]
    assert service.types == ["application/json"]


def test_post_carries_the_page_token_only_when_there_is_one(service: _Service) -> None:
    """A continuation page names its token in the body; a first page has no `pageToken` key."""
    bb_records.post("inv-1", "tok-2", host="127.0.0.1", port=service.port)
    assert service.seen[0][1]["pageToken"] == "tok-2"
    bb_records.post("inv-1", "", host="127.0.0.1", port=service.port)
    assert "pageToken" not in service.seen[1][1]


def test_post_refuses_any_status_but_200(service: _Service) -> None:
    """A 404 from the service is an OSError naming the status, never an empty page."""
    service.status = _NOT_FOUND
    with pytest.raises(OSError, match="HTTP 404"):
        bb_records.post("inv-1", "", host="127.0.0.1", port=service.port)


def test_command_is_the_text_inside_sh_dash_c_quotes() -> None:
    """A record's check is what sits between `sh -c '` and the next quote."""
    assert bb_records.command("env X=1 sh -c 'echo hi' tail") == "echo hi"


def test_command_without_the_wrapper_is_the_head_of_the_snippet() -> None:
    """With no `sh -c '` the first 60 characters stand for the command."""
    long = "x" * (_SNIPPET_HEAD + 10)
    assert bb_records.command(long) == "x" * _SNIPPET_HEAD


def test_collect_walks_every_page_following_the_token() -> None:
    """Page one's token is fed back; the walk ends at a page with none, and both fold in."""
    pages: dict[str, object] = {
        "": {"execution": [_record("w1", "sh -c 'a'")], "nextPageToken": "t2"},
        "t2": {"execution": [_record("w2", "sh -c 'b'")]},
    }
    asked: list[tuple[str, str]] = []

    def fetch(invocation_id: str, token: str) -> object:
        asked.append((invocation_id, token))
        return pages[token]

    tally = bb_records.collect("inv-9", fetch)
    assert asked == [("inv-9", ""), ("inv-9", "t2")]
    assert tally.records == len(pages)
    assert dict(tally.by_worker) == {"w1": 1, "w2": 1}
    assert dict(tally.by_command) == {"a": 1, "b": 1}


def test_collect_sums_cpu_and_keeps_the_peak_memory_maximum() -> None:
    """CPU nanoseconds add across records; peak memory is the largest one, not the sum."""
    page: object = {
        "execution": [
            _record("w", "sh -c 'a'", cpu=str(_CPU_ONE), peak=str(_PEAK_ONE)),
            _record("w", "sh -c 'a'", cpu=str(_CPU_TWO), peak=str(_PEAK_TWO)),
        ],
    }
    tally = bb_records.collect("inv", lambda _i, _t: page)
    assert tally.cpu_nanos == _CPU_ONE + _CPU_TWO
    assert tally.peak_memory_max == _PEAK_ONE


def test_a_record_it_cannot_read_is_counted_not_dropped() -> None:
    """A non-object, a record without metadata and one without a snippet are each unreadable."""
    page: object = {
        "execution": [
            "not-a-record",
            {"commandSnippet": "sh -c 'a'"},
            {"executedActionMetadata": {"worker": "w"}},
            _record("w", "sh -c 'ok'"),
        ],
    }
    tally = bb_records.collect("inv", lambda _i, _t: page)
    assert (tally.records, tally.unreadable) == (1, _UNREADABLE)


def test_a_non_numeric_usage_figure_and_a_missing_worker_read_as_zero_and_unknown() -> None:
    """A usage figure that is not digits is 0; a worker that is not a string is `?`."""
    page: object = {"execution": [_record(None, "sh -c 'a'", cpu="-5", peak="x")]}
    tally = bb_records.collect("inv", lambda _i, _t: page)
    assert dict(tally.by_worker) == {"?": 1}
    assert (tally.cpu_nanos, tally.peak_memory_max) == (0, 0)


def test_a_page_that_is_not_an_object_ends_the_walk_unreadable() -> None:
    """A JSON array where a page should be counts one unreadable and stops."""
    tally = bb_records.collect("inv", lambda _i, _t: [1, 2])
    assert (tally.records, tally.unreadable) == (0, 1)


def test_an_execution_field_that_is_not_an_array_contributes_nothing() -> None:
    """`execution` as a string is no list of records: nothing folds in, nothing is unreadable."""
    tally = bb_records.collect("inv", lambda _i, _t: {"execution": "oops"})
    assert (tally.records, tally.unreadable) == (0, 0)


def test_main_prints_the_tally_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    """The report carries counts, CPU seconds, peak memory and the by-worker/by-command maps."""
    page: object = {
        "execution": [_record("w1", "sh -c 'a'", cpu=str(_CPU_ONE), peak=str(_PEAK_ONE))],
    }
    assert bb_records.main(["inv"], lambda _i, _t: page) == 0
    report: object = json.loads(capsys.readouterr().out)
    assert report == {
        "records": 1,
        "unreadable": 0,
        "cpu_seconds": 1.5,
        "peak_memory_max_bytes": _PEAK_ONE,
        "by_worker": {"w1": 1},
        "by_command": {"a": 1},
    }


@pytest.mark.parametrize("argv", [[], ["-h"], ["a", "b"]])
def test_main_refuses_anything_but_one_invocation_id(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """No operand, a flag, or two operands is a usage error: exit 2, the usage line, no fetch."""

    def fetch(_i: str, _t: str) -> object:
        pytest.fail("a usage error must not reach the service")

    assert bb_records.main(argv, fetch) == _USAGE_EXIT
    assert capsys.readouterr().err == bb_records.USAGE + "\n"


def test_main_reports_an_unreachable_service_with_exit_3(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An OSError from the fetch is exit 3 naming the endpoint, never a traceback."""

    def fetch(_i: str, _t: str) -> object:
        msg = "boom"
        raise OSError(msg)

    assert bb_records.main(["inv"], fetch) == _UNREACHABLE_EXIT
    assert "unreachable: boom" in capsys.readouterr().err

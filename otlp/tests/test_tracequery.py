# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`query-traces` prints a store's spans as JSON lines, and an outage is never an empty result."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.otlp import cli, sender, tracequery

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

BASE = "http://traces:10428"
_OK = 200
_BAD_REQUEST = 400
_BAD_GATEWAY = 502
_DAY_US = 86_400_000_000
_WINDOW = (1_000, 9_000)
_QUERY = ("mikemol-train", "train.round", 5)
_TRACE = {
    "traceID": "aa" * 16,
    "spans": [
        {
            "traceID": "aa" * 16,
            "spanID": "bb" * 8,
            "operationName": "train.round",
            "startTime": 1_792_537_156_599_782,
            "duration": 1_214,
            "tags": [{"key": "failed", "type": "string", "value": "//a:t"}, "stray"],
        }
    ],
}
_FLAT = {
    "trace_id": "aa" * 16,
    "span_id": "bb" * 8,
    "name": "train.round",
    "start_us": 1_792_537_156_599_782,
    "duration_us": 1_214,
    "fields": {"failed": "//a:t"},
}


def _answer(status: int, body: object) -> tracequery.Get:
    def get(_url: str) -> tuple[int, str]:
        return status, body if isinstance(body, str) else json.dumps(body)

    return get


def test_the_search_url_carries_service_window_limit_and_the_name_when_given() -> None:
    """An empty name leaves `operation` out, so every span of the service matches."""
    named = tracequery.search_url(BASE + "/", "svc", "a b", _WINDOW, 7)
    assert named.startswith(f"{BASE}/select/jaeger/api/traces?service=svc&start=1000&end=9000")
    assert named.endswith("&limit=7&operation=a+b")
    unnamed = tracequery.search_url(BASE, "svc", "", _WINDOW, 7)
    assert "operation" not in unnamed


def test_each_span_is_one_flat_json_line_with_its_attributes() -> None:
    """A found trace prints its spans' ids, name, times and tags; a malformed tag is skipped."""
    code, lines, said = tracequery.run(BASE, _QUERY, _WINDOW, _answer(_OK, {"data": [_TRACE]}))
    assert (code, said) == (tracequery.EXIT_OK, "")
    assert lines == [json.dumps(_FLAT, sort_keys=True)]


def test_a_store_that_answered_with_no_trace_is_exit_zero_and_no_lines() -> None:
    """Nothing matched is an answer, not an outage."""
    code, lines, _ = tracequery.run(BASE, _QUERY, _WINDOW, _answer(_OK, {"data": []}))
    assert (code, lines) == (tracequery.EXIT_OK, [])


def _down(_url: str) -> tuple[int, str]:
    message = "connection refused"
    raise sender.SendError(message)


def test_a_store_that_did_not_answer_is_exit_three_never_empty() -> None:
    """A refused connection, a non-JSON reply and a body with no `data` are all exit 3."""
    code, lines, said = tracequery.run(BASE, _QUERY, _WINDOW, _down)
    assert code == tracequery.EXIT_UNREACHABLE
    assert lines == []
    assert "did not answer" in said
    html = tracequery.run(BASE, _QUERY, _WINDOW, _answer(_BAD_GATEWAY, "<html>bad</html>"))
    assert (html[0], html[1]) == (tracequery.EXIT_UNREACHABLE, [])
    odd = tracequery.run(BASE, _QUERY, _WINDOW, _answer(_OK, {"unrelated": 1}))
    assert (odd[0], odd[1]) == (tracequery.EXIT_UNREACHABLE, [])
    wrong_status = tracequery.run(BASE, _QUERY, _WINDOW, _answer(_BAD_GATEWAY, {"data": []}))
    assert wrong_status[0] == tracequery.EXIT_UNREACHABLE


def test_a_search_the_store_rejects_is_exit_four_naming_the_error() -> None:
    """A malformed parameter reads differently from a dead store."""
    body = {"errors": [{"code": _BAD_REQUEST, "msg": "bad start"}]}
    code, lines, said = tracequery.run(BASE, _QUERY, _WINDOW, _answer(_BAD_REQUEST, body))
    assert (code, lines) == (tracequery.EXIT_REJECTED, [])
    assert "bad start" in said
    plain = tracequery.run(BASE, _QUERY, _WINDOW, _answer(_BAD_REQUEST, {"errors": ["no good"]}))
    assert "no good" in plain[2]


def test_the_verb_needs_an_endpoint_and_asks_no_network_without_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No `victoriatraces-http` is exit 3 and says which name is missing."""
    monkeypatch.delenv("MIKEMOL_ENDPOINTS", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cli.main(["query-traces", "--service", "svc"]) == tracequery.EXIT_UNREACHABLE
    assert tracequery.ENDPOINT in capsys.readouterr().err


def test_the_verb_prints_what_the_search_found_and_defaults_to_the_last_day(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The window defaults to a day ending at `--end-us`; the lines reach stdout."""
    seen: list[tuple[str, str, int, tuple[int, int]]] = []

    def run(
        _base: str, query: tuple[str, str, int], window: tuple[int, int]
    ) -> tuple[int, list[str], str]:
        seen.append((*query, window))
        return tracequery.EXIT_OK, ['{"a": 1}'], ""

    monkeypatch.setattr(tracequery, "run", run)
    args = ["query-traces", "--url", BASE, "--service", "svc", "--name", "n", "--end-us", "90"]
    assert cli.main([*args, "--limit", "3"]) == tracequery.EXIT_OK
    assert capsys.readouterr().out == '{"a": 1}\n'
    assert seen == [("svc", "n", 3, (90 - _DAY_US, 90))]

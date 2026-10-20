# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`query-metrics` prints a store's series as JSON lines, and an outage is never an empty result."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.otlp import cli, query_metrics, sender

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

BASE = "http://store:8428"
_OK = 200
_UNPROCESSABLE = 422
_BAD_GATEWAY = 502
_SERIES = {"metric": {"job": "web"}, "value": [1, "2"]}


def _answer(status: int, body: object) -> query_metrics.Get:
    def get(_url: str) -> tuple[int, str]:
        return status, body if isinstance(body, str) else json.dumps(body)

    return get


def _success(result: list[object]) -> dict[str, object]:
    return {"status": "success", "data": {"resultType": "vector", "result": result}}


def test_an_instant_and_a_range_query_build_their_urls() -> None:
    """The expression is URL-encoded; a range carries start, end and step."""
    instant = query_metrics.query_url(BASE + "/", "sum(up{job='a b'})")
    assert instant.startswith(f"{BASE}/api/v1/query?query=sum%28up")
    ranged = query_metrics.query_url(BASE, "up", ("1", "9", "30s"))
    assert ranged == f"{BASE}/api/v1/query_range?query=up&start=1&end=9&step=30s"


def test_each_series_is_one_json_line() -> None:
    """A successful answer prints its series, exit 0."""
    get = _answer(_OK, _success([_SERIES, _SERIES]))
    code, lines, said = query_metrics.run(BASE, "up", get=get)
    assert (code, said) == (query_metrics.EXIT_OK, "")
    assert lines == [json.dumps(_SERIES, sort_keys=True)] * 2


def test_a_store_that_answered_with_no_series_is_exit_zero_and_no_lines() -> None:
    """No series matched is an answer, not an outage."""
    code, lines, _ = query_metrics.run(BASE, "nothing", get=_answer(_OK, _success([])))
    assert (code, lines) == (query_metrics.EXIT_OK, [])


def _down(_url: str) -> tuple[int, str]:
    message = "connection refused"
    raise sender.SendError(message)


def test_a_store_that_did_not_answer_is_exit_three_never_empty() -> None:
    """A refused connection and a reply that is not a query answer are both exit 3."""
    code, lines, said = query_metrics.run(BASE, "up", get=_down)
    assert code == query_metrics.EXIT_UNREACHABLE
    assert lines == []
    assert "did not answer" in said
    html = query_metrics.run(BASE, "up", get=_answer(_BAD_GATEWAY, "<html>bad gateway</html>"))
    assert html[0] == query_metrics.EXIT_UNREACHABLE
    assert html[1] == []


def test_a_query_the_store_rejects_is_exit_four_naming_the_error() -> None:
    """A PromQL typo reads differently from a dead store."""
    body = {"status": "error", "errorType": "bad_data", "error": "parse error at char 3"}
    code, lines, said = query_metrics.run(BASE, "up{", get=_answer(_UNPROCESSABLE, body))
    assert (code, lines) == (query_metrics.EXIT_REJECTED, [])
    assert "bad_data: parse error at char 3" in said


def test_the_verb_needs_an_endpoint_and_all_three_range_bounds_or_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No `vmsingle-http` is exit 3, a partial range is exit 2, and neither asks the network."""
    monkeypatch.delenv("MIKEMOL_ENDPOINTS", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cli.main(["query-metrics", "up"]) == query_metrics.EXIT_UNREACHABLE
    partial = ["query-metrics", "up", "--url", BASE, "--start", "1"]
    assert cli.main(partial) == cli.EXIT_USAGE
    assert "together or none" in capsys.readouterr().err

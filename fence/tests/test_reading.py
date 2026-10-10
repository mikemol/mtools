# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the guard's reading source: every failure is a blind sample (W919).

⚑ THE SUCCESSFUL READ IS THE POSITIVE CONTROL: without it, "a failure reads as None" cannot be told
from a reader that returns None for everything. The transport arm talks to a server on the loopback
interface that the test starts and stops; no real endpoint, address or store is named.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

from mikemol.fence import reading

if TYPE_CHECKING:
    from pathlib import Path

_QUERY = "histogram_quantile(0.99, sum by (le) (rate(x_bucket[5m])))"
_VALUE = 0.25
_OK: dict[str, object] = {
    "status": "success",
    "data": {"resultType": "vector", "result": [{"metric": {}, "value": [1.0, "0.25"]}]},
}
_ERROR: dict[str, object] = {"status": "error"}
_LOOPBACK = "127.0.0.1"
_OK_STATUS = 200
_BAD_REQUEST = 400
_TIMEOUT_S = 5.0


def _endpoints(tmp_path: Path, mapping: dict[str, str]) -> dict[str, str]:
    """Write the host's endpoint file and return the environment that names it.

    Returns:
        the environment mapping.

    """
    path = tmp_path / "endpoints.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")
    return {reading.ENV: str(path)}


def _nothing(_url: str, _timeout: float) -> object:
    """Stand in for a fetch that found nothing.

    Returns:
        None, the answer to a transport failure.

    """
    return None


def test_a_successful_instant_query_reads_its_first_sample(tmp_path: Path) -> None:
    """The positive control: the name resolves, the URL carries the encoded query, it parses."""
    seen: list[str] = []

    def fetcher(url: str, timeout: float) -> object:
        seen.append(f"{url}|{timeout}")
        return _OK

    env = _endpoints(tmp_path, {"vm": "http://store.invalid:8428/"})
    assert reading.reader("vm", _QUERY, env, fetcher)() == _VALUE
    assert seen[0].startswith("http://store.invalid:8428/api/v1/query?query=histogram_quantile")
    assert " " not in seen[0]


def test_an_unset_missing_or_unparseable_endpoints_file_is_blind(tmp_path: Path) -> None:
    """No address means no reading, and the fetcher is never called."""
    calls: list[str] = []

    def fetcher(url: str, timeout: float) -> object:
        calls.append(f"{url}|{timeout}")
        return _OK

    broken = tmp_path / "broken.json"
    broken.write_text("not json", encoding="utf-8")
    for env in ({}, {reading.ENV: str(tmp_path / "absent.json")}, {reading.ENV: str(broken)}):
        assert reading.reader("vm", _QUERY, env, fetcher)() is None
    assert calls == []


def test_an_unknown_name_or_a_foreign_scheme_is_blind(tmp_path: Path) -> None:
    """A name the host does not map, a file:// URL, an ftp:// URL and a bare word are refused."""
    mapping = {"files": "file:///etc/passwd", "ftp": "ftp://x/", "bare": "store"}
    env = _endpoints(tmp_path, mapping)
    assert reading.endpoint_url("absent", env) is None
    assert reading.endpoint_url("files", env) is None
    assert reading.endpoint_url("ftp", env) is None
    assert reading.endpoint_url("bare", env) is None


def test_a_non_object_endpoints_file_is_blind(tmp_path: Path) -> None:
    """A JSON list is not a name-to-url map."""
    path = tmp_path / "list.json"
    path.write_text("[1, 2]", encoding="utf-8")
    assert reading.endpoint_url("vm", {reading.ENV: str(path)}) is None


def test_a_failed_query_or_an_empty_or_odd_answer_is_blind() -> None:
    """Only a successful, non-empty, numeric, non-NaN vector is a reading."""
    cases: list[object] = [
        None,
        "text",
        {"status": "error", "data": {}},
        {"status": "success", "data": {"result": []}},
        {"status": "success", "data": {"result": [{"value": [1.0]}]}},
        {"status": "success", "data": {"result": [{"value": [1.0, "NaN"]}]}},
        {"status": "success", "data": {"result": [{"value": [1.0, "soon"]}]}},
        {"status": "success", "data": "x"},
    ]
    assert [reading.value_of(case) for case in cases] == [None] * len(cases)
    assert reading.value_of(_OK) == _VALUE


def test_a_fetcher_that_found_nothing_is_blind(tmp_path: Path) -> None:
    """A transport failure arrives as None and stays None."""
    env = _endpoints(tmp_path, {"vm": "http://store.invalid:8428"})
    assert reading.reader("vm", _QUERY, env, _nothing)() is None


class _StoreHandler(BaseHTTPRequestHandler):
    """A stand-in for a metrics store: the instant vector on the query path, a 400 elsewhere."""

    def do_GET(self) -> None:
        """Answer a GET."""
        ok = self.path.startswith(reading.QUERY_PATH)
        body = json.dumps(_OK if ok else _ERROR).encode("utf-8")
        self.send_response(_OK_STATUS if ok else _BAD_REQUEST)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_the_real_fetch_reads_a_server_and_a_dead_port_is_blind() -> None:
    """The transport against a loopback server, and the same URL once the server is gone."""
    server = HTTPServer((_LOOPBACK, 0), _StoreHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://{_LOOPBACK}:{server.server_address[1]}"
    url = reading.query_url(base, _QUERY)
    try:
        assert reading.value_of(reading.fetch(url, _TIMEOUT_S)) == _VALUE
        assert reading.value_of(reading.fetch(f"{base}/nope?x=1", _TIMEOUT_S)) is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert reading.fetch(url, _TIMEOUT_S) is None

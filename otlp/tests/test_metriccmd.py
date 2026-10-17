# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-otlp metric`: one sample out, of the kind asked (W1445).

⚑ A PLANTED LOCAL STORE, NOT LUTHEN'S: it records each POST, so the path, the protobuf body and the
kind of metric are read back through the same wheel. Whether the live vmsingle agrees is a witness
that needs the cluster and is not claimed here. The controls: a gauge must NOT arrive as a sum (a
reader that rates it would be wrong), an up-down must arrive as a non-monotonic sum, a store that
refuses is exit 1, and no destination is a usage refusal.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, cast

from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)

from mikemol.otlp import cli, metriccmd, sender

if TYPE_CHECKING:
    from collections.abc import Iterator

    import pytest

Doc = dict[str, object]
ACCEPTED = 200
REFUSED = 500


@contextmanager
def _store(status: int = ACCEPTED) -> Iterator[tuple[str, list[tuple[str, bytes]]]]:
    posts: list[tuple[str, bytes]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            posts.append((self.path, body))
            self.send_response(status)
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", posts
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _argv(base: str, *extra: str) -> list[str]:
    who = ["--service", "mikemol-commit", "--namespace", "mtools"]
    return ["metric", "--url", base, *who, "--name", "mikemol.commit.queued", *extra]


def _metric(body: bytes) -> Doc:
    doc = MessageToDict(ExportMetricsServiceRequest.FromString(body))
    resource = cast("list[Doc]", doc["resourceMetrics"])[0]
    scope = cast("list[Doc]", resource["scopeMetrics"])[0]
    return cast("list[Doc]", scope["metrics"])[0]


def test_a_gauge_is_posted_to_the_metrics_path_as_a_gauge(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The default kind: the path is luthen's, the metric is a gauge with the value and labels."""
    with _store() as (base, posts):
        argv = _argv(base, "--value", "3", "--field", "repo=mtools")
        assert cli.main(argv) == metriccmd.EXIT_SENT
    path, body = posts[0]
    assert path == sender.METRICS_PATH
    sent = _metric(body)
    assert sent["name"] == "mikemol.commit.queued"
    assert "gauge" in sent
    assert "sum" not in sent
    point = cast("list[Doc]", cast("Doc", sent["gauge"])["dataPoints"])[0]
    assert point["asInt"] == "3"
    assert "sent gauge mikemol.commit.queued=3" in capsys.readouterr().out


def test_an_up_down_sample_arrives_as_a_non_monotonic_sum() -> None:
    """The other kind: a cumulative sum that is allowed to fall."""
    with _store() as (base, posts):
        assert cli.main(_argv(base, "--value", "2", "--kind", "updown")) == metriccmd.EXIT_SENT
    total = cast("Doc", _metric(posts[0][1])["sum"])
    assert total.get("isMonotonic", False) is False
    assert total["aggregationTemporality"] == "AGGREGATION_TEMPORALITY_CUMULATIVE"


def test_a_fractional_value_stays_a_double() -> None:
    """2.5 is not rounded to 2: it arrives as a double point."""
    with _store() as (base, posts):
        assert cli.main(_argv(base, "--value", "2.5")) == metriccmd.EXIT_SENT
    point = cast("list[Doc]", cast("Doc", _metric(posts[0][1])["gauge"])["dataPoints"])[0]
    assert "asInt" not in point
    assert str(point["asDouble"]) == "2.5"


def test_a_store_that_refuses_the_sample_is_a_failed_send(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A 500 is exit 1 naming the status."""
    with _store(REFUSED) as (base, _):
        assert cli.main(_argv(base, "--value", "1")) == metriccmd.EXIT_FAILED
    assert "500" in capsys.readouterr().err


def test_no_destination_is_a_usage_refusal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no --url and no endpoints file the command refuses, naming the endpoint."""
    monkeypatch.delenv("MIKEMOL_ENDPOINTS", raising=False)
    argv = ["metric", "--service", "s", "--namespace", "n", "--name", "x", "--value", "1"]
    assert cli.main(argv) == cli.EXIT_USAGE
    assert metriccmd.ENDPOINT in capsys.readouterr().err

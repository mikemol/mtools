# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-otlp trace`: one span out, one read back, each failure named (W1438).

⚑ A PLANTED LOCAL STORE, NOT LUTHEN'S: it records each POST, and answers a GET on the Jaeger path
with the trace id it was POSTed, the way the real store does once the span is ingested. That proves
the paths, the protobuf body and the read-back logic end to end; whether the live VictoriaTraces
agrees is the witness that needs the cluster and is not claimed here. The controls are the three
ways it goes wrong: a store that refuses (exit 1), a span not visible yet (exit 3, not 0), and a
read that answers 200 without the span's own id (still not a witness).
"""

from __future__ import annotations

import base64
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, cast

import pytest
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

from mikemol.otlp import cli, sender, tracecmd

if TYPE_CHECKING:
    from collections.abc import Iterator


Doc = dict[str, object]
ACCEPTED = 200
REFUSED = 500
HEX_WIDTH = 32


class _Store:
    # What the planted store saw and how it behaves.
    def __init__(self, post_status: int, *, visible: bool) -> None:
        self.post_status = post_status
        self.visible = visible
        self.posts: list[tuple[str, bytes]] = []
        self.gets: list[str] = []
        self.trace_hex = ""


@contextmanager
def _store(post_status: int = ACCEPTED, *, visible: bool = True) -> Iterator[tuple[str, _Store]]:
    state = _Store(post_status, visible=visible)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            state.posts.append((self.path, body))
            doc = MessageToDict(ExportTraceServiceRequest.FromString(body))
            resource = cast("list[Doc]", doc["resourceSpans"])[0]
            span = cast("list[Doc]", cast("list[Doc]", resource["scopeSpans"])[0]["spans"])[0]
            raw = base64.b64decode(cast("str", span["traceId"]))
            state.trace_hex = raw.hex()
            self.send_response(state.post_status)
            self.end_headers()

        def do_GET(self) -> None:
            state.gets.append(self.path)
            found = state.visible and self.path.endswith(state.trace_hex)
            self.send_response(ACCEPTED if found else 404)
            self.end_headers()
            if found:
                self.wfile.write(f'{{"data":[{{"traceID":"{state.trace_hex}"}}]}}'.encode())

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _argv(base: str, *extra: str) -> list[str]:
    who = ["--service", "mikemol-commit", "--namespace", "mtools", "--name", "commit"]
    return ["trace", "--url", base, *who, *extra]


def test_a_span_is_posted_as_protobuf_to_the_traces_path_and_read_back(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Send then GET once: the POST path is luthen's, the GET path ends in the trace id, exit 0."""
    with _store() as (base, state):
        assert cli.main(_argv(base, "--readback", "--field", "sha=abc")) == tracecmd.EXIT_SENT
    path, _ = state.posts[0]
    assert path == sender.TRACES_PATH
    assert len(state.trace_hex) == HEX_WIDTH
    assert state.gets == [tracecmd.JAEGER_PATH + state.trace_hex]
    assert f"read back trace_id={state.trace_hex}" in capsys.readouterr().out


def test_without_readback_nothing_is_fetched(capsys: pytest.CaptureFixture[str]) -> None:
    """The default sends and stops: no GET is made and the trace id is printed for later."""
    with _store() as (base, state):
        assert cli.main(_argv(base)) == tracecmd.EXIT_SENT
    assert not state.gets
    assert f"trace_id={state.trace_hex}" in capsys.readouterr().out


def test_a_span_not_visible_yet_is_busy_not_success(capsys: pytest.CaptureFixture[str]) -> None:
    """The control: a 404 on the read is exit 3 with the URL to retry, never a quiet 0."""
    with _store(visible=False) as (base, state):
        assert cli.main(_argv(base, "--readback")) == tracecmd.EXIT_BUSY
    err = capsys.readouterr().err
    assert "not visible yet (status 404)" in err
    assert tracecmd.JAEGER_PATH + state.trace_hex in err


def test_a_store_that_refuses_the_span_is_a_failed_send(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A 500 on the POST exits 1 naming the status, and no read is attempted."""
    with _store(REFUSED) as (base, state):
        assert cli.main(_argv(base, "--readback")) == tracecmd.EXIT_FAILED
    assert "500" in capsys.readouterr().err
    assert not state.gets


def test_an_answer_without_the_spans_own_id_is_not_a_witness() -> None:
    """The control for the read: 200 with some other trace's body is busy, not found."""

    def post(url: str, body: bytes) -> int:
        del url, body
        return ACCEPTED

    def get(url: str) -> tuple[int, str]:
        del url
        return ACCEPTED, '{"data":[{"traceID":"someone-else"}]}'

    request = tracecmd.Request("http://x", "svc", "ns", "", "n", "UNSET", 1, {}, readback=True)
    assert tracecmd.run(request, post, get) == tracecmd.EXIT_BUSY


def test_no_destination_is_a_usage_refusal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no --url and no endpoints file the command refuses, naming the endpoint."""
    monkeypatch.delenv("MIKEMOL_ENDPOINTS", raising=False)
    argv = ["trace", "--service", "s", "--namespace", "n", "--name", "x"]
    assert cli.main(argv) == cli.EXIT_USAGE
    assert tracecmd.ENDPOINT in capsys.readouterr().err


def test_get_refuses_a_non_http_url_and_names_an_unreachable_endpoint() -> None:
    """The reader refuses a non-http URL and names a dead port, as the poster does."""
    with pytest.raises(sender.SendError, match="not an http"):
        sender.get("file:///etc/passwd")
    with _store() as (base, _):
        pass
    with pytest.raises(sender.SendError, match="cannot reach"):
        sender.get(base + tracecmd.JAEGER_PATH + "x")


def test_explicit_ids_and_times_are_sent_as_given(capsys: pytest.CaptureFixture[str]) -> None:
    """A span for something that already happened keeps its own ids, parent and nanosecond times."""
    trace, span, parent = "ab" * 16, "cd" * 8, "ef" * 8
    start, end = 1_760_000_000_000_000_000, 1_760_000_002_000_000_000
    given = ["--trace-id", trace, "--span-id", span, "--parent-id", parent]
    given += ["--start-ns", str(start), "--end-ns", str(end)]
    with _store() as (base, state):
        assert cli.main(_argv(base, *given)) == tracecmd.EXIT_SENT
    doc = MessageToDict(ExportTraceServiceRequest.FromString(state.posts[0][1]))
    resource = cast("list[Doc]", doc["resourceSpans"])[0]
    sent = cast("list[Doc]", cast("list[Doc]", resource["scopeSpans"])[0]["spans"])[0]
    assert base64.b64decode(cast("str", sent["traceId"])).hex() == trace
    assert base64.b64decode(cast("str", sent["spanId"])).hex() == span
    assert base64.b64decode(cast("str", sent["parentSpanId"])).hex() == parent
    assert (sent["startTimeUnixNano"], sent["endTimeUnixNano"]) == (str(start), str(end))
    assert f"trace_id={trace}" in capsys.readouterr().out


def test_a_malformed_id_is_a_usage_refusal_and_nothing_is_sent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The control: a 4-byte trace id never reaches the store; the builder's reason is printed."""
    with _store() as (base, state):
        assert cli.main(_argv(base, "--trace-id", "abcdef01")) == tracecmd.EXIT_USAGE
    assert not state.posts
    assert "trace_id must be 16 bytes" in capsys.readouterr().err

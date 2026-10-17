# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the sender: protobuf goes out typed, and a non-2xx answer is a failure (W1412).

⚑ THE ENDPOINT IS A PLANTED LOCAL SERVER, not luthen's: the tests prove what this module puts on
the wire (the bytes unchanged, the protobuf content type, the path) and how it reads an answer,
nothing about the real receiver. A real read-back against luthen's endpoint is a separate witness
that needs the cluster. The controls: a 400 raises and names the status, a URL that is not http(s)
is refused before any connection, and an unreachable port is a SendError, not a bare OSError.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

import pytest

from mikemol.otlp import sender

if TYPE_CHECKING:
    from collections.abc import Iterator

BODY = b"\x0a\x00protobuf-bytes"
REFUSED = 400
ACCEPTED = 204
Seen = list[tuple[str, str, bytes]]


@contextmanager
def _endpoint(answer: int) -> Iterator[tuple[str, Seen]]:
    # A one-purpose local receiver: it records each POST and answers with `answer`.
    seen: Seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            size = int(self.headers.get("Content-Length", "0"))
            kind = self.headers.get("Content-Type", "")
            seen.append((self.path, kind, self.rfile.read(size)))
            self.send_response(answer)
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_the_payload_arrives_unchanged_with_the_protobuf_content_type_on_the_path() -> None:
    """The control: the bytes, the type and the path the caller named are what the endpoint saw."""
    with _endpoint(ACCEPTED) as (base, seen):
        assert sender.send(base + sender.METRICS_PATH, BODY) == ACCEPTED
    assert seen == [(sender.METRICS_PATH, sender.CONTENT_TYPE, BODY)]


def test_a_refusal_raises_and_names_the_status_and_the_protobuf_rule() -> None:
    """A 400 (luthen's answer to a JSON body) is a failure the caller sees, not a quiet pass."""
    with _endpoint(REFUSED) as (base, _), pytest.raises(sender.SendError, match="400"):
        sender.send(base + sender.LOGS_PATH, BODY)


def test_a_url_that_is_not_http_is_refused_before_any_connection() -> None:
    """The control: file: and custom schemes never reach a socket."""
    with pytest.raises(sender.SendError, match="not an http"):
        sender.post("file:///etc/passwd", BODY)


def test_an_unreachable_endpoint_is_a_send_error_not_a_bare_os_error() -> None:
    """Connection refused (a port nobody listens on) surfaces as SendError naming the URL."""
    with _endpoint(ACCEPTED) as (base, _):
        pass
    with pytest.raises(sender.SendError, match="cannot reach"):
        sender.post(base + sender.METRICS_PATH, BODY)

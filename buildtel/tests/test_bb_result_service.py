# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""bb_result asks the service for one label and downloads a blob, on a local stand-in (W1750)."""

from __future__ import annotations

import http.server
import json
import threading
import urllib.parse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import bb_result

if TYPE_CHECKING:
    from collections.abc import Iterator

_HOST = "127.0.0.1"
_URI = "bytestream://x/blobs/ab/12"


@dataclass
class _Service:
    """A local stand-in for BuildBuddy's web service: what it was sent, what it answers."""

    port: int = 0
    status: int = 200
    body: bytes = b"{}"
    posts: list[tuple[str, dict[str, object]]] = field(default_factory=list)
    gets: list[tuple[str, dict[str, str]]] = field(default_factory=list)


@pytest.fixture()
def service() -> Iterator[_Service]:
    """Serve one local HTTP endpoint that records each POST and GET and answers with `body`.

    Yields:
        the service handle, its `port` filled in.

    """
    state = _Service()

    class Handler(http.server.BaseHTTPRequestHandler):
        def _answer(self) -> None:
            self.send_response(state.status)
            self.send_header("Content-Length", str(len(state.body)))
            self.end_headers()
            self.wfile.write(state.body)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            sent: object = json.loads(self.rfile.read(length))
            if isinstance(sent, dict):
                state.posts.append((self.path, {str(k): v for k, v in sent.items()}))
            self._answer()

        def do_GET(self) -> None:
            parts = urllib.parse.urlsplit(self.path)
            query = {k: v[0] for k, v in urllib.parse.parse_qs(parts.query).items()}
            state.gets.append((parts.path, query))
            self._answer()

    server = http.server.ThreadingHTTPServer((_HOST, 0), Handler)
    state.port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


def test_post_target_asks_get_target_for_the_invocation_and_the_label(service: _Service) -> None:
    """The body names the invocation id and the target label, and the answer is parsed."""
    service.body = b'{"targetGroups": []}'
    got = bb_result.post_target("inv-1", "//a:t", _HOST, service.port)
    assert got == {"targetGroups": []}
    assert service.posts == [
        (bb_result.RPC_TARGET, {"invocationId": "inv-1", "targetLabel": "//a:t"})
    ]


def test_download_sends_the_uri_the_invocation_and_the_file_name_and_returns_the_text(
    service: _Service,
) -> None:
    """The three query keys the web UI sends, and the blob's text back."""
    service.body = b"7 passed in 0.1s\n"
    got = bb_result.download("inv-1", _URI, "test.log", _HOST, service.port)
    assert got == "7 passed in 0.1s\n"
    sent = {"bytestream_url": _URI, "invocation_id": "inv-1", "filename": "test.log"}
    assert service.gets == [(bb_result.DOWNLOAD, sent)]


def test_a_download_the_service_refuses_raises_so_the_command_reports_it(service: _Service) -> None:
    """Any status but 200 is an OSError, the way the POST side treats it."""
    service.status = 404
    with pytest.raises(OSError, match="HTTP 404"):
        bb_result.download("inv-1", _URI, "test.log", _HOST, service.port)

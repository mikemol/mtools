# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bazelprofile.get_file`: a 200's bytes are returned, any other status is named."""

from __future__ import annotations

import http.server
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import bazelprofile

if TYPE_CHECKING:
    from collections.abc import Iterator

_NOT_FOUND = 404


@dataclass
class _Service:
    """A local stand-in for BuildBuddy's file endpoint: what it was asked, what it answers."""

    port: int = 0
    status: int = 200
    body: bytes = b""
    paths: list[str] = field(default_factory=list)


@pytest.fixture()
def service() -> Iterator[_Service]:
    """Serve one local HTTP endpoint that records each GET path and answers with `body`.

    Yields:
        the service handle, its `port` filled in.

    """
    state = _Service()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            state.paths.append(self.path)
            self.send_response(state.status)
            self.send_header("Content-Length", str(len(state.body)))
            self.end_headers()
            self.wfile.write(state.body)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


def test_get_asks_for_the_path_and_returns_the_bytes_of_a_200(service: _Service) -> None:
    """The request path reaches the service unchanged and the body comes back byte for byte."""
    service.body = b"\x1f\x8bprofile"
    got = bazelprofile.get_file("/file/download?x=1", host="127.0.0.1", port=service.port)
    assert got == b"\x1f\x8bprofile"
    assert service.paths == ["/file/download?x=1"]


def test_get_refuses_any_status_but_200_naming_it(service: _Service) -> None:
    """A 404 for a profile the cache lost is an OSError with the status, never empty bytes."""
    service.status = _NOT_FOUND
    service.body = b"no such file"
    with pytest.raises(OSError, match="HTTP 404"):
        bazelprofile.get_file("/file/download?x=1", host="127.0.0.1", port=service.port)

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a batch reaches a fake ingest, a refusal comes back as a fact, and names resolve.

W1167. ⚑ THE FAKE ENDPOINT IS A REAL HTTP SERVER on a loopback port chosen by the kernel, so the
request line, query and body are read as the server received them, not as the client meant them.
⚑ THE REFUSING AND THE DEAD ENDPOINTS ARE THE CONTROLS: a 503 and a connection nobody answers must
each report not-taken with a reason, or "taken" has stopped meaning anything.
⚑ NO ADDRESS IS LITERAL IN THE TEST EITHER: hosts are `localhost` and the port is read back.
"""

from __future__ import annotations

import http.server
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from mikemol.hooks import vlogsink

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

_ACCEPTED = 204
_REFUSED = 503
_LINES = ['{"_msg": "a"}', '{"_msg": "b"}']


class _Server(http.server.ThreadingHTTPServer):
    """A fake ingest: records each POST and answers with a fixed status."""

    def __init__(self, status: int) -> None:
        super().__init__(("localhost", 0), _Ingest)
        self.status = status
        self.seen: list[tuple[str, str, bytes]] = []


class _Ingest(http.server.BaseHTTPRequestHandler):
    """Record what arrived and answer with the server's status."""

    def do_POST(self) -> None:
        server = cast("_Server", self.server)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        server.seen.append((self.path, self.headers.get("Content-Type", ""), body))
        self.send_response(server.status)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        """Say nothing: the server's record is `seen`."""


@contextmanager
def _serving(status: int) -> Iterator[_Server]:
    """Serve on a kernel-chosen loopback port until the block ends.

    Yields:
        the running fake ingest.

    """
    server = _Server(status)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def _url(server: _Server) -> str:
    return f"http://localhost:{server.server_address[1]}"


def test_ingest_url_names_the_message_time_and_stream_fields() -> None:
    """The query tells the endpoint which fields are which; a trailing slash is not doubled."""
    url = vlogsink.ingest_url("http://store/", ["tool", "repo"])
    assert url == (
        "http://store/insert/jsonline?_msg_field=_msg&_time_field=_time&_stream_fields=tool,repo"
    )


def test_an_accepting_ingest_receives_the_lines_as_the_server_saw_them() -> None:
    """The path and query, the content type and the body: one JSON line each, newline-ended."""
    with _serving(_ACCEPTED) as server:
        url = vlogsink.ingest_url(_url(server), ["tool"])
        got = vlogsink.post(url, _LINES)
    assert got.ok
    assert got.status == _ACCEPTED
    path, content_type, body = server.seen[0]
    assert path.startswith("/insert/jsonline?")
    assert content_type == vlogsink.CONTENT_TYPE
    assert body == b'{"_msg": "a"}\n{"_msg": "b"}\n'


def test_a_refusing_ingest_is_not_taken_and_says_why() -> None:
    """The control: a 503 is a Posted with ok False, the status, and a reason; nothing raises."""
    with _serving(_REFUSED) as server:
        got = vlogsink.post(vlogsink.ingest_url(_url(server), ["tool"]), _LINES)
    assert not got.ok
    assert got.status == _REFUSED
    assert got.reason


def test_a_connection_nobody_answers_is_status_zero_with_a_reason() -> None:
    """Take a port from the kernel, close it unserved, post to it: refused by the OS."""
    server = _Server(_ACCEPTED)
    url = _url(server)
    server.server_close()
    got = vlogsink.post(f"{url}/insert/jsonline", _LINES)
    assert not got.ok
    assert got.status == 0
    assert got.reason


def test_a_scheme_that_is_not_http_is_refused_without_opening_anything() -> None:
    """A `file:` URL must never be opened by an ingest client."""
    got = vlogsink.post("file:///nowhere", _LINES)
    assert not got.ok
    assert got.status == 0
    assert "scheme" in got.reason


def _resolver(status: int, out: str, seen: list[Sequence[str]]) -> vlogsink.Resolver:
    """Build a resolver that records its argv and answers fixed.

    Returns:
        the resolver callable.

    """

    def run(argv: Sequence[str]) -> tuple[int, str]:
        seen.append(list(argv))
        return status, out

    return run


def test_resolve_substitutes_the_name_into_one_argv_element_and_takes_the_first_line() -> None:
    """A name with spaces and a semicolon stays ONE argument; only the first output line counts."""
    seen: list[Sequence[str]] = []
    base = vlogsink.resolve(
        "a b; c", ["endpoints_query", "{name}"], _resolver(0, "\nhttp://store\nignored\n", seen)
    )
    assert base == "http://store"
    assert seen == [["endpoints_query", "a b; c"]]


def test_resolve_is_none_for_no_template_a_failing_resolver_or_an_empty_answer() -> None:
    """Each way of not knowing the endpoint says None, so the lines stay in the spool."""
    seen: list[Sequence[str]] = []
    assert vlogsink.resolve("x", [], _resolver(0, "http://store", seen)) is None
    assert not seen
    assert vlogsink.resolve("x", ["q", "{name}"], _resolver(1, "http://store", seen)) is None
    assert vlogsink.resolve("x", ["q", "{name}"], _resolver(0, "  \n", seen)) is None

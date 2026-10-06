# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bb_log.post`: one chunk asked for and decoded, a bad answer never a log."""

from __future__ import annotations

import base64
import http.server
import json
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import bb_log

if TYPE_CHECKING:
    from collections.abc import Iterator

_SERVER_ERROR = 500


@dataclass
class _Service:
    """A local stand-in for BuildBuddy's web service: what it was sent, what it answers."""

    port: int = 0
    status: int = 200
    answer: object = field(default_factory=dict)
    seen: list[tuple[str, dict[str, object]]] = field(default_factory=list)


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


def _chunk(text: str, following: str) -> dict[str, str]:
    """Build the chunk BuildBuddy answers with: base64 text and the next chunk id.

    Returns:
        the response body.

    """
    return {"buffer": base64.b64encode(text.encode()).decode(), "nextChunkId": following}


def test_post_asks_for_the_chunk_and_returns_its_text_and_next_id(service: _Service) -> None:
    """The body names the invocation and chunk, the path is the RPC, and the answer is decoded."""
    service.answer = _chunk("INFO: built\n", "0002")
    text, following = bb_log.post("inv-1", "0001", host="127.0.0.1", port=service.port)
    assert (text, following) == ("INFO: built\n", "0002")
    path, body = service.seen[0]
    assert path == bb_log.RPC
    assert body == {"invocationId": "inv-1", "chunkId": "0001", "minLines": bb_log.MIN_LINES}


def test_post_decodes_undecodable_bytes_by_replacing_them(service: _Service) -> None:
    """A log with a stray byte is still readable: the byte is replaced, the rest kept."""
    broken = base64.b64encode(b"ok \xff end\n").decode()
    service.answer = {"buffer": broken, "nextChunkId": ""}
    text, _following = bb_log.post("inv-1", "", host="127.0.0.1", port=service.port)
    assert text.startswith("ok ")
    assert text.endswith(" end\n")


def test_post_refuses_any_status_but_200_naming_it(service: _Service) -> None:
    """A 500 for an unknown invocation is an OSError with the status, never an empty log."""
    service.status = _SERVER_ERROR
    service.answer = {"message": "invocation not found"}
    with pytest.raises(OSError, match="HTTP 500"):
        bb_log.post("inv-1", "", host="127.0.0.1", port=service.port)


def test_post_refuses_an_answer_that_is_not_a_chunk(service: _Service) -> None:
    """A list, a non-text buffer and bad base64 are each an OSError, never an empty log."""
    answers: list[object] = [[], {"buffer": 5, "nextChunkId": ""}, {"buffer": "abcde"}]
    for answer in answers:
        service.answer = answer
        with pytest.raises(OSError, match=r"object|chunk|base64"):
            bb_log.post("inv-1", "", host="127.0.0.1", port=service.port)

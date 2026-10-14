# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses of the shipper core: spool first, drain by name, keep what is refused, replay.

W1177. ⚑ THE FAKE INGEST IS A REAL HTTP SERVER (as in test_vlogsink), so the stream fields are read
from the query the server received. ⚑ THE REFUSING SERVER AND THE UNRESOLVED NAME ARE THE CONTROLS,
and a SECOND `drain_all` after the endpoint "comes back" is the restart: the replay is read from
the spool directory, not from state held by the first call.
"""

from __future__ import annotations

import http.server
import json
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from mikemol.hooks import vlogrecord, vlogship

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

_ACCEPTED = 204
_REFUSED = 503
_NOW = "2026-10-14T00:00:00.000000Z"
_TWO = 2
_STREAMS = {"tool": "commit", "repo": "mtools"}
Doc = dict[str, object]


class _Server(http.server.ThreadingHTTPServer):
    """A fake ingest: records each POST and answers with a status that can change."""

    def __init__(self, status: int) -> None:
        super().__init__(("localhost", 0), _Ingest)
        self.status = status
        self.seen: list[tuple[str, bytes]] = []


class _Ingest(http.server.BaseHTTPRequestHandler):
    """Record what arrived and answer with the server's current status."""

    def do_POST(self) -> None:
        server = cast("_Server", self.server)
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        server.seen.append((self.path, body))
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


def _doc(line: str) -> Doc:
    return cast("Doc", json.loads(line))


def _config(tmp_path: Path, port: int | None = None, max_lines: int = 1000) -> vlogship.Config:
    """Build a config whose resolver prints the fake's base URL (or nothing, with no port).

    Returns:
        the config.

    """
    answer = f"http://localhost:{port}" if port is not None else ""
    template = ("resolve-fake", "{name}", answer)
    return vlogship.Config(tmp_path / "spool", "logs", template, max_lines, 1 << 20)


def _resolver(argv: Sequence[str]) -> tuple[int, str]:
    """Answer like a resolver: the last argument is what it prints.

    Returns:
        status 0 and that text.

    """
    return 0, argv[-1]


def _ship(config: vlogship.Config, lines: list[str], streams: dict[str, str] | None = None) -> None:
    vlogship.ship(lines, streams or _STREAMS, vlogrecord.FieldMap(), config, lambda: _NOW)


def test_lines_are_spooled_to_a_file_named_for_the_sorted_stream_keys(tmp_path: Path) -> None:
    """Two key sets make two spools; blank lines are skipped; fields and streams are kept."""
    config = _config(tmp_path)
    _ship(config, ['{"message": "a", "sha": "1"}', "", "plain text"])
    _ship(config, ['{"message": "b"}'], {"zone": "x"})
    names = sorted(p.name for p in (tmp_path / "spool").glob("vlog-*.spool"))
    assert names == sorted([vlogship.spool_name(["repo", "tool"]), vlogship.spool_name(["zone"])])
    first = (tmp_path / "spool" / vlogship.spool_name(["tool", "repo"])).read_text(encoding="utf-8")
    records = [_doc(line) for line in first.splitlines()]
    assert [r["_msg"] for r in records] == ["a", "plain text"]
    assert records[0]["sha"] == "1"
    assert records[1]["parse_failure"] == "not-json"
    assert records[0]["repo"] == "mtools"


def test_a_drain_posts_each_spool_with_its_own_stream_fields_and_empties_it(
    tmp_path: Path,
) -> None:
    """The query carries the keys read back from the file name; nothing is left."""
    with _serving(_ACCEPTED) as server:
        config = _config(tmp_path, server.server_address[1])
        _ship(config, ['{"message": "a"}', '{"message": "b"}'])
        got = vlogship.drain_all(config, resolver=_resolver)
    assert (got.sent, got.left, got.reason) == (_TWO, 0, "")
    path, body = server.seen[0]
    assert "_stream_fields=repo,tool" in path
    assert [_doc(line)["_msg"] for line in body.decode().splitlines()] == ["a", "b"]


def test_a_refusing_ingest_leaves_the_spool_and_a_restart_replays_it_in_order(
    tmp_path: Path,
) -> None:
    """503: nothing is lost and the reason names the status; the next drain sends it all."""
    with _serving(_REFUSED) as server:
        config = _config(tmp_path, server.server_address[1])
        _ship(config, ['{"message": "a"}', '{"message": "b"}'])
        refused = vlogship.drain_all(config, resolver=_resolver)
        assert (refused.sent, refused.left) == (0, _TWO)
        assert str(_REFUSED) in refused.reason
        server.status = _ACCEPTED
        replayed = vlogship.drain_all(config, resolver=_resolver)
    assert (replayed.sent, replayed.left) == (_TWO, 0)
    last_body = server.seen[-1][1].decode().splitlines()
    assert [_doc(line)["_msg"] for line in last_body] == ["a", "b"]


def test_no_service_or_an_unresolved_name_leaves_the_spool_and_says_no_destination(
    tmp_path: Path,
) -> None:
    """The caller named nothing, then the resolver gave nothing: both keep every line."""
    unnamed = vlogship.Config(tmp_path / "spool", None, (), 1000, 1 << 20)
    _ship(unnamed, ['{"message": "a"}'])
    first = vlogship.drain_all(unnamed, resolver=_resolver)
    assert (first.sent, first.left) == (0, 1)
    assert "no destination" in first.reason
    blank = _config(tmp_path)
    second = vlogship.drain_all(blank, resolver=_resolver)
    assert (second.sent, second.left) == (0, 1)
    assert "no destination" in second.reason


def _holding(tmp_path: Path, max_lines: int) -> vlogship.Config:
    """Build a config whose spool holds at most `max_lines` and whose policy is `hold`.

    Returns:
        the config.

    """
    return vlogship.Config(tmp_path / "spool", None, (), max_lines, 1 << 20, "hold")


def _held(config: vlogship.Config, lines: list[str]) -> vlogship.Shipped:
    return vlogship.ship(lines, _STREAMS, vlogrecord.FieldMap(), config, lambda: _NOW)


def test_hold_spools_what_fits_reports_the_rest_and_counts_input_lines_consumed(
    tmp_path: Path,
) -> None:
    """Five lines with a blank, room for two: a and b go, c and d are held, three were consumed."""
    got = _held(_holding(tmp_path, _TWO), ["a", "", "b", "c", "d"])
    assert (got.spooled, got.dropped, got.held, got.consumed) == (_TWO, 0, _TWO, 3)
    spool = vlogship.spool_for(_holding(tmp_path, _TWO), list(_STREAMS))
    kept: list[str] = []

    def take(lines: list[str]) -> bool:
        kept.extend(lines)
        return True

    spool.drain(take)
    assert [_doc(line)["_msg"] for line in kept] == ["a", "b"]


def test_hold_with_room_for_everything_consumes_every_input_line(tmp_path: Path) -> None:
    """The control: nothing is held, and a trailing blank line counts as consumed."""
    got = _held(_holding(tmp_path, 10), ["a", "b", ""])
    assert (got.spooled, got.held, got.consumed) == (_TWO, 0, _TWO + 1)


def test_hold_into_a_full_spool_consumes_nothing(tmp_path: Path) -> None:
    """No room at all: nothing spooled, everything held, zero lines consumed, no gap record."""
    config = _holding(tmp_path, 1)
    _held(config, ["first"])
    got = _held(config, ["x", "y"])
    assert (got.spooled, got.held, got.consumed, got.dropped) == (0, _TWO, 0, 0)


def test_a_ceiling_that_dropped_lines_is_itself_recorded(tmp_path: Path) -> None:
    """Four lines into a spool of two: two are dropped and one record says how many, once."""
    config = _config(tmp_path, max_lines=_TWO + 1)
    shipped = vlogship.ship(
        ["1", "2", "3", "4"], _STREAMS, vlogrecord.FieldMap(), config, lambda: _NOW
    )
    assert shipped.dropped == 1
    spool = vlogship.spool_for(config, list(_STREAMS))
    kept: list[str] = []

    def take(lines: list[str]) -> bool:
        kept.extend(lines)
        return True

    spool.drain(take)
    gap = [d for d in (_doc(line) for line in kept) if "dropped" in d]
    assert len(gap) == 1
    assert gap[0]["dropped"] == 1
    assert gap[0]["repo"] == "mtools"

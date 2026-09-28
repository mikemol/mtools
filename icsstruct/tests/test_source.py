# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the source edge: a planted secret URL reaches no record, label or error.

The remote cases are served from a loopback server or a stub transport. Nothing here touches the
network, and the calendars are life's synthetic fixtures.
"""

from __future__ import annotations

import functools
import http.server
import threading
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.icsstruct.source import SourceError, read, url_label

if TYPE_CHECKING:
    from collections.abc import Iterator

_FIXTURES = Path(__file__).parent / "fixtures"
_PLANTED = "S3CR3T-PLANTED-TOKEN"
_PRIVATE = f"/calendar/ical/private-{_PLANTED}/basic.ics"
_NAMELESS = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
_HASH_HEX = 12


@pytest.fixture()
def origin(tmp_path: Path) -> Iterator[str]:
    """Serve fixture 01 at the private path from a loopback server, for one test.

    ⚑ The stdlib's own file handler, rooted at a temporary directory: anything else is a 404.

    Yields:
        the server's base URL.

    """
    served = tmp_path / _PRIVATE.lstrip("/")
    served.parent.mkdir(parents=True)
    served.write_bytes((_FIXTURES / "01-weekly-rrule-exdate.ics").read_bytes())
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def _printed(err: BaseException) -> str:
    """Render an exception the way an uncaught one is printed.

    Returns:
        the traceback text.

    """
    return "".join(traceback.format_exception(err))


def test_remote_source_is_labelled_by_its_calname_and_holds_no_url(origin: str) -> None:
    """A real GET of the private URL yields the text, labelled `Synthetic Weekly`."""
    source = read(origin + _PRIVATE)
    assert source.label == "Synthetic Weekly"
    assert source.text.startswith("BEGIN:VCALENDAR")
    assert _PLANTED not in repr(source)


def test_remote_source_without_a_calname_is_labelled_by_hash() -> None:
    """With no X-WR-CALNAME the label is `url:` and 12 hex digits, and not the URL."""
    url = "https://calendar.invalid" + _PRIVATE
    source = read(url, lambda _: _NAMELESS)
    assert source.label == url_label(url)
    assert len(source.label.removeprefix("url:")) == _HASH_HEX
    assert _PLANTED not in repr(source)


def test_http_status_error_names_the_label_not_the_url(origin: str) -> None:
    """A 404 from the server is a `SourceError` carrying the label and the status only."""
    url = origin + _PRIVATE.replace("basic", "missing")
    with pytest.raises(SourceError) as caught:
        read(url)
    assert str(caught.value) == f"{url_label(url)}: fetch failed: HTTP 404"
    assert _PLANTED not in _printed(caught.value)


def test_transport_error_text_is_not_propagated() -> None:
    """A transport error that embeds the URL is rewritten, and its text is not chained.

    ⚑ Raised `from None`: neither `__cause__` nor the printed context carries the original.
    """
    url = "https://calendar.invalid" + _PRIVATE

    def refuse(target: str) -> bytes:
        msg = f"cannot reach {target}"
        raise ConnectionRefusedError(msg)

    with pytest.raises(SourceError) as caught:
        read(url, refuse)
    assert str(caught.value) == f"{url_label(url)}: fetch failed: ConnectionRefusedError"
    assert caught.value.__cause__ is None
    assert _PLANTED not in _printed(caught.value)


def test_webcal_is_fetched_as_https_and_labelled_by_what_was_given() -> None:
    """`webcal://` goes out as `https://`; the label hashes the location the caller gave."""
    url = "webcal://calendar.invalid" + _PRIVATE
    asked: list[str] = []

    def record(target: str) -> bytes:
        asked.append(target)
        return _NAMELESS

    source = read(url, record)
    assert asked == ["https://calendar.invalid" + _PRIVATE]
    assert source.label == url_label(url)


def test_non_utf8_source_is_refused_by_label() -> None:
    """RFC 5545 requires UTF-8; other bytes are a `SourceError`, not a lossy decode."""
    url = "https://calendar.invalid" + _PRIVATE
    with pytest.raises(SourceError) as caught:
        read(url, lambda _: b"\xff\xfe")
    assert str(caught.value) == f"{url_label(url)}: not UTF-8"


def test_path_source_is_read_and_labelled() -> None:
    """A path is not a credential: it labels itself unless the calendar names itself."""
    path = _FIXTURES / "03-all-day.ics"
    source = read(str(path))
    assert source.label == "Synthetic All-Day"
    assert source.text == path.read_bytes().decode("utf-8")
    missing = str(_FIXTURES / "absent.ics")
    with pytest.raises(SourceError) as caught:
        read(missing)
    assert str(caught.value) == f"{missing}: FileNotFoundError"

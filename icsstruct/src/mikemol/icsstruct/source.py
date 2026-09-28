# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a calendar source once, and keep a label for it, never its URL.

⚑⚑ A SECRET CALENDAR URL IS A CREDENTIAL (.claude/design/W247-icsstruct.md). Google's "secret
address in iCal format" grants read access to anyone holding the string. So the URL is redacted at
the edge: `read` returns a `Source` holding the text and a label, and nothing it returns or raises
holds the URL. The label is the calendar's own `X-WR-CALNAME` when it has one, else
`url:<first 12 hex of sha256(url)>`, which is stable across runs and reveals nothing.

⚑ FETCH ERRORS ARE REWRITTEN, NOT WRAPPED. A urllib or socket error can embed the host or the whole
URL in its text. `SourceError` carries the label and the error's type name or HTTP status only,
and is raised `from None`, so the original is neither its cause nor its printed context.

⚑ `http.client`, NOT `urllib.request.urlopen`: typeshed types urlopen's return as `Any`, which
the strict block refuses at every call site. `http.client` is typed, and it follows no redirect: a
redirect is a status, reported as one.
"""

from __future__ import annotations

import hashlib
import http.client
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.icsstruct.lexical import ContentLine, lex

if TYPE_CHECKING:
    from collections.abc import Callable

_REMOTE = frozenset({"http", "https", "webcal"})
_TIMEOUT = 30.0
_OK = 200


@dataclass(frozen=True, slots=True)
class Source:
    """A calendar's text and its label. It holds no URL."""

    label: str
    text: str


class SourceError(Exception):
    """A source could not be read. The message names the label, never the location."""


class _StatusError(OSError):
    """A fetch answered with a status other than 200."""

    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status


def _fetch(url: str) -> bytes:
    """GET `url` once over http or https, following no redirect.

    Returns:
        the response body.

    Raises:
        _StatusError: if the status is not 200.

    """
    parts = urllib.parse.urlsplit(url)
    connect = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    connection = connect(parts.netloc, timeout=_TIMEOUT)
    target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    try:
        connection.request("GET", target)
        response = connection.getresponse()
        body = response.read()
    finally:
        connection.close()
    if response.status != _OK:
        raise _StatusError(response.status)
    return body


def url_label(url: str) -> str:
    """Name a URL without revealing it.

    Returns:
        `url:` and the first 12 hex digits of its sha256.

    """
    return "url:" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def _calname(text: str) -> str | None:
    """Read the calendar's own `X-WR-CALNAME`, if it sits directly in the VCALENDAR.

    Returns:
        the name, or None.

    """
    for record in lex(text):
        if (
            isinstance(record, ContentLine)
            and record.name == "X-WR-CALNAME"
            and len(record.path) == 1
            and record.value
        ):
            return record.value
    return None


def _decode(data: bytes, label: str) -> str:
    """Decode a source as UTF-8, which RFC 5545 §3.1.4 requires.

    Returns:
        the text.

    Raises:
        SourceError: if it is not UTF-8.

    """
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        msg = f"{label}: not UTF-8"
        raise SourceError(msg) from None


def read(location: str, fetch: Callable[[str], bytes] = _fetch) -> Source:
    """Read an `.ics` path or an http, https or webcal URL, once.

    `webcal://` is fetched as `https://`. `fetch` is the transport; tests pass their own.

    Returns:
        the source, labelled by its X-WR-CALNAME, else by `url_label` or the path.

    Raises:
        SourceError: naming the label, if the source cannot be read.

    """
    scheme = urllib.parse.urlsplit(location).scheme.lower()
    if scheme in _REMOTE:
        label = url_label(location)
        target = "https" + location[len(scheme) :] if scheme == "webcal" else location
        try:
            data = fetch(target)
        except _StatusError as exc:
            msg = f"{label}: fetch failed: HTTP {exc.status}"
            raise SourceError(msg) from None
        except OSError as exc:
            msg = f"{label}: fetch failed: {type(exc).__name__}"
            raise SourceError(msg) from None
    else:
        label = location
        try:
            data = Path(location).read_bytes()
        except OSError as exc:
            msg = f"{label}: {type(exc).__name__}"
            raise SourceError(msg) from None
    text = _decode(data, label)
    return Source(_calname(text) or label, text)

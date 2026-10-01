# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Gmail API reads, narrowed into records, with the HTTP GET passed in (W357).

`search` walks `users.messages.list` pages and hands them to records.pages; `show` fetches one
`users.messages.get` (format=metadata) into records.message. Nothing is cached or logged.

⚑ A FAILED REQUEST IS AN ERROR, NEVER A SHORTER RESULT. A non-200 status raises FetchError naming
the status and which request, so a partial listing cannot pass as a complete one. A run that stops
at --max-pages while Google still offers a next page is reported by records.pages as truncated.

⚑ AN ID GOES INTO A URL PATH ONLY IF IT IS A PLAIN IDENTIFIER. Gmail message ids are hex; anything
else is refused before a request is made.
"""

from __future__ import annotations

import binascii
import json
from collections.abc import Callable
from typing import cast
from urllib.parse import urlencode

from mikemol.gmailstruct.records import (
    Listed,
    Message,
    Unreadable,
    decode_base64url,
    message,
    pages,
)

API = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
_OK = 200

# (url, access token) -> (HTTP status, body). The CLI supplies one that GETs; tests fake it.
type Getter = Callable[[str, str], tuple[int, bytes]]


class FetchError(Exception):
    """A Gmail request failed; the message names the status and the request, never a token."""


def _json(body: bytes) -> object:
    try:
        return cast("object", json.loads(body))
    except (ValueError, UnicodeDecodeError):
        return None


def search(query: str, access: str, get: Getter, max_pages: int) -> list[Listed | Unreadable]:
    """List the messages matching `query`, at most `max_pages` pages of them.

    Returns:
        records.pages over the pages fetched: one record per listed id, and a truncation record
        when the last page fetched still names a next one.

    Raises:
        FetchError: when a page request returns anything but 200.

    """
    values: list[object] = []
    token = ""
    for page_no in range(max_pages):
        params = {"q": query} | ({"pageToken": token} if token else {})
        status, body = get(f"{API}?{urlencode(params)}", access)
        if status != _OK:
            msg = f"listing page {page_no} failed: HTTP {status}"
            raise FetchError(msg)
        value = _json(body)
        values.append(value)
        fields = cast("dict[str, object]", value) if isinstance(value, dict) else {}
        following = fields.get("nextPageToken")
        if not isinstance(following, str) or not following:
            break
        token = following
    return pages(values)


def show(msg_id: str, access: str, get: Getter) -> Message | Unreadable:
    """Fetch one message's metadata.

    Returns:
        records.message over the response.

    Raises:
        FetchError: when the id is not a plain identifier, or the request returns anything but 200.

    """
    if not msg_id.isascii() or not msg_id.isalnum():
        msg = "a message id is letters and digits only"
        raise FetchError(msg)
    status, body = get(f"{API}/{msg_id}?{urlencode({'format': 'metadata'})}", access)
    if status != _OK:
        msg = f"fetching message {msg_id} failed: HTTP {status}"
        raise FetchError(msg)
    return message(_json(body))


def raw(msg_id: str, access: str, get: Getter) -> bytes:
    """Fetch one message as the exact RFC 822 bytes Gmail holds (format=raw).

    ⚑ THE BYTES ARE EVIDENCE. life's scripts/eml_summary.py hashes the .eml (W358), so nothing
    here normalizes, re-encodes or re-wraps them: they are the base64url Gmail returned, decoded
    strictly, and nothing else.

    Returns:
        the message bytes.

    Raises:
        FetchError: when the id is not a plain identifier, the request returns anything but 200,
            or the response has no `raw` field that decodes as base64url. No message quotes the
            body.

    """
    if not msg_id.isascii() or not msg_id.isalnum():
        msg = "a message id is letters and digits only"
        raise FetchError(msg)
    status, body = get(f"{API}/{msg_id}?{urlencode({'format': 'raw'})}", access)
    if status != _OK:
        msg = f"fetching message {msg_id} failed: HTTP {status}"
        raise FetchError(msg)
    value = _json(body)
    fields = cast("dict[str, object]", value) if isinstance(value, dict) else {}
    text = fields.get("raw")
    if not isinstance(text, str) or not text:
        msg = f"message {msg_id} came back with no raw field"
        raise FetchError(msg)
    try:
        return decode_base64url(text)
    except binascii.Error:
        msg = f"message {msg_id}'s raw field is not base64url"
        raise FetchError(msg) from None

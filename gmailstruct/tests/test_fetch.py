# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""fetch: Gmail reads become records, and a failed request is an error, never a shorter result."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from mikemol.gmailstruct.fetch import API, FetchError, search, show
from mikemol.gmailstruct.records import Listed, Message, Unreadable

_ACCESS = "ya29.synthetic-access"
_OK = 200
_FORBIDDEN = 403


def _dumps(value: object) -> bytes:
    return json.dumps(value).encode()


class _Gmail:
    """A Gmail stand-in: answers each GET from a list of responses, recording the requests."""

    def __init__(self, *responses: tuple[int, bytes]) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, str]] = []

    def __call__(self, url: str, access: str) -> tuple[int, bytes]:
        self.requests.append((url, access))
        return self.responses.pop(0)


def _query(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


_PAGE_ONE = _dumps({"messages": [{"id": "a1", "threadId": "t1"}], "nextPageToken": "p2"})
_PAGE_TWO = _dumps({"messages": [{"id": "b2", "threadId": "t2"}]})


def test_search_walks_pages_until_no_next_token() -> None:
    """Two pages, the second asked for with the first's token, give one record per listed id."""
    gmail = _Gmail((_OK, _PAGE_ONE), (_OK, _PAGE_TWO))
    assert search("from:ada", _ACCESS, gmail, 10) == [
        Listed("a1", "t1", 0, 0),
        Listed("b2", "t2", 1, 0),
    ]
    assert [_query(url) for url, _ in gmail.requests] == [
        {"q": "from:ada"},
        {"q": "from:ada", "pageToken": "p2"},
    ]
    assert {access for _, access in gmail.requests} == {_ACCESS}


def test_search_stopped_by_max_pages_reports_truncation() -> None:
    """A run cut off at --max-pages while Google offers a next page says it is truncated."""
    records = search("x", _ACCESS, _Gmail((_OK, _PAGE_ONE)), 1)
    assert records[0] == Unreadable(id=None, reason="page 0 has nextPageToken: listing truncated")
    assert records[1:] == [Listed("a1", "t1", 0, 0)]


def test_failed_page_is_an_error_not_a_shorter_listing() -> None:
    """A page that fails after one that succeeded raises, rather than returning page one alone."""
    gmail = _Gmail((_OK, _PAGE_ONE), (_FORBIDDEN, b"denied"))
    with pytest.raises(FetchError, match="page 1 failed: HTTP 403"):
        search("x", _ACCESS, gmail, 10)


def test_show_fetches_metadata_for_one_message() -> None:
    """One GET to messages/<id> with format=metadata, narrowed by records.message."""
    body = {
        "id": "a1",
        "threadId": "t1",
        "internalDate": "1",
        "payload": {"headers": [{"name": "Subject", "value": "Hi"}]},
    }
    gmail = _Gmail((_OK, _dumps(body)))
    assert show("a1", _ACCESS, gmail) == Message("a1", "t1", (), "", 1, (("Subject", "Hi"),))
    [(url, _)] = gmail.requests
    assert url.startswith(f"{API}/a1?")
    assert _query(url) == {"format": "metadata"}


@pytest.mark.parametrize("bad", ["../x", "a1?format=raw", "", "a 1"])
def test_show_refuses_an_id_that_is_not_an_identifier(bad: str) -> None:
    """An id that could alter the URL is refused before any request is made."""
    gmail = _Gmail()
    with pytest.raises(FetchError, match="letters and digits"):
        show(bad, _ACCESS, gmail)
    assert gmail.requests == []


def test_failed_show_names_the_status() -> None:
    """A message that cannot be fetched is an error naming the id and the status."""
    with pytest.raises(FetchError, match="a1 failed: HTTP 403"):
        show("a1", _ACCESS, _Gmail((_FORBIDDEN, b"")))

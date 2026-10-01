# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""auth.exchange: refresh token to access token in memory, and no failure carries a token."""

from __future__ import annotations

import json
import traceback

import pytest

from mikemol.gmailstruct.auth import OAUTH_ENDPOINT, ExchangeError, Poster, exchange

# ⚑ SYNTHETIC: planted values, so a test can look for them where they must not be.
_REFRESH = "1//planted-refresh-token-0f2a"
_SECRET = "planted-client-secret-77c1"
_ACCESS = "ya29.planted-access-token-91be"
_CLIENT = "123.apps.googleusercontent.com"
_OK = 200
_BAD_REQUEST = 400


class _Fake:
    """A poster that records each request and answers with a fixed response."""

    def __init__(self, status: int, body: bytes) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.response = (status, body)

    def __call__(self, url: str, form: dict[str, str]) -> tuple[int, bytes]:
        self.calls.append((url, form))
        return self.response


def _exchange(post: Poster) -> tuple[str, int]:
    return exchange(_REFRESH, _CLIENT, _SECRET, post)


def _body(value: object) -> bytes:
    return json.dumps(value).encode()


def _rendered(err: BaseException) -> str:
    return "".join(traceback.format_exception(err))


def test_access_token_is_returned_with_its_lifetime() -> None:
    """The positive control: a 200 with both fields gives the token and its lifetime, in memory."""
    fake = _Fake(_OK, _body({"access_token": _ACCESS, "expires_in": 3599, "token_type": "Bearer"}))
    assert _exchange(fake) == (_ACCESS, 3599)


def test_request_is_the_refresh_grant_to_googles_endpoint() -> None:
    """One POST to the token endpoint, carrying the refresh-token grant and the client pair."""
    fake = _Fake(_OK, _body({"access_token": _ACCESS, "expires_in": 1}))
    _exchange(fake)
    assert fake.calls == [
        (
            OAUTH_ENDPOINT,
            {
                "grant_type": "refresh_token",
                "refresh_token": _REFRESH,
                "client_id": _CLIENT,
                "client_secret": _SECRET,
            },
        ),
    ]


def test_refused_grant_names_the_oauth_error_and_no_secret() -> None:
    """A 400 names its status and OAuth code; an echoed body never reaches the traceback."""
    echoed = {"error": "invalid_grant", "error_description": f"{_REFRESH} {_SECRET} expired"}
    with pytest.raises(ExchangeError) as caught:
        _exchange(_Fake(_BAD_REQUEST, _body(echoed)))
    assert "HTTP 400, invalid_grant" in str(caught.value)
    for planted in (_REFRESH, _SECRET):
        assert planted not in _rendered(caught.value)


def test_error_code_that_is_not_an_identifier_is_not_quoted() -> None:
    """Only a plain code is quoted; an error field carrying anything else reads as unreadable."""
    with pytest.raises(ExchangeError, match="unreadable") as caught:
        _exchange(_Fake(_BAD_REQUEST, _body({"error": _REFRESH})))
    assert _REFRESH not in _rendered(caught.value)


def test_success_without_both_fields_is_an_error() -> None:
    """A 200 lacking access_token or expires_in is refused, never returned half-formed."""
    halves: tuple[object, ...] = (
        {"access_token": _ACCESS},
        {"expires_in": 5},
        [],
        {"access_token": ""},
    )
    for value in halves:
        with pytest.raises(ExchangeError, match="no access_token"):
            _exchange(_Fake(_OK, _body(value)))


def test_non_json_success_is_an_error_carrying_none_of_it() -> None:
    """A 200 whose body is not JSON is refused, and the decode error is not chained."""
    with pytest.raises(ExchangeError) as caught:
        _exchange(_Fake(_OK, b"<html>" + _ACCESS.encode()))
    assert caught.value.__cause__ is None
    assert _ACCESS not in _rendered(caught.value)

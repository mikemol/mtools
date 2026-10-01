# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""consent: the refresh token reaches only `encrypt`, and no failure carries a secret."""

from __future__ import annotations

import base64
import hashlib
import json
import traceback
from urllib.parse import parse_qs, urlsplit

import pytest

from mikemol.gmailstruct.auth import OAUTH_ENDPOINT
from mikemol.gmailstruct.consent import SCOPE, ConsentError, consent, pkce, read_client

# ⚑ SYNTHETIC: planted values, so a test can look for them where they must not be.
_SECRET = "planted-client-secret-77c1"
_REFRESH = "1//planted-refresh-token-0f2a"
_CODE = "4/planted-auth-code-5d3e"
_CLIENT = "123.apps.googleusercontent.com"
_REDIRECT = "http://127.0.0.1:8765"
_OK = 200
_BAD_REQUEST = 400


def _dumps(value: object) -> str:
    return json.dumps(value)


_CLIENT_JSON = _dumps({"installed": {"client_id": _CLIENT, "client_secret": _SECRET}})


class _Run:
    """Every effect of one consent run, faked and recorded."""

    def __init__(self, status: int = _OK, body: bytes = b"", *, tamper: bool = False) -> None:
        self.counter = 0
        self.opened: list[str] = []
        self.posted: list[tuple[str, dict[str, str]]] = []
        self.encrypted: list[str] = []
        self.response = (status, body or _dumps({"refresh_token": _REFRESH}).encode())
        self.tamper = tamper

    def random(self, n: int) -> bytes:
        self.counter += 1
        return bytes([self.counter]) * n

    def browser(self, url: str) -> None:
        self.opened.append(url)

    def await_code(self) -> tuple[str, str]:
        state = parse_qs(urlsplit(self.opened[-1]).query)["state"][0]
        return _CODE, ("forged" if self.tamper else state)

    def post(self, url: str, form: dict[str, str]) -> tuple[int, bytes]:
        self.posted.append((url, form))
        return self.response

    def encrypt(self, token: str) -> None:
        self.encrypted.append(token)

    def go(self, client_text: str = _CLIENT_JSON) -> None:
        effects = (self.random, self.browser, self.await_code, self.post, self.encrypt)
        consent(client_text, _REDIRECT, effects)


def _rendered(err: BaseException) -> str:
    return "".join(traceback.format_exception(err))


def test_refresh_token_reaches_only_encrypt() -> None:
    """The positive control: one consent page, one code POST, and the token handed to encrypt."""
    run = _Run()
    run.go()
    assert run.encrypted == [_REFRESH]
    [(url, form)] = run.posted
    assert url == OAUTH_ENDPOINT
    assert form["grant_type"] == "authorization_code"
    expected = (_CODE, _REDIRECT, _SECRET)
    assert (form["code"], form["redirect_uri"], form["client_secret"]) == expected


def test_consent_page_asks_for_readonly_offline_access_with_pkce() -> None:
    """The page asks read-only Gmail, offline access and a fresh prompt, with an S256 challenge."""
    run = _Run()
    run.go()
    query = {k: v[0] for k, v in parse_qs(urlsplit(run.opened[0]).query).items()}
    assert query["scope"] == SCOPE
    assert (query["access_type"], query["prompt"]) == ("offline", "consent")
    verifier = run.posted[0][1]["code_verifier"]
    digest = hashlib.sha256(verifier.encode()).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert (query["code_challenge"], query["code_challenge_method"]) == (expected, "S256")
    assert _SECRET not in run.opened[0]


def test_state_mismatch_is_refused_before_the_code_is_used() -> None:
    """A redirect whose state differs is refused; nothing is POSTed and nothing is encrypted."""
    run = _Run(tamper=True)
    with pytest.raises(ConsentError, match="state"):
        run.go()
    assert run.posted == []
    assert run.encrypted == []


def test_refused_exchange_carries_no_secret() -> None:
    """A 400 echoing the secret and the code names its status only; encrypt is never called."""
    echoed = _dumps({"error": "invalid_grant", "error_description": f"{_SECRET} {_CODE}"})
    run = _Run(_BAD_REQUEST, echoed.encode())
    with pytest.raises(ConsentError, match="HTTP 400") as caught:
        run.go()
    for planted in (_SECRET, _CODE):
        assert planted not in _rendered(caught.value)
    assert run.encrypted == []


def test_response_without_refresh_token_is_refused() -> None:
    """A 200 with no refresh_token is an error, not a silent success with nothing encrypted."""
    run = _Run(_OK, _dumps({"access_token": "ya29.x"}).encode())
    with pytest.raises(ConsentError, match="no refresh_token"):
        run.go()
    assert run.encrypted == []


def test_unreadable_client_json_is_refused_without_quoting_it() -> None:
    """A client JSON that will not parse, or lacks its fields, is refused; its text is unquoted."""
    for text in ("{" + _SECRET, _dumps({"web": {"client_secret": _SECRET}})):
        with pytest.raises(ConsentError) as caught:
            read_client(text)
        assert _SECRET not in _rendered(caught.value)


def test_pkce_pair_is_unpadded_base64url_and_s256() -> None:
    """The verifier is 32 random bytes as unpadded base64url; the challenge is its SHA-256."""
    verifier, challenge = pkce(lambda n: b"\xff" * n)
    digest = hashlib.sha256(verifier.encode()).digest()
    assert "=" not in verifier + challenge
    assert challenge == base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

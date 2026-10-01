# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The one-time consent run (W353): a refresh token that only ever exists age-encrypted.

The operator runs this once (W290): it opens Google's consent page, receives the authorization code
on a loopback redirect, exchanges it, and hands the refresh token straight to `encrypt`, which
writes it as an age file to the YubiKey recipient. After that, auth.decrypt is the only way back.

⚑⚑ THE REFRESH TOKEN IS NEVER RETURNED, PRINTED OR WRITTEN IN THE CLEAR. `consent` passes it to
`encrypt` and drops it. The client secret is read here and nowhere else, and no error quotes
either one, or the client JSON, or a response body.

⚑ EVERY EFFECT IS AN ARGUMENT. The browser, the loopback listener, the POST, the encryption and the
random source are all passed in, so the flow is tested end to end with fakes, and this module does
no I/O of its own. The CLI (W289) supplies the real ones.

⚑ PKCE AND STATE, as RFC 7636 and RFC 6749 section 10.12 ask of a desktop client: the verifier
never leaves this process except in the token POST, and a redirect whose `state` differs from the
one sent is refused before its code is used.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from typing import cast
from urllib.parse import urlencode

from mikemol.gmailstruct.auth import OAUTH_ENDPOINT, Poster

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
_OK = 200
_ENTROPY = 32

type Random = Callable[[int], bytes]
type Browser = Callable[[str], None]
# () -> (code, state), from the loopback redirect the CLI listens for.
type AwaitCode = Callable[[], tuple[str, str]]
# The refresh token -> nothing: the CLI writes it age-encrypted to the YubiKey recipient.
type Encrypt = Callable[[str], None]


class ConsentError(Exception):
    """The consent run failed; the message holds no token, secret, code or body."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def pkce(random: Random) -> tuple[str, str]:
    """Make a PKCE verifier and its S256 challenge.

    Returns:
        (verifier, challenge), both unpadded base64url.

    """
    verifier = _b64url(random(_ENTROPY))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def read_client(text: str) -> tuple[str, str]:
    """Read the client id and secret from a Google "installed" client JSON.

    Returns:
        (client_id, client_secret).

    Raises:
        ConsentError: when either is missing; the message never quotes the file.

    """
    try:
        value = cast("object", json.loads(text))
    except ValueError:
        msg = "the client JSON is not JSON"
        raise ConsentError(msg) from None
    root = cast("dict[str, object]", value) if isinstance(value, dict) else {}
    installed = root.get("installed")
    fields = cast("dict[str, object]", installed) if isinstance(installed, dict) else {}
    client_id = fields.get("client_id")
    secret = fields.get("client_secret")
    if not isinstance(client_id, str) or not client_id or not isinstance(secret, str) or not secret:
        msg = "the client JSON has no installed.client_id and installed.client_secret"
        raise ConsentError(msg)
    return client_id, secret


def consent_url(client_id: str, redirect_uri: str, challenge: str, state: str) -> str:
    """Build the consent page URL: read-only Gmail, offline access, a fresh consent prompt.

    Returns:
        the URL to open.

    """
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
    )
    return f"{AUTH_ENDPOINT}?{query}"


def _redeem(form: dict[str, str], post: Poster) -> str:
    """POST the authorization-code grant and return the refresh token it yields.

    Returns:
        the refresh token.

    Raises:
        ConsentError: on a non-200, a body that is not JSON, or no refresh_token in it.

    """
    status, body = post(OAUTH_ENDPOINT, form)
    if status != _OK:
        msg = f"the code exchange failed: HTTP {status}"
        raise ConsentError(msg)
    try:
        value = cast("object", json.loads(body))
    except (ValueError, UnicodeDecodeError):
        msg = "the code exchange returned a body that is not JSON"
        raise ConsentError(msg) from None
    fields = cast("dict[str, object]", value) if isinstance(value, dict) else {}
    refresh = fields.get("refresh_token")
    if not isinstance(refresh, str) or not refresh:
        msg = "the code exchange returned no refresh_token (was prompt=consent honoured?)"
        raise ConsentError(msg)
    return refresh


def consent(
    client_text: str,
    redirect_uri: str,
    effects: tuple[Random, Browser, AwaitCode, Poster, Encrypt],
) -> None:
    """Run the consent flow once, ending with the refresh token handed to `encrypt`.

    Raises:
        ConsentError: on a state mismatch, a refused exchange, or a response with no refresh
            token. No message names the token, the secret, the code or the body.

    """
    random, browser, await_code, post, encrypt = effects
    client_id, secret = read_client(client_text)
    verifier, challenge = pkce(random)
    state = _b64url(random(_ENTROPY))
    browser(consent_url(client_id, redirect_uri, challenge, state))
    code, returned = await_code()
    if not hmac.compare_digest(returned, state):
        msg = "the redirect's state does not match the one sent; refusing its code"
        raise ConsentError(msg)
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": secret,
    }
    encrypt(_redeem(form, post))

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The refresh token, decrypted from its age file into memory only (W351).

⚑⚑ THE TOKEN NEVER TOUCHES A FILE IN THE CLEAR. It lives on disk only as an age file to the
YubiKey PIV recipient (age-plugin-yubikey); `decrypt` asks `age` for it on stdout, a pipe the
runner reads, and returns it. Nothing here writes, caches or logs it.

⚑ THE RUNNER IS AN ARGUMENT, NOT A DEFAULT. This module starts no process: the CLI (W289) passes
the runner that executes `age`, and the tests pass a fake one. So the record layer stays free of
subprocess, and the path from ciphertext to token is testable without a key.

⚑ A FAILURE CARRIES NO SECRET. When `age` fails, its stdout is dropped unread and the error names
only the file and the exit status, so a partial or garbage plaintext cannot reach a traceback.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

# argv -> (exit status, stdout, stderr). The CLI supplies one that runs the command; tests fake it.
type Runner = Callable[[list[str]], tuple[int, bytes, bytes]]


class DecryptError(Exception):
    """The token could not be decrypted; the message holds no plaintext."""


def decrypt(path: Path, identity: Path, runner: Runner) -> str:
    """Decrypt the refresh token at `path` with the YubiKey identity stub at `identity`.

    Returns:
        the token, stripped of surrounding whitespace.

    Raises:
        DecryptError: when age fails, or yields no token. The message names the file only.

    """
    status, out, _err = runner(["age", "--decrypt", "--identity", str(identity), str(path)])
    if status != 0:
        msg = f"age could not decrypt {path} (exit {status})"
        raise DecryptError(msg)
    try:
        token = out.decode("utf-8").strip()
    except UnicodeDecodeError:
        msg = f"age decrypted {path} to bytes that are not UTF-8"
        raise DecryptError(msg) from None
    if not token:
        msg = f"age decrypted {path} to nothing"
        raise DecryptError(msg)
    return token


# W352: Google's token endpoint. The refresh-token grant is RFC 6749 section 6.
OAUTH_ENDPOINT = "https://oauth2.googleapis.com/token"
_OK = 200

# (url, form fields) -> (HTTP status, body). The CLI supplies one that POSTs; tests fake it.
type Poster = Callable[[str, dict[str, str]], tuple[int, bytes]]


class ExchangeError(Exception):
    """The refresh token could not be exchanged; the message holds no token and no body."""


def _oauth_error(body: bytes) -> str:
    """Return the OAuth `error` code from a failed response, or "unreadable".

    Only the code is taken (e.g. `invalid_grant`): it names the failure and carries no secret. The
    body itself, which can echo request fields, is never put in a message.

    Returns:
        the error code, or "unreadable" when the body has none that is a plain identifier.

    """
    try:
        value = cast("object", json.loads(body))
    except (ValueError, UnicodeDecodeError):
        return "unreadable"
    if isinstance(value, dict):
        code = cast("dict[str, object]", value).get("error")
        if isinstance(code, str) and code.isascii() and code.replace("_", "").isalnum():
            return code
    return "unreadable"


def exchange(refresh: str, client_id: str, client_secret: str, post: Poster) -> tuple[str, int]:
    """Exchange the refresh token for an access token, in memory.

    Returns:
        (access token, seconds until it expires).

    Raises:
        ExchangeError: on a non-200 status or a response without both fields. The message names
            the status and the OAuth error code only.

    """
    status, body = post(
        OAUTH_ENDPOINT,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    if status != _OK:
        msg = f"token exchange failed: HTTP {status}, {_oauth_error(body)}"
        raise ExchangeError(msg)
    try:
        value = cast("object", json.loads(body))
    except (ValueError, UnicodeDecodeError):
        msg = "token exchange returned a body that is not JSON"
        raise ExchangeError(msg) from None
    fields = cast("dict[str, object]", value) if isinstance(value, dict) else {}
    token = fields.get("access_token")
    expires = fields.get("expires_in")
    if not isinstance(token, str) or not token or not isinstance(expires, int):
        msg = "token exchange returned no access_token and expires_in"
        raise ExchangeError(msg)
    return token, expires

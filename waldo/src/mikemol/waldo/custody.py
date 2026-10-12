# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Custody of a secret a waldo holds: print a fingerprint, store 0600, name who acts (W1058).

Lifted from amr-skills' `peer_token.py` (W325/W340), which minted a bounded token, stored it, and
printed only a fingerprint and an expiry.

⚑ A `Secret` PRINTS AS ITS FINGERPRINT, EVERYWHERE. `repr`, `str`, an f-string and a `%s` all give
`Secret(3f9a1c0b27de)`; the value leaves only through `reveal()`, which a reviewer can grep for.
What the queue may see is the fingerprint (the first 12 hex of the value's sha256: enough to tell
two secrets apart, useless to an attacker) and an expiry.

⚑ THE FILE IS 0600 IN A 0700 DIRECTORY, WRITTEN BY RENAME. A temporary file is made with `O_EXCL`
at mode 0600 in the same directory and renamed over the target, so a reader sees the old secret or
the new one, never half of one. An existing directory that is open to group or others is REFUSED,
not tightened behind the owner's back, and a link is refused as data (no-symlinks ruling) for the
file and its directory alike.

⚑ THE IDENTITY THAT ACTS IS AN EXPLICIT CHOICE. `require_identity` refuses unless a machine
identity is named or the caller says `as_current_user`; a waldo never quietly becomes the operator.

⚑ `scrub` REMOVES A SECRET FROM TEXT before it is printed or logged, so an error that echoes a
command's output cannot carry it out.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

DIR_MODE = 0o700
FILE_MODE = 0o600
OPEN_BITS = 0o077
FINGERPRINT_HEX = 12


class CustodyError(RuntimeError):
    """The secret cannot be kept, read or acted on safely."""


def fingerprint(value: str) -> str:
    """Give the first 12 hex of a value's sha256.

    Returns:
        the fingerprint.

    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:FINGERPRINT_HEX]


class Secret:
    """A secret value that prints as its fingerprint; only `reveal()` gives the value back."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        """Hold `value`."""
        self._value = value

    def reveal(self) -> str:
        """Give the secret value; the one way out, so a reviewer can find every use.

        Returns:
            the value.

        """
        return self._value

    def fingerprint(self) -> str:
        """Give the fingerprint of the value.

        Returns:
            the first 12 hex digits of the sha256.

        """
        return fingerprint(self._value)

    def __repr__(self) -> str:
        """Print the fingerprint, never the value.

        Returns:
            `Secret(<fingerprint>)`.

        """
        return f"Secret({self.fingerprint()})"

    def __str__(self) -> str:
        """Print the fingerprint, never the value.

        Returns:
            `Secret(<fingerprint>)`.

        """
        return repr(self)

    def __format__(self, spec: str) -> str:
        """Format as the fingerprint form whatever the spec asks.

        Returns:
            `Secret(<fingerprint>)`, padded by the spec when it has one.

        """
        return format(repr(self), spec)


def scrub(text: str, *secrets: Secret) -> str:
    """Replace each secret's value in `text` with its printed form.

    Returns:
        the text with no secret value in it.

    """
    for secret in secrets:
        value = secret.reveal()
        if value:
            text = text.replace(value, repr(secret))
    return text


def require_identity(identity: str | None, *, as_current_user: bool) -> str:
    """Refuse to act unless the caller chose who acts.

    Returns:
        a label for the chosen identity: the named one, or `current user`.

    Raises:
        CustodyError: when no identity is named and the caller did not opt in to their own.

    """
    if identity:
        return identity
    if as_current_user:
        return "current user"
    msg = "no identity chosen: name a machine identity, or pass as_current_user explicitly"
    raise CustodyError(msg)


def _refuse_link(path: Path) -> None:
    """Refuse a path that is a link.

    Raises:
        CustodyError: when it is.

    """
    if path.is_symlink():
        msg = f"{path} is a link; a secret is never written or read through one"
        raise CustodyError(msg)


def write_secret(path: Path, secret: Secret) -> None:
    """Write the secret to `path` at 0600 in a 0700 directory, atomically.

    A link at the file or its directory is refused too.

    Raises:
        CustodyError: when the directory already exists and is open to group or others.

    """
    _refuse_link(path)
    _refuse_link(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True, mode=DIR_MODE)
    if path.parent.stat().st_mode & OPEN_BITS:
        msg = f"{path.parent} is open to group or others; refusing to keep a secret there"
        raise CustodyError(msg)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(secret.reveal())
    temporary.replace(path)


def read_secret(path: Path) -> Secret | None:
    """Read the stored secret; a link at the file or its directory is refused.

    Returns:
        the Secret, or None when nothing (or only blank text) is stored.

    """
    _refuse_link(path)
    _refuse_link(path.parent)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return Secret(text) if text else None


def describe(secret: Secret, expires: float | None = None) -> str:
    """Say what may be shown about a secret: its fingerprint and expiry, never its value.

    Returns:
        `fingerprint <hex>` with `, expires <UTC time>` when an expiry is known.

    """
    shown = f"fingerprint {secret.fingerprint()}"
    if expires is None:
        return shown
    stamp = datetime.fromtimestamp(expires, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{shown}, expires {stamp}"

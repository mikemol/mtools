# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An MHTML archive as a list of parts, with a root part and addressing by Content-Location (W907).

⚑ AN MHTML FILE IS A `multipart/related` MESSAGE: the first part is the page and the rest are what
it embeds, each named by a `Content-Location`. Anything else is a `Skip` with its reason, never a
guess that it was HTML. ⚑ A PART'S PAYLOAD IS DECODED BEFORE IT IS EXPOSED (quoted-printable and
base64 are transfer encodings, not content), and the root is decoded with the charset the part
declares, falling back to UTF-8, so the HTML readers see the page and not its wire form.
⚑ AN ABSENT LOCATION IS A `Miss`, NOT NONE: a part that exists with no body and a location that
names nothing are different answers.

⚑ THE MULTIPART SPLIT IS WRITTEN HERE, NOT TAKEN FROM `email`: the standard library's message
types are generic over `Any`, which this distribution's strict typing refuses to let through, and
the part of RFC 2046 an archive needs is small (a boundary, headers, a blank line, a body).

CONSUMED BY: the CLI and the routing of one file to the HTML or MHTML reader (W908, W909).
"""

from __future__ import annotations

import base64
import binascii
import quopri
import re
from dataclasses import dataclass

from mikemol.htmlstruct import tree

_ROOT_TYPE = "multipart/related"
_BOUNDARY = re.compile(r'boundary="?([^";\s]+)"?', re.IGNORECASE)
_CHARSET = re.compile(r'charset="?([^";\s]+)"?', re.IGNORECASE)
_HEAD_END = re.compile(rb"\r?\n\r?\n")


@dataclass(frozen=True)
class Part:
    """One part: where it says it lives, its media type and charset, and its decoded bytes."""

    location: str | None
    content_type: str
    charset: str | None
    payload: bytes


@dataclass(frozen=True)
class Archive:
    """The parts of an archive in order; the first is the root."""

    parts: tuple[Part, ...]


@dataclass(frozen=True)
class Miss:
    """A location that names no part, with the location."""

    location: str


def _split(raw: bytes) -> tuple[dict[str, str], bytes]:
    """Split a message into its headers (lower-cased names, folded lines joined) and its body.

    Returns:
        the headers, first spelling of a name winning, and the bytes after the blank line.

    """
    end = _HEAD_END.search(raw)
    head, body = (raw, b"") if end is None else (raw[: end.start()], raw[end.end() :])
    headers: dict[str, str] = {}
    last = ""
    for line in head.decode("latin-1").splitlines():
        if line[:1] in {" ", "\t"} and last:
            headers[last] += " " + line.strip()
        elif ":" in line:
            name, _, value = line.partition(":")
            last = name.strip().lower()
            headers.setdefault(last, value.strip())
    return headers, body


def _bodies(body: bytes, boundary: str) -> list[bytes]:
    """Cut a multipart body at its delimiter lines.

    Returns:
        the raw bytes of each part, the line ending before a delimiter not included.

    """
    opener, closer = f"--{boundary}".encode(), f"--{boundary}--".encode()
    parts: list[bytes] = []
    current: list[bytes] | None = None
    for line in body.splitlines(keepends=True):
        mark = line.rstrip()
        if mark in {opener, closer}:
            if current is not None:
                parts.append(b"".join(current).removesuffix(b"\n").removesuffix(b"\r"))
            if mark == closer:
                break
            current = []
        elif current is not None:
            current.append(line)
    return parts


def _decoded(body: bytes, encoding: str) -> bytes | None:
    """Undo a part's Content-Transfer-Encoding.

    Returns:
        the content bytes, or None when base64 is malformed.

    """
    kind = encoding.strip().lower()
    if kind == "base64":
        try:
            return base64.b64decode(body)
        except binascii.Error:
            return None
    if kind == "quoted-printable":
        return quopri.decodestring(body)
    return body


def _part(raw: bytes) -> Part | None:
    headers, body = _split(raw)
    content = _decoded(body, headers.get("content-transfer-encoding", ""))
    if content is None:
        return None
    kind = headers.get("content-type", "text/plain")
    charset = _CHARSET.search(kind)
    return Part(
        headers.get("content-location"),
        kind.partition(";")[0].strip().lower(),
        None if charset is None else charset.group(1),
        content,
    )


def read(data: bytes) -> Archive | tree.Skip:
    """Parse an MHTML file into its parts.

    Returns:
        the Archive, or a Skip when the file is not a multipart/related message with at least one
        part that decodes.

    """
    headers, body = _split(data)
    kind = headers.get("content-type", "")
    if kind.partition(";")[0].strip().lower() != _ROOT_TYPE:
        return tree.Skip(f"not {_ROOT_TYPE}: {kind.partition(';')[0].strip() or 'no Content-Type'}")
    boundary = _BOUNDARY.search(kind)
    if boundary is None:
        return tree.Skip(f"{_ROOT_TYPE} with no boundary")
    decoded = [_part(raw) for raw in _bodies(body, boundary.group(1))]
    if None in decoded:
        return tree.Skip("a part has malformed base64")
    parts = tuple(p for p in decoded if p is not None)
    return Archive(parts) if parts else tree.Skip(f"{_ROOT_TYPE} with no parts")


def part_at(archive: Archive, location: str) -> Part | Miss:
    """Find the first part whose Content-Location is exactly `location`.

    Returns:
        the Part, or a Miss naming the location.

    """
    found = next((p for p in archive.parts if p.location == location), None)
    return Miss(location) if found is None else found


def root_tree(archive: Archive) -> tree.Node | tree.Skip:
    """Parse the root part as HTML, in the charset it declares.

    Returns:
        the document tree, or a Skip when the root is not HTML or cannot be decoded.

    """
    root = archive.parts[0]
    if root.content_type != "text/html":
        return tree.Skip(f"root part is {root.content_type}, not text/html")
    charset = root.charset or "utf-8"
    try:
        text = root.payload.decode(charset)
    except (UnicodeDecodeError, LookupError) as fault:
        return tree.Skip(f"root part is not decodable as {charset}: {fault}")
    return tree.parse(text)

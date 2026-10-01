# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""RFC 5545 content lines, written: escaping, folding and CRLF, standard library only (W312).

The projection (W313, W314) builds properties as (name, params, value) and hands them here. This
module only makes them legal iCalendar text, and decides nothing about what a waypoint means.

⚑ THE THREE RULES THAT MAKE A WRITER WRONG IN WAYS A READER HIDES:

- TEXT escaping (3.3.11): backslash, semicolon, comma and newline are escaped. A raw comma in a
  SUMMARY reads back as two values to a strict reader, and as one to a lenient one.
- Folding (3.1): no physical line longer than 75 OCTETS, not characters. A continuation line
  starts with one space, and that space counts. A fold never splits a UTF-8 sequence, or the
  unfolded text is no longer valid UTF-8.
- Line ends are CRLF, always, including after the last line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_LIMIT = 75
_ESCAPES = (("\\", "\\\\"), (";", "\\;"), (",", "\\,"), ("\r\n", "\\n"), ("\n", "\\n"))


def escape(value: str) -> str:
    """Escape a TEXT value (RFC 5545 3.3.11).

    Returns:
        the value with backslash, semicolon, comma and newlines escaped. Backslash goes first, so
        an escape is never escaped again.

    """
    for raw, escaped in _ESCAPES:
        value = value.replace(raw, escaped)
    return value


def fold(line: str) -> list[str]:
    """Fold one content line into physical lines of at most 75 octets (RFC 5545 3.1).

    Returns:
        the physical lines, continuations led by one space, none splitting a UTF-8 sequence.

    """
    parts: list[str] = []
    current = ""
    room = _LIMIT
    for char in line:
        size = len(char.encode())
        if size > room:
            parts.append(current)
            current, room = " ", _LIMIT - 1
        current += char
        room -= size
    parts.append(current)
    return parts


def content_line(name: str, value: str, params: Iterable[tuple[str, str]] = ()) -> str:
    """Write NAME;PARAM=VALUE:value, unfolded, with the value exactly as given.

    The caller escapes a TEXT value with `escape`; a DATE-TIME, an RRULE or a DURATION is written
    as is, because escaping its ";" or "," would break it.

    Returns:
        the logical content line.

    """
    prefix = "".join(f";{key}={param}" for key, param in params)
    return f"{name}{prefix}:{value}"


def serialize(lines: Iterable[str]) -> str:
    """Fold every content line and join them with CRLF, ending with one.

    Returns:
        the iCalendar text.

    """
    return "".join(f"{physical}\r\n" for line in lines for physical in fold(line))

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Redact a literal from one waypoint's text, and scan the whole state for one (W185).

⚑⚑ THE ONLY WRITER HAD NO WAY TO REMOVE TEXT (luthen-observability, 2026-09-27). Evidence is
append-only through `--evidence-append`, and hand edits of the state file are forbidden, so a
cluster Service IP appended into W79's evidence blocked every commit in that repo on its
address-literals gate, and paged, with no allowed path to take it out.

⚑ THE PATTERN IS THE DISCLOSURE, so nothing here echoes it: the ledger and every message name it
by `digest`, and the scan reports where and how many, never what.
⚑ LITERAL, NOT A REGEX: the caller is removing one string it already knows; a regex would make a
typo match something else in silence.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from mikemol.pathsforward.model import text
from mikemol.pathsforward.ops import RefusedError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mikemol.pathsforward.model import Json

REDACTED = "[redacted]"
# The free-text fields of a waypoint; the structured ones (symbols, tags, enums) hold no prose.
FIELDS = ("evidence", "next_bounded_step", "title")
_DIGEST_HEX = 12


def digest(pattern: str) -> str:
    """Name a pattern without disclosing it.

    Returns:
        `sha256:` and the first 12 hex digits of the pattern's hash.

    """
    return "sha256:" + hashlib.sha256(pattern.encode("utf-8")).hexdigest()[:_DIGEST_HEX]


def redact(w: Json, pattern: str, replacement: str = REDACTED) -> int:
    """Replace every occurrence of `pattern` in `w`'s free-text fields, in place.

    Returns:
        how many occurrences were replaced.

    Raises:
        RefusedError: on an empty pattern, a replacement that still holds the pattern, or a pattern
            that matches nothing — so a typo is a refusal, not a silent no-op.

    """
    sym = text(w, "symbol")
    if not pattern:
        msg = f"{sym}: --evidence-redact needs a non-empty pattern"
        raise RefusedError(msg)
    if pattern in replacement:
        msg = f"{sym}: the replacement contains the pattern {digest(pattern)}; nothing would leave"
        raise RefusedError(msg)
    count = sum(text(w, field).count(pattern) for field in FIELDS)
    if count == 0:
        msg = f"{sym}: pattern {digest(pattern)} matches nothing in {', '.join(FIELDS)}"
        raise RefusedError(msg)
    for field in FIELDS:
        value = w.get(field)
        if isinstance(value, str):
            w[field] = value.replace(pattern, replacement)
    return count


def _occurrences(value: object, pattern: str) -> int:
    """Count `pattern` in a string, or across a list's strings; anything else holds none.

    Returns:
        the count.

    """
    if isinstance(value, str):
        return value.count(pattern)
    if isinstance(value, list):
        return sum(item.count(pattern) for item in value if isinstance(item, str))
    return 0


def scan(records: Iterable[Json], ledger_lines: Iterable[str], pattern: str) -> list[str]:
    """Find every place `pattern` still appears: any field of any record, and any ledger line.

    Returns:
        one `SYM field n=<count>` or `ledger line <i> n=<count>` per hit, in order; empty when
        the literal is gone everywhere.

    """
    hits: list[str] = []
    for rec in records:
        for key, value in rec.items():
            n = _occurrences(value, pattern)
            if n:
                hits.append(f"{text(rec, 'symbol')} {key} n={n}")
    for i, raw in enumerate(ledger_lines, 1):
        n = raw.count(pattern)
        if n:
            hits.append(f"ledger line {i} n={n}")
    return hits

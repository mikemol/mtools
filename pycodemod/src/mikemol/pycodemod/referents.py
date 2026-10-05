# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The referent tokens an expression mentions: names, attributes, keywords, identifier strings.

Ported from substrate's `scratch/_pycodemod_fingerprint.py` (W607 step 2): `token_parts`,
`referents` and `MAX_TOKEN`. The control-census import is gone; the one helper it supplied
(`as_list`, a node or a sequence of nodes read as a list) is inlined.

⚑ NO KIND SURVIVES INTO THE KEY. A `Name.id`, an `Attribute.attr`, a keyword-argument name and a
string constant that spells a (dotted) identifier all contribute the bare token, so `terms`,
`.terms` and `"terms"` are ONE referent. That collapse is what lets a column named in a string and
the column the schema declares be the same countable thing.

⚑ NUMERIC AND NON-IDENTIFIER STRING CONSTANTS ARE NOT REFERENTS. `if n > 2:` contributes `n`, not
`2`; a raw SQL blob contributes nothing. This is a SHAPE rule, applied identically wherever the
extractor runs, not a judgement about which referents are interesting.

⚑ A TOKEN LONGER THAN `MAX_TOKEN` IS PROSE. It is a shape bound; the token's meaning is never
consulted.

⚑ `referents(None)` RAISES `TypeError` (W664). The origin's `as_list(None)` was `[]`, so
`referents(None)` was the empty set (confirmed by running both). A caller here passes the empty
tuple for no expression, as `fp_sites` does, so a `None` is a bug it should see rather than an empty
referent set that reads as "mentions nothing".
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

MAX_TOKEN = 64


def _as_list(nodes: ast.AST | Iterable[ast.AST]) -> list[ast.AST]:
    """Return one node or any iterable of nodes as a list.

    Returns:
        the nodes, in order.

    """
    if isinstance(nodes, ast.AST):
        return [nodes]
    return list(nodes)


def token_parts(value: object) -> tuple[str, ...]:
    """Return the referent tokens a constant spells, or `()`.

    A non-string, an empty or over-long string, and a string with any non-identifier dotted part
    all spell nothing.

    Returns:
        the dotted parts in order, or the empty tuple.

    """
    if not isinstance(value, str) or not value or len(value) > MAX_TOKEN:
        return ()
    parts = value.split(".")
    if not all(p.isidentifier() for p in parts):
        return ()
    return tuple(parts)


def referents(nodes: ast.AST | Iterable[ast.AST]) -> set[str]:
    """Return the DISTINCT referent tokens an expression (or a sequence of them) mentions.

    Returns:
        the bare tokens, each once.

    """
    out: set[str] = set()
    for top in _as_list(nodes):
        for n in ast.walk(top):
            if isinstance(n, ast.Name):
                out.add(n.id)
            elif isinstance(n, ast.Attribute):
                out.add(n.attr)
            elif isinstance(n, ast.keyword) and n.arg:
                out.add(n.arg)
            elif isinstance(n, ast.Constant):
                out.update(token_parts(n.value))
    return {t for t in out if t and len(t) <= MAX_TOKEN}

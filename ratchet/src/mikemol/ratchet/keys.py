# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The key schema: which field of a baseline key is the PATH, declared rather than guessed.

⚑⚑⚑ A MOVE IS RECOGNISED BY COMPARING KEYS ON EVERYTHING BUT THE PATH, SO THE RATCHET MUST KNOW
WHICH FIELD THE PATH IS. For ruff's `path:rule` that is "all but the last colon field", and
`RUFF` keeps that reading byte-for-byte. A peer's gates key differently — `::`-separated, a path
SECOND in two of them, three fields in two more — and reading those as `path:rule` gets all three
wrong: a reversed key's NAME reads as its path, a triple keeps only its last field so two
violations collide, and a key of the wrong shape is quietly read as a path. Each of those is a
false absolution, which is the one error a paydown-only ratchet must never make.

⚑⚑ A KEY ITS DECLARED SCHEMA CANNOT PARSE IS REFUSED — `MalformedKeyError` — never read as a
path. A mis-assigned path makes a genuine violation look like churn.

⚑⚑ THE SEAM IS A FUNCTION, `str -> ParsedKey`, NOT A PROTOCOL WITH A `parse` METHOD. Measured:
`mutate_runner.py` addresses a def-site by NAME and mutates the first match, so a Protocol stub
plus two implementations of `parse` put three mutants on the never-called stub and reported all
three SURVIVED while the real parsers went unmutated. Distinct function names make every parser a
site the gate actually reaches. A new schema is one more entry in `SCHEMAS`.

⚑ THE PEER'S TABLE IS MEASURED, NOT IMPORTED. `substrate/ratchet_key.py` `SCHEMA` (lines 65-91)
declares seven gates; the entries below re-express its `sep`, `path_field` and `arity` so this
distribution keeps its zero runtime dependencies. Baseline file names and nouns are the peer's
concern and are not carried.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class MalformedKeyError(ValueError):
    """Raised for a key its declared schema cannot parse."""


class UnknownSchemaError(ValueError):
    """Raised for a schema name no entry declares."""


@dataclass(frozen=True, slots=True)
class ParsedKey:
    """One key split into the path a move changes and the identity a move preserves."""

    path: str
    identity: tuple[str, ...]


def split_last_field(key: str, *, sep: str) -> ParsedKey:
    """Read ruff's `path:rule`: the rule is the LAST `sep` field, since a path may carry colons.

    ⚑ TOTAL — IT NEVER REFUSES, which is the pre-schema reading kept exactly: a key with no
    separator is its own identity at the empty path.

    Returns:
        the path before the last separator, and the rule after it as a one-field identity.

    """
    path, _, rule = key.rpartition(sep)
    return ParsedKey(path, (rule or key,))


@dataclass(frozen=True, slots=True)
class FieldShape:
    """A `sep`-joined key of exactly `arity` fields, of which `path_field` is the path."""

    sep: str
    path_field: int
    arity: int


def split_fields(key: str, *, shape: FieldShape) -> ParsedKey:
    """Split on `shape.sep`, refusing any field count other than `shape.arity`.

    Returns:
        the path field, and every other field in order as the identity.

    Raises:
        MalformedKeyError: when the field count differs from `shape.arity`.

    """
    fields = key.split(shape.sep)
    if len(fields) != shape.arity:
        msg = (
            f"MalformedKeyError: expected {shape.arity} {shape.sep!r}-separated "
            f"field(s), got {len(fields)} in {key!r}"
        )
        raise MalformedKeyError(msg)
    ident = tuple(f for i, f in enumerate(fields) if i != shape.path_field)
    return ParsedKey(fields[shape.path_field], ident)


type KeySchema = Callable[[str], ParsedKey]

_SEP = "::"
_PATH_FIRST = 0
_PATH_SECOND = 1
_PAIR = 2
_TRIPLE = 3

RUFF = "ruff"


def _substrate(path_field: int, arity: int) -> KeySchema:
    """Bind one of the peer's `::` shapes.

    Returns:
        a parser for that shape.

    """
    return partial(split_fields, shape=FieldShape(_SEP, path_field, arity))


SCHEMAS: dict[str, KeySchema] = {
    RUFF: partial(split_last_field, sep=":"),
    "substrate:public": _substrate(_PATH_FIRST, _PAIR),
    "substrate:private": _substrate(_PATH_FIRST, _PAIR),
    "substrate:carrier-locality": _substrate(_PATH_FIRST, _PAIR),
    # ⚑ REVERSED in the peer's census: `name::relpath`.
    "substrate:sumtype": _substrate(_PATH_SECOND, _PAIR),
    "substrate:discharge": _substrate(_PATH_SECOND, _PAIR),
    "substrate:ban": _substrate(_PATH_FIRST, _TRIPLE),
    "substrate:claims": _substrate(_PATH_FIRST, _TRIPLE),
}

SCHEMA_NAMES: tuple[str, ...] = tuple(sorted(SCHEMAS))


def schema_named(name: str) -> KeySchema:
    """Return the declared schema called `name`.

    Returns:
        the schema declared under `name`.

    Raises:
        UnknownSchemaError: when no schema is declared under `name`.

    """
    try:
        return SCHEMAS[name]
    except KeyError:
        msg = f"UnknownSchemaError: no key schema named {name!r}; declared: {list(SCHEMA_NAMES)}"
        raise UnknownSchemaError(msg) from None


def parse_all(schema: KeySchema, keys: frozenset[str]) -> dict[str, ParsedKey]:
    """Parse every key, so one malformed key refuses the whole set.

    Returns:
        each key mapped to its parse.

    """
    return {key: schema(key) for key in keys}

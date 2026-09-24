# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a warrants bib FULL-FIDELITY — what the FILE says, including what the engine drops.

Moved from substrate's `substrate/raw_bib.py` (the N-d warrant split, witness half, moved whole);
its suite is ported to `tests/test_raw_bib.py`.

⚑⚑⚑ THE SECOND READER, AND THE PAIR IS THE POINT. The engine's parser is a WHITELIST (a projector
must not render fields it does not understand); this reads the raw text. The DIFFERENCE between
them is a class of fact nothing else sees: which entries carry a field the engine silently drops.

⚑⚑ A KEY DECLARED IN TWO BIBS IS A COLLISION, NOT A MERGE: a plain update loses the earlier
declaration with no signal, which is how twelve files declaring 84 records reported as 77 distinct
keys. Last-write-wins is kept (a later bib layering an earlier one is how a composed projection
works), but the collision is REPORTED, beside the map, never inside it as a phantom entry.

⚑⚑⚑ ABSENT, BROKEN AND MANGLED ARE THREE FACTS, and only absent is an answer. A non-UTF-8 bib is
BROKEN: decoding with replacement characters would parse plausible fictional entries, and an
invented row corroborates itself where a missing one can at least move a denominator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# ⚑ THE EDGE VOCABULARY, DECLARED ONCE: the fields that name another entry.
EDGE_FIELDS = ("from", "rests-on", "enables")

# One `@kind{key, …}` record, up to a closing brace at column 0.
_ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", re.DOTALL)

# One `field = {value}`, tolerating one level of nested braces inside the value.
_FIELD = re.compile(r"['\"]?([\w-]+)['\"]?\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")


class BibError(RuntimeError):
    """A bib could not be read, with the arm that failed named in the message."""


@dataclass(frozen=True, slots=True)
class Collision:
    """One key declared in two bibs, and where."""

    key: str
    first: Path
    later: Path


@dataclass(frozen=True, slots=True)
class Corpus:
    """The composed entry map, and the collisions found composing it: both halves, always."""

    entries: dict[str, dict[str, str]]
    collisions: tuple[Collision, ...]


def read_text(path: Path) -> str:
    """Read a bib's text, naming WHICH failure occurred when it cannot.

    Returns:
        the text.

    Raises:
        BibError: ABSENT for a missing file, DIRECTORY for a directory, BROKEN for invalid UTF-8,
            and a did-not-happen read for any other OS failure.

    """
    if not path.exists():
        msg = (
            f"no such bib {path} — ABSENT. The file is not there; this is NOT the same as an "
            f"empty bib, and not the same as a read that failed."
        )
        raise BibError(msg)
    if path.is_dir():
        msg = f"cannot read {path} — it is a DIRECTORY, so the read did not happen."
        raise BibError(msg)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        msg = (
            f"{path} is not valid UTF-8 ({exc}). A bib that cannot be decoded is BROKEN, not "
            f"empty — refusing to parse a mangled corpus into entries that would look "
            f"plausible and corroborate themselves."
        )
        raise BibError(msg) from exc
    except OSError as exc:
        msg = f"cannot read {path} — the read did NOT happen ({exc}). This is not an absence."
        raise BibError(msg) from exc


def _group(found: re.Match[str], index: int) -> str:
    """Narrow one captured group to `str` at the seam (`group()` is typed `str | Any`).

    Returns:
        the group's text; empty when the group did not participate.

    """
    got = found.group(index)
    return got if isinstance(got, str) else ""


def _fields_of(body: str) -> dict[str, str]:
    """Read one entry's fields.

    Returns:
        `{field: raw value}`.

    """
    return {_group(found, 1): _group(found, 2) for found in _FIELD.finditer(body)}


def parse(text: str) -> dict[str, dict[str, str]]:
    """Parse one bib's text, every field, deliberately NOT filtered to the engine's whitelist.

    Returns:
        `{key: {field: raw value}}`.

    """
    return {_group(found, 2): _fields_of(_group(found, 3)) for found in _ENTRY.finditer(text)}


def read(paths: Path | list[Path]) -> Corpus:
    """Read one bib or a composed set, reporting any key declared in more than one.

    ⚑⚑ The composed set is the unit: a document projects from several bibs.

    Returns:
        the composed entries (last declaration wins) and every collision.

    """
    if isinstance(paths, Path):
        return Corpus(entries=parse(read_text(paths)), collisions=())
    out: dict[str, dict[str, str]] = {}
    seen: dict[str, Path] = {}
    collisions: list[Collision] = []
    for one in paths:
        for key, fields in parse(read_text(one)).items():
            if key in seen and seen[key] != one:
                collisions.append(Collision(key=key, first=seen[key], later=one))
            seen[key] = one
            out[key] = fields
    return Corpus(entries=out, collisions=tuple(collisions))


def entries_with_dropped_edges(corpus: Corpus, accepted: frozenset[str]) -> tuple[str, ...]:
    """Name the entries carrying an edge field the engine does NOT accept.

    ⚑⚑ The join the two readers exist for. `accepted` comes from the ENGINE, a parameter, never a
    constant here, so this cannot drift from what the engine currently accepts.

    Returns:
        the sorted keys.

    """
    return tuple(
        sorted(
            key
            for key, fields in corpus.entries.items()
            if any(field in EDGE_FIELDS and field not in accepted for field in fields)
        )
    )

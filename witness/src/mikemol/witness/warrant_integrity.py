# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The keys-unique family — a warrant set that is present, whole, and carrying its commitments.

Moved from substrate's `substrate/warrant_integrity.py` (the N-d warrant split, witness half);
its suite is ported to `tests/test_warrant_integrity.py`.

⚑⚑⚑ IT DID NOT MOVE WHOLE, AND THE TWO SEAMS ARE THE SPLIT ITSELF. substrate's version read its
bib from `warrant_bib.BIB` (derived from `corpus.ROOT`, which the no-ROOT ruling forbids) and
parsed through `warrant_records.records` (the one paperkit contact, which the split sends to
paperkit). So both are REQUIRED ARGUMENTS here: the caller names the bib, and passes the engine's
parse as `parse`. This distribution stays stdlib-only and never imports the engine.

⚑⚑ FOUR CLAIMS, grown one at a time as mutation sweeps graded each prior one insensitive:
- the set is NOT EMPTY: a check built only from "for all x" claims cannot detect the collection's
  destruction, because every one of them is vacuously true of zero entries;
- NO KEY IS SILENTLY SHADOWED: the engine keeps the last duplicate with no warning, so the FILE's
  own count (written) is compared with what SURVIVED parsing (parsed); two routes are the test;
- every entry carries a CLAIM and a CHECK;
- every claim carries READABLE PROSE (at least `MIN_PROSE` characters): the claim that makes the
  check answer about content rather than structure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.witness import raw_bib, witness_family, witness_row

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    # The engine's parse: a bib path to `{key: {field: value}}`. The CALLER's to pass.
    type Parse = Callable[[Path], dict[str, dict[str, str]]]
    type Row = witness_row.Part | witness_row.Verdict

# A claim shorter than this is not a commitment. One spelling, shared by witness and cases.
MIN_PROSE = 20

# One `@type{key` opening at a line start: the FILE's own count, deliberately not the engine's.
_OPENING = re.compile(r"^@\w+\{\s*([^,\s]+)", re.MULTILINE)

FAMILY = witness_family.of(
    key="keys-unique",
    apex="the warrant set is present, no key is silently shadowed, and every surviving entry "
    "carries the commitment that makes it a claim",
    subject="the entries in the warrants bib",
    members=[
        witness_family.Member(
            name="the_warrant_set_is_not_empty",
            claim="a check built only from universally-quantified claims about a collection "
            "cannot detect the collection's DESTRUCTION: every structural question is "
            "vacuously true of zero entries",
        ),
        witness_family.Member(
            name="no_key_is_silently_shadowed",
            claim="the engine keeps the last duplicate with no warning, so comparing what the "
            "FILE wrote against what SURVIVED parsing detects the loss",
            premises=("the_warrant_set_is_not_empty",),
        ),
        witness_family.Member(
            name="every_entry_carries_a_claim_and_a_check",
            claim="a damaged field vanishes from the parsed record while the entry still "
            "parses, so the warrant is seen and its commitment is gone",
            premises=("the_warrant_set_is_not_empty",),
        ),
        witness_family.Member(
            name="every_claim_carries_readable_prose",
            claim="structural answers survive corruption of the text; asserting prose a reader "
            "could act on is what makes the check answer about CONTENT",
            premises=("every_entry_carries_a_claim_and_a_check",),
        ),
    ],
)


@dataclass(frozen=True, slots=True)
class Integrity:
    """What the two readers say about the warrant set: keys the file wrote, entries that parsed."""

    written: tuple[str, ...]
    parsed: dict[str, dict[str, str]]

    @property
    def empty(self) -> bool:
        """Report whether the parse yielded nothing.

        Returns:
            True for zero parsed entries.

        """
        return not self.parsed

    @property
    def shadowed(self) -> tuple[str, ...]:
        """Name the keys the file writes more than once.

        Returns:
            the sorted duplicated keys.

        """
        return tuple(sorted({k for k in self.written if self.written.count(k) > 1}))

    def missing_field(self, field: str) -> tuple[str, ...]:
        """Name the entries whose `field` did not survive the parse.

        Returns:
            the sorted keys.

        """
        return tuple(key for key, rec in sorted(self.parsed.items()) if not rec.get(field))

    def thin_prose(self) -> tuple[tuple[str, int], ...]:
        """Name the claims too short to be a commitment, with how short.

        Returns:
            `(key, length)` pairs.

        """
        out: list[tuple[str, int]] = []
        for key, rec in sorted(self.parsed.items()):
            prose = " ".join(rec.get("claim", "").split())
            if len(prose) < MIN_PROSE:
                out.append((key, len(prose)))
        return tuple(out)


def read(path: Path, *, parse: Parse) -> tuple[Integrity | None, str | None]:
    """Read the warrant set through BOTH routes, or say why it could not be read.

    ⚑⚑ The engine's exception is caught broadly ON PURPOSE (declared per-file in pyproject): its
    parse errors are its own types, and naming them would couple a witness to an upstream class
    hierarchy that has already changed once. What a caller needs is the REASON.

    Returns:
        `(Integrity, None)`, or `(None, reason)` for an unreadable or unparseable bib.

    """
    try:
        text = raw_bib.read_text(path)
    except raw_bib.BibError as exc:
        return None, str(exc)
    try:
        parsed = parse(path)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    written = tuple(
        got for found in _OPENING.finditer(text) if isinstance(got := found.group(1), str)
    )
    return Integrity(written=written, parsed=parsed), None


def _unreadable(key: str, why: str) -> Iterator[Row]:
    """Yield the verdict for a warrant set that could not be read at all.

    Yields:
        one OPEN verdict naming the reason.

    """
    yield witness_row.opened(key, f"the warrant set could not be read: {why}")


def witness_present(key: str, *, path: Path, parse: Parse) -> Iterator[Row]:
    """Witness that the warrant set exists at all.

    Yields:
        a part for an empty set, then the verdict.

    """
    got, why = read(path, parse=parse)
    if got is None:
        yield from _unreadable(key, why or "no reason given")
        return
    if got.empty:
        yield witness_row.part(key, str(path), route="restore the warrant set")
        yield witness_row.opened(
            key,
            "the warrant set is EMPTY — missing, unreadable, or parsed to zero entries; "
            "a worklist with no claims is not a clean worklist",
        )
        return
    yield witness_row.closed(key, f"{len(got.parsed)} warrant(s) present")


def witness_unshadowed(key: str, *, path: Path, parse: Parse) -> Iterator[Row]:
    """Witness that no key is silently shadowed.

    Yields:
        one part per shadowed key, then the verdict.

    """
    got, why = read(path, parse=parse)
    if got is None:
        yield from _unreadable(key, why or "no reason given")
        return
    for shadowed in got.shadowed:
        yield witness_row.part(key, shadowed, route="rename or remove the duplicate entry")
    if len(got.written) != len(got.parsed):
        yield witness_row.opened(
            key,
            f"{len(got.written)} entries written but {len(got.parsed)} survived parsing — "
            f"key(s) silently shadowed: {', '.join(got.shadowed) or 'unknown'}",
        )
        return
    yield witness_row.closed(key, f"{len(got.parsed)} warrant key(s), all distinct")


def witness_committed(key: str, *, path: Path, parse: Parse) -> Iterator[Row]:
    """Witness that every entry carries a claim and a check.

    Yields:
        one part per entry missing a field, then the verdict.

    """
    got, why = read(path, parse=parse)
    if got is None:
        yield from _unreadable(key, why or "no reason given")
        return
    missing = [(entry, field) for field in ("claim", "check") for entry in got.missing_field(field)]
    for entry, field in missing:
        yield witness_row.part(key, f"{entry} ({field})", route=f"restore the {field} field")
    if missing:
        yield witness_row.opened(
            key,
            f"{len(missing)} warrant(s) missing a commitment: "
            f"{', '.join(f'{e} (no {f})' for e, f in missing)}",
        )
        return
    yield witness_row.closed(key, f"every one of {len(got.parsed)} warrants carries both fields")


def witness_legible(key: str, *, path: Path, parse: Parse) -> Iterator[Row]:
    """Witness that every claim carries readable prose.

    Yields:
        one part per claim too short to be a commitment, then the verdict.

    """
    got, why = read(path, parse=parse)
    if got is None:
        yield from _unreadable(key, why or "no reason given")
        return
    thin = got.thin_prose()
    for entry, length in thin:
        yield witness_row.part(
            key, f"{entry} ({length} chars)", route="write prose a reader could act on"
        )
    if thin:
        yield witness_row.opened(
            key,
            f"{len(thin)} claim(s) shorter than {MIN_PROSE} chars: "
            f"{', '.join(f'{e} ({n})' for e, n in thin)}",
        )
        return
    yield witness_row.closed(key, f"every claim carries at least {MIN_PROSE} chars of prose")


def render(got: Integrity) -> str:
    """Render what each member of the family currently reads.

    Returns:
        one line per population, findings or not.

    """
    lines = [
        f"  {len(got.written)} written, {len(got.parsed)} parsed",
        f"    non-empty        : {'no' if got.empty else 'yes'}",
        f"    shadowed keys    : {', '.join(got.shadowed) or 'none'}",
    ]
    lines.extend(
        f"    missing {field:<9}: {', '.join(got.missing_field(field)) or 'none'}"
        for field in ("claim", "check")
    )
    thin = got.thin_prose()
    lines.append(f"    thin prose       : {', '.join(f'{k} ({n})' for k, n in thin) or 'none'}")
    return "\n".join(lines) + "\n"

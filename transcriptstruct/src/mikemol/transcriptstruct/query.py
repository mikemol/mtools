# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 5: the queries — every answer carries the denominator it was drawn from.

Replaces substrate's messages / grep_content / prose / extract / stats. Two differences are the
point of the port:

- ⚑ "n OF m", AND m IS THE WHOLE INPUT. The old queries counted `total` only up to where they
  stopped scanning, so an `until` or `limit` shrank the denominator with the numerator and a
  "3 of 40" meant "3 of the 40 I happened to read". Here `Result.total` is every record in the
  input, `Result.searched` those inside the line window, and `Result.malformed` the lines that
  were not JSON — all three always, whatever the window;
- ⚑ NOTHING IS SNIPPED. The old grep returned a 240-character window around the first match.
  A `Hit` carries the whole text and the match's span; a reader that wants a preview cuts it.

`stats` gains the UNDECODED count the study asked for: the strings inside every block `blocks`
marked `decoded=False`, plus those under an unknown record's content roots (`message.content`,
`attachment.prompt`). Envelope metadata (ids, timestamps) is not content and is not counted, and
neither is a structural field inside a decoded block (its `type`, a tool_use's `id`): those
were read to decode it.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct.blocks import blocks
from mikemol.transcriptstruct.provenance import classify
from mikemol.transcriptstruct.records import MalformedLine, UnknownRecord
from mikemol.transcriptstruct.walk import strings

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator, Sequence

    from mikemol.transcriptstruct.blocks import Block
    from mikemol.transcriptstruct.records import Record
    from mikemol.transcriptstruct.walk import Path

_CONTENT_ROOTS: tuple[Path, ...] = (("message", "content"), ("attachment", "prompt"))


def _envelope(record: Record) -> object:
    """Return a record's parsed JSON, or None for a line that did not parse.

    Returns:
        the envelope as parsed; None for a malformed line.

    """
    return None if isinstance(record, MalformedLine) else record.raw


def _type_of(envelope: object) -> str:
    """Name an envelope's `type`, as the file spells it.

    Returns:
        the `type` field; "(none)" when absent or not a string; "(not an object)" otherwise.

    """
    if not isinstance(envelope, dict):
        return "(not an object)"
    value = cast("dict[str, object]", envelope).get("type")
    return value if isinstance(value, str) else "(none)"


def raw(
    records: Iterable[Record], types: Collection[str], *, window: Window | None = None
) -> Result:
    """List whole records of the named envelope types, as JSON, in line order.

    This is the read that decides whether a record type earns a decoder: `unknown_types` says
    how many there are, and this shows what they hold.

    Returns:
        one hit per matching record, `kind` its type and `text` its whole JSON, and the
        denominators.

    """
    tally = _Tally()
    for record in _pass(records, window or Window(), tally):
        envelope = _envelope(record)
        kind = _type_of(envelope)
        if kind in types:
            text = json.dumps(envelope, ensure_ascii=False)
            tally.hits.append(Hit(record.line, kind, text, (0, len(text))))
    return tally.result()


# An extracted line: its blocks, or None where no well-formed record has that line.
type Found = tuple[Block, ...] | None


@dataclass(frozen=True, slots=True)
class Hit:
    """One matching text: its line, what it is, the whole text, and where the match sits."""

    line: int
    kind: str
    text: str
    span: tuple[int, int]


@dataclass(frozen=True, slots=True)
class Result:
    """Hits, and the three denominators they were drawn from."""

    hits: tuple[Hit, ...]
    searched: int
    total: int
    malformed: int


@dataclass(frozen=True, slots=True)
class Window:
    """An inclusive range of 1-based line numbers; an open end is unbounded."""

    since: int | None = None
    until: int | None = None

    def admits(self, line: int) -> bool:
        """Say whether `line` falls inside the window.

        Returns:
            True when the line is within both bounds.

        """
        return (self.since is None or line >= self.since) and (
            self.until is None or line <= self.until
        )


@dataclass(slots=True)
class _Tally:
    """The running denominators for one pass."""

    searched: int = 0
    total: int = 0
    malformed: int = 0
    hits: list[Hit] = field(default_factory=list)

    def result(self) -> Result:
        """Freeze the tally.

        Returns:
            the Result.

        """
        return Result(tuple(self.hits), self.searched, self.total, self.malformed)


def _pass(records: Iterable[Record], window: Window, tally: _Tally) -> Iterator[Record]:
    """Count every record, and yield those inside the window that are not malformed.

    Yields:
        each well-formed record whose line the window admits.

    """
    for record in records:
        tally.total += 1
        if isinstance(record, MalformedLine):
            tally.malformed += 1
            continue
        if window.admits(record.line):
            tally.searched += 1
            yield record


def grep_blocks(
    records: Iterable[Record],
    pattern: str,
    *,
    block_kinds: Collection[str] | None = None,
    window: Window | None = None,
) -> Result:
    """Search decoded block text, one hit per matching block.

    Returns:
        the hits, with `kind` the block's kind, and the denominators.

    """
    rx = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    tally = _Tally()
    for record in _pass(records, window or Window(), tally):
        for block in blocks(record):
            match = rx.search(block.text)
            if match and (block_kinds is None or block.kind in block_kinds):
                tally.hits.append(Hit(record.line, block.kind, block.text, match.span()))
    return tally.result()


def grep_prose(
    records: Iterable[Record],
    pattern: str,
    *,
    speakers: Collection[str],
    scheduled: Sequence[str] = (),
    window: Window | None = None,
) -> Result:
    """Search what the named speakers said, wrappers stripped: `speakers={"human"}` is --human.

    Returns:
        the hits, with `kind` the speaker kind, and the denominators.

    """
    rx = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    tally = _Tally()
    for record in _pass(records, window or Window(), tally):
        said = classify(record, scheduled=scheduled)
        match = rx.search(said.text) if said.kind in speakers else None
        if match:
            tally.hits.append(Hit(record.line, said.kind, said.text, match.span()))
    return tally.result()


def prose(
    records: Iterable[Record],
    *,
    speakers: Collection[str] = ("human", "peer", "assistant"),
    scheduled: Sequence[str] = (),
    window: Window | None = None,
) -> Result:
    """List every non-empty utterance by the named speakers, whole, in line order.

    Returns:
        one hit per utterance, its span the whole text, and the denominators.

    """
    tally = _Tally()
    for record in _pass(records, window or Window(), tally):
        said = classify(record, scheduled=scheduled)
        if said.kind in speakers and said.text.strip():
            tally.hits.append(Hit(record.line, said.kind, said.text, (0, len(said.text))))
    return tally.result()


def extract(records: Iterable[Record], lines: Collection[int]) -> dict[int, Found]:
    """Fetch the named lines' blocks, whole.

    Returns:
        every requested line as a key: its blocks, or None where no well-formed record has
        that line — a missing line is reported, never silently absent.

    """
    found: dict[int, Found] = dict.fromkeys(lines)
    for record in records:
        if record.line in found and not isinstance(record, MalformedLine):
            found[record.line] = blocks(record)
    return found


@dataclass(frozen=True, slots=True)
class Stats:
    """Population counts over a whole input."""

    total: int
    malformed: int
    unknown: int
    speakers: dict[str, int]
    block_kinds: dict[str, int]
    undecoded_blocks: int
    undecoded_strings: int
    # ⚑ WHICH record types the unknown count is made of, keyed by `type` ("(none)" when absent).
    # A bare count said "a third of the file is unknown" and could not say why.
    unknown_types: dict[str, int]


def _under(path: Path, roots: Iterable[Path]) -> bool:
    """Say whether `path` lies at or below any of `roots`.

    Returns:
        True when some root is a prefix of the path.

    """
    return any(path[: len(root)] == root for root in roots)


def stats(records: Iterable[Record], *, scheduled: Sequence[str] = ()) -> Stats:
    """Count the populations: speakers, block kinds, and what nothing decoded.

    Returns:
        the Stats. `undecoded_strings` counts the strings inside unread blocks and unknown
        records' content; `unknown_types` breaks the unknown count down by record type.

    """
    total = malformed = undecoded_blocks = undecoded_strings = 0
    speakers: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    unknown_types: Counter[str] = Counter()
    for record in records:
        total += 1
        if isinstance(record, MalformedLine):
            malformed += 1
            continue
        if isinstance(record, UnknownRecord):
            unknown_types[record.type or "(none)"] += 1
        speakers[classify(record, scheduled=scheduled).kind] += 1
        decoded = blocks(record)
        kinds.update(block.kind for block in decoded)
        unread = [block.path for block in decoded if not block.decoded]
        undecoded_blocks += len(unread)
        if isinstance(record, UnknownRecord):
            unread.extend(_CONTENT_ROOTS)
        undecoded_strings += sum(_under(leaf.path, unread) for leaf in strings(record.raw))
    return Stats(
        total=total,
        malformed=malformed,
        unknown=unknown_types.total(),
        speakers=dict(speakers),
        block_kinds=dict(kinds),
        undecoded_blocks=undecoded_blocks,
        undecoded_strings=undecoded_strings,
        unknown_types=dict(unknown_types),
    )

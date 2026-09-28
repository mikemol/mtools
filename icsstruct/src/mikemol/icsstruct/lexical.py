# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 1: RFC 5545 §3.1 lexing, where every physical line lands in exactly one record.

A `.ics` file is a sequence of content lines, each `NAME;PARAM=VALUE...:VALUE`, folded across
physical lines by starting a continuation with one space or tab. `BEGIN:X` and `END:X` nest the
content lines into components. This module unfolds, splits and nests, and yields two record kinds:

- `ContentLine`: one unfolded content line, with its name, parameters and value, and the path of
  components enclosing it;
- `Malformed`: anything that is not a well-formed content line in a well-nested position. It
  carries the reason.

⚑ THE POSITIVE-CONTROL RULE: the records' `first`..`last` spans partition the physical lines, in
order, with no gaps and no overlaps. Malformed lines are records, never skips, so a count over the
output is a count over the input. This is the property no iCalendar library holds: a strict parser
raises on the first bad line and a lenient one drops it (.claude/design/W247-icsstruct.md).

⚑ NESTING IS REPAIRED THE WAY A READER MEANS IT, AND THE REPAIR IS REPORTED. An `END:X` whose `X`
is open deeper in the stack closes `X`, and every component still open above it is unclosed: its
`BEGIN` line becomes a `Malformed` record. An `END:X` with no open `X` is a stray and is itself
`Malformed`. A component still open at end of input is unclosed the same way. Life's fixture 06
(an `END:VCALENDAR` over an open VEVENT) is the case this rule was written against.

Both line terminators are accepted: CRLF, which RFC 5545 requires and real exports produce, and
bare LF, which hand-edited files have.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

type Nesting = tuple[tuple[str, int], ...]
type Params = tuple[tuple[str, str], ...]

_ORPHAN = "continuation with nothing to fold onto"


@dataclass(frozen=True, slots=True)
class ContentLine:
    """One unfolded content line. `path` names each enclosing component with its ordinal."""

    first: int
    last: int
    raw: tuple[str, ...]
    path: Nesting
    name: str
    params: Params
    value: str


@dataclass(frozen=True, slots=True)
class Malformed:
    """Physical lines that are not a well-formed, well-nested content line. Never skipped."""

    first: int
    last: int
    raw: tuple[str, ...]
    path: Nesting
    reason: str


type Record = ContentLine | Malformed


@dataclass(frozen=True, slots=True)
class Split:
    """A content line split into its three parts, names upper-cased (RFC 5545 §3.1)."""

    name: str
    params: Params
    value: str


@dataclass(frozen=True, slots=True)
class _Logical:
    first: int
    last: int
    raw: tuple[str, ...]


def physical_lines(text: str) -> list[str]:
    """Split on LF, dropping one CR before each LF, and drop the empty piece after a final LF.

    ⚑ NOT `str.splitlines`, which also splits on form feed, vertical tab and U+2028 — characters
    that can sit inside a value, and whose split would invent a physical line.

    Returns:
        the physical lines, without terminators.

    """
    pieces = text.split("\n")
    if not pieces[-1]:
        pieces.pop()
    return [p.removesuffix("\r") for p in pieces]


def _outside_quotes(text: str, stops: str) -> int:
    """Find the first character of `stops` that is not inside a double-quoted run.

    Returns:
        its index, or -1.

    """
    quoted = False
    for i, ch in enumerate(text):
        if ch == '"':
            quoted = not quoted
        elif not quoted and ch in stops:
            return i
    return -1


def split_content_line(line: str) -> Split | str:
    """Split one unfolded line into name, parameters and value.

    ⚑ THE SPLIT IS THE FIRST COLON OUTSIDE QUOTES, NOT THE FIRST COLON. A quoted parameter value
    may hold a colon (`ATTENDEE;CN="Room: 4":mailto:...`); the value may hold any number.

    Returns:
        the split, or the reason it is malformed.

    """
    colon = _outside_quotes(line, ":")
    if colon < 0:
        return "no colon outside quotes, so no value"
    head, value = line[:colon], line[colon + 1 :]
    parts: list[str] = []
    while (semi := _outside_quotes(head, ";")) >= 0:
        parts.append(head[:semi])
        head = head[semi + 1 :]
    parts.append(head)
    name, *raw_params = parts
    if not name:
        return "empty property name"
    params: list[tuple[str, str]] = []
    for param in raw_params:
        key, eq, pval = param.partition("=")
        if not eq or not key:
            return f"parameter {param!r} is not NAME=VALUE"
        params.append((key.upper(), pval))
    return Split(name.upper(), tuple(params), value)


def _logical(lines: list[str]) -> list[_Logical | Malformed]:
    """Group physical lines into logical lines by unfolding continuations.

    Returns:
        one entry per logical line, or a `Malformed` for a line that cannot start or join one.

    """
    out: list[_Logical | Malformed] = []
    for number, line in enumerate(lines, start=1):
        if line[:1] in {" ", "\t"}:
            prev = out[-1] if out else None
            if isinstance(prev, _Logical):
                out[-1] = _Logical(prev.first, number, (*prev.raw, line))
                continue
            out.append(Malformed(number, number, (line,), (), _ORPHAN))
        elif not line:
            out.append(Malformed(number, number, (line,), (), "empty line"))
        else:
            out.append(_Logical(number, number, (line,)))
    return out


def _unfold(raw: tuple[str, ...]) -> str:
    """Join a logical line's physical lines, dropping each continuation's one leading blank.

    Returns:
        the unfolded content line.

    """
    return raw[0] + "".join(r[1:] for r in raw[1:])


class _Nester:
    """The open-component stack, and the records whose BEGIN it may later mark unclosed."""

    def __init__(self) -> None:
        self.records: list[Record] = []
        # Each open component: its name, its ordinal among same-named siblings, its BEGIN's index.
        self.stack: list[tuple[str, int, int]] = []
        self.ordinals: dict[tuple[Nesting, str], int] = {}

    def path(self) -> Nesting:
        return tuple((name, ordinal) for name, ordinal, _ in self.stack)

    def unclose(self, depth: int) -> None:
        """Pop every component above `depth`, turning its BEGIN record into a `Malformed`."""
        while len(self.stack) > depth:
            name, _, index = self.stack.pop()
            begin = self.records[index]
            reason = f"BEGIN:{name} is never closed"
            self.records[index] = Malformed(begin.first, begin.last, begin.raw, begin.path, reason)

    def end(self, line: _Logical, split: Split) -> None:
        target = split.value.upper()
        names = [name for name, _, _ in self.stack]
        if target not in names:
            reason = f"END:{target} with no open BEGIN"
            self.records.append(Malformed(line.first, line.last, line.raw, self.path(), reason))
            return
        depth = len(names) - 1 - names[::-1].index(target)
        self.unclose(depth + 1)
        self.content(line, split)
        self.stack.pop()

    def content(self, line: _Logical, split: Split) -> None:
        path = self.path()
        self.records.append(
            ContentLine(
                line.first, line.last, line.raw, path, split.name, split.params, split.value
            )
        )

    def begin(self, line: _Logical, split: Split) -> None:
        self.content(line, split)
        name = split.value.upper()
        key = (self.path(), name)
        self.ordinals[key] = self.ordinals.get(key, 0) + 1
        self.stack.append((name, self.ordinals[key], len(self.records) - 1))


def lex(text: str) -> tuple[Record, ...]:
    """Lex a whole `.ics` text into records whose spans partition its physical lines.

    Returns:
        the records, in input order.

    """
    nester = _Nester()
    for item in _logical(physical_lines(text)):
        if isinstance(item, Malformed):
            nester.records.append(replace(item, path=nester.path()))
            continue
        split = split_content_line(_unfold(item.raw))
        if isinstance(split, str):
            nester.records.append(Malformed(item.first, item.last, item.raw, nester.path(), split))
        elif split.name == "END":
            nester.end(item, split)
        elif split.name == "BEGIN":
            nester.begin(item, split)
        else:
            nester.content(item, split)
    nester.unclose(0)
    return tuple(nester.records)

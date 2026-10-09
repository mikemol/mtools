# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""A real parser for paperkit's bibliography format, ported from paperkit's `bibparse`.

⚑ WHY THIS EXISTS, AND WHY A SCANNER WAS NOT ENOUGH. paperkit's `bib.parse` once read entries
with a regex (`@\w+\{...(.*?)\n\}`), which TRUNCATED an entry at the first line-initial `}`: an
entry whose value held a brace at column 0 parsed with ZERO FIELDS while a reader reported
`2 of 2 entries`. A claim with no `check` is excluded from the gate's `warrants` set, so the
defect DISARMED a claim while the gate stayed green. Brace-counting fixed that and then had no
answer for the next question, because a scanner has no grammar to answer from: a `claim` value
whose brace never closes swallows the fields after it. Is that an entry with a long claim and no
check, an entry to skip, or an error? A parser answers by construction: a value that never
closes is a SYNTAX ERROR AT A POSITION, not a swallowed field and not a silent skip.

⚑ THE GRAMMAR IS THE CORPUS'S, NOT BIBTEX'S. paperkit censused all 28 of its bibs before
writing a line. ABSENT from the whole corpus: `@string`, `@preamble`, `@comment`, paren-delimited
entries `@misc(...)`, `#` concatenation, and any quoted or bare value. Present: brace values,
nested braces, LaTeX-escaped braces, trailing commas, one `@` inside a value. So the language is
small and the parser refuses everything outside it BY NAME rather than mis-parsing it.

⚑ THE `%` COMMENT IS PAPERKIT'S, NOT BIBTEX'S, and it is stripped by the LEXER, before any entry
is seen. Real BibTeX has no comment syntax; text between entries is simply ignored, which is why
a bare `@` in that text starts an entry and a conforming parser then demands a brace.

This port is faithful except for three mechanical changes: the exception takes a `Position`
rather than three positional arguments, every function states its return in a docstring, and
Greek tag glyphs are written in prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

_EXCERPT_WIDTH = 100
_BLANKS = " \t\r\n"
_NAME_PUNCTUATION = "-_.:/+"
_UNSUPPORTED_TYPES = ("string", "preamble", "comment")


class Position(NamedTuple):
    """Where in which source a diagnostic points."""

    path: str
    line: int
    col: int


class BibSyntaxError(SyntaxError):
    """A parse failure that NAMES ITS POSITION.

    ⚑ A SyntaxError subclass on purpose: a malformed bib is a broken FILE, and the engine's own
    doctrine is that a cannot-parse must not be reported as a result.
    """

    def __init__(self, msg: str, where: Position, excerpt: str = "") -> None:
        """Record the message and the position it was found at."""
        self.path = str(where.path)
        self.lineno = where.line
        self.offset = where.col
        detail = f"{where.path}:{where.line}:{where.col}: {msg}"
        if excerpt:
            detail += f"\n    {excerpt.strip()[:_EXCERPT_WIDTH]}"
        super().__init__(detail)


@dataclass
class Entry:
    """One parsed entry: its type, key, fields, where it started, and the text it spans.

    `start` and `end` are character offsets into the parsed text: `text[start:end]` is the
    entry's own text, from its `@` through its closing `}`, byte for byte, with the trivia
    between entries (whitespace, `%` comments) outside it. A caller that edits a bib as TEXT
    (drop an entry, keep the rest untouched) needs exactly that, and a parser that only returned
    the fields could not say which bytes to drop (mtools:W860). Both are 0 for an entry built
    by hand rather than parsed.
    """

    typ: str
    key: str
    fields: dict[str, str] = field(default_factory=dict)
    line: int = 0
    start: int = 0
    end: int = 0

    # Field ORDER is preserved (dicts are ordered): a parser that returned an unordered mapping
    # would make any projection depend on hash seeding.


class _Lexer:
    """Position-tracking character reader. Owns line/col so every error can name its place."""

    def __init__(self, text: str, path: str = "<bib>") -> None:
        """Start at the first character of `text`, line 1, column 1."""
        self.t = text
        self.path = path
        self.i = 0
        self.line = 1
        self.col = 1

    def eof(self) -> bool:
        """Report whether every character has been consumed.

        Returns:
            True at the end of the text.

        """
        return self.i >= len(self.t)

    def peek(self) -> str:
        """Look at the next character without consuming it.

        Returns:
            The next character, or the empty string at the end.

        """
        return self.t[self.i] if self.i < len(self.t) else ""

    def next(self) -> str:
        """Consume one character, advancing the line and column.

        Returns:
            The consumed character.

        """
        c = self.t[self.i]
        self.i += 1
        if c == "\n":
            self.line, self.col = self.line + 1, 1
        else:
            self.col += 1
        return c

    def err(self, msg: str) -> BibSyntaxError:
        """Build a syntax error at the current position, quoting the current line.

        Returns:
            The error, ready to raise.

        """
        nl = self.t.rfind("\n", 0, self.i) + 1
        end = self.t.find("\n", self.i)
        return BibSyntaxError(
            msg,
            Position(self.path, self.line, self.col),
            self.t[nl : end if end >= 0 else len(self.t)],
        )

    def skip_trivia(self) -> None:
        """Consume whitespace and `%` comments, the only things allowed between entries.

        ⚑ A `%` comment is consumed HERE, in the lexer, so the entry grammar never sees one.
        That is what makes `% ... [@key] ...` harmless to THIS parser while a conforming BibTeX
        parser refuses it: the comment is paperkit's extension, and the lexer is where an
        extension belongs.
        """
        while not self.eof():
            c = self.peek()
            if c in _BLANKS:
                self.next()
            elif c == "%":
                while not self.eof() and self.peek() != "\n":
                    self.next()
            else:
                return

    def escaped(self) -> bool:
        """Report whether `i` is preceded by an ODD run of backslashes (LaTeX-escaped).

        Returns:
            True when the character at `i` is escaped.

        """
        n, j = 0, self.i - 1
        while j >= 0 and self.t[j] == "\\":
            n += 1
            j -= 1
        return n % 2 == 1


def _name(lx: _Lexer, what: str) -> str:
    """Parse an identifier: entry type, key, or field name.

    A missing identifier is a `BibSyntaxError` at the current position.

    Returns:
        The identifier text.

    """
    start = lx.i
    while not lx.eof() and (lx.peek().isalnum() or lx.peek() in _NAME_PUNCTUATION):
        lx.next()
    if lx.i == start:
        msg = f"expected {what}"
        raise lx.err(msg)
    return lx.t[start : lx.i]


def _brace_value(lx: _Lexer) -> str:
    """Parse a `{...}` value, brace-counted, LaTeX-escapes skipped.

    ⚑ THIS IS WHERE THE RUNAWAY CASE IS DECIDED. If the braces never balance we reach EOF, and
    that is a syntax error naming the line the value OPENED on, not a value that silently
    swallowed every field after it.

    Returns:
        The text between the outer braces, verbatim.

    Raises:
        BibSyntaxError: The opening brace is never closed.

    """
    opened = Position(lx.path, lx.line, lx.col)
    lx.next()  # the caller already confirmed this is `{` via peek()
    depth, start = 1, lx.i
    while not lx.eof():
        c = lx.peek()
        if c in "{}" and not lx.escaped():
            if c == "{":
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    v = lx.t[start : lx.i]
                    lx.next()
                    return v
        lx.next()
    msg = (
        "unterminated value: the `{` opened here is never closed, so every field after it is "
        "swallowed into this one"
    )
    raise BibSyntaxError(msg, opened)


def _entry_header(lx: _Lexer) -> tuple[str, str]:
    """Parse `@type{key,`, lowercasing and validating the type.

    A paren-delimited entry, `@string`, `@preamble`, `@comment` or a malformed header is a
    `BibSyntaxError` at the current position.

    Returns:
        The lowercased type and the key.

    """
    lx.next()  # the caller already confirmed this is `@` via peek()
    typ = _name(lx, "an entry type after `@`")
    lx.skip_trivia()
    if lx.peek() == "(":
        msg = (
            f"paren-delimited entries `@type(...)` are not supported: no bib in this "
            f"corpus uses one; write `@{typ}{{...}}` instead"
        )
        raise lx.err(msg)
    if lx.peek() != "{":
        msg = f"expected `{{` after `@{typ}`"
        raise lx.err(msg)
    lx.next()
    lx.skip_trivia()
    low = typ.lower()
    if low in _UNSUPPORTED_TYPES:
        msg = (
            f"`@{low}` is not supported: no bib in this corpus uses one, and "
            "supporting it silently would inherit a BibTeX feature paperkit has never "
            "needed; remove it or state the case for it"
        )
        raise lx.err(msg)
    key = _name(lx, "an entry key")
    lx.skip_trivia()
    if lx.peek() != ",":
        msg = f"expected `,` after the key `{key}`"
        raise lx.err(msg)
    lx.next()
    return low, key


def _entry_fields(lx: _Lexer, e: Entry, line: int) -> None:
    """Parse the `name = {value},` list up to the entry's closing `}`, filling `e.fields`.

    Raises:
        BibSyntaxError: The entry never closes, a field is malformed, or a field repeats.

    """
    while True:
        lx.skip_trivia()
        if lx.eof():
            msg = f"unterminated entry `{e.key}`: no closing `}}`"
            raise BibSyntaxError(msg, Position(lx.path, line, 1))
        if lx.peek() == "}":
            lx.next()
            return
        fpos = Position(lx.path, lx.line, lx.col)
        fname = _name(lx, f"a field name in `{e.key}`")
        lx.skip_trivia()
        if lx.peek() != "=":
            msg = f"expected `=` after field `{fname}` in `{e.key}`"
            raise lx.err(msg)
        lx.next()
        lx.skip_trivia()
        if lx.peek() != "{":
            msg = (
                f"field `{fname}` in `{e.key}` must have a `{{...}}` value: quoted, bare and "
                "concatenated values are not supported (no bib in this corpus uses one)"
            )
            raise lx.err(msg)
        val = _brace_value(lx)
        if fname in e.fields:
            msg = (
                f"field `{fname}` is given twice in `{e.key}`: the second would silently "
                "replace the first"
            )
            raise BibSyntaxError(msg, fpos)
        # ⚑ THE VALUE IS CARRIED VERBATIM, with no whitespace normalisation: `join = {. }`
        # MEANS the trailing space, the connector rendered between two clauses.
        e.fields[fname] = val
        lx.skip_trivia()
        if lx.peek() == ",":
            lx.next()  # a trailing comma before `}` is fine
        elif lx.peek() != "}":
            msg = f"expected `,` or `}}` after field `{fname}` in `{e.key}`"
            raise lx.err(msg)


def _entry(lx: _Lexer) -> Entry:
    """Parse one whole entry.

    Returns:
        The entry, with the line it started on and the span of text it covers.

    """
    line, start = lx.line, lx.i
    low, key = _entry_header(lx)
    e = Entry(typ=low, key=key, line=line, start=start)
    _entry_fields(lx, e, line)
    e.end = lx.i
    return e


def parse(text: str, path: str = "<bib>") -> list[Entry]:
    """Parse every entry in `text`, in file order.

    Any malformed input is a `BibSyntaxError` naming its position.

    Returns:
        The entries.

    """
    lx = _Lexer(text, path)
    out: list[Entry] = []
    while True:
        lx.skip_trivia()
        if lx.eof():
            return out
        if lx.peek() != "@":
            msg = (
                "expected `@` to start an entry: text between entries must be a `%` "
                "comment (paperkit's extension) or whitespace; a bare `@` in prose "
                "starts an entry for a conforming BibTeX parser"
            )
            raise lx.err(msg)
        out.append(_entry(lx))

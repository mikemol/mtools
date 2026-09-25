# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The ⚑ incident-log census and its preservation gate.

Cleanroomed from substrate's `scratch/_pycodemod_commentary.py` (W43). These read the
COMMENTARY — the marked lines that are a corpus's incident log — not its code structure, and one
of them is a GATE: `commentary_lost` names what a split dropped.

What moved and what did not:

⚑⚑ AN UNREADABLE FILE IS REPORTED, NEVER SKIPPED. The origin read with `errors="replace"` and
passed over an `OSError`, so a file it could not read contributed a silent zero to the census —
the census whose purpose is to prove nothing went missing. Every reader here returns `unread`.

⚑⚑ ONE MATCHER ON BOTH SIDES OF THE GATE. The origin's `commentary_lost` matched the BEFORE side
with a bare substring test and the AFTER side with the bounded `mark_hit`, so a widened mark such
as `NB` counted "UNBALANCED" before and not after — a spurious LOST line manufactured by the gate
itself. Both sides now go through `mark_hit`.

⚑ NO ROOT, NO GIT. The origin's gate shelled out to `git show` against a module-level `ROOT`.
Here the caller passes the tree and a `show` callable that returns a path's text at the baseline,
or None when the path is absent there; the paths that were absent are REPORTED, so "nothing
existed before" is visible rather than inferred from an empty diff.

⚑ A DOCSTRING IS THE FIRST STATEMENT OF A MODULE, CLASS OR DEF — NOTHING ELSE. The origin took the
first string of ANY block body, so a marked string opening an `if` body was filed as documentation
while it is executable payload.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

# The glyphs that mark a line of incident commentary. A tuple a caller WIDENS, never a literal
# buried in a comprehension: this tooling reads several checkouts with different conventions.
COMMENTARY_MARKS = ("⚑",)

# A symbol an incident CITES: a backticked flag or identifier. The markup is the convention, so a
# capitalised word in prose is emphasis, not a citation.
_BACKTICKED = re.compile(r"`(--?[A-Za-z][\w-]*|[A-Za-z_][\w.]*(?:\(\))?)`")

_QUOTES = ('"""', "'''")
_KEY_STRIP = "#:'\" "

type Place = tuple[str, int]


@dataclass(frozen=True, slots=True)
class Hit:
    """One marked line: where it is, and its normalized sentence."""

    path: str
    line: int
    text: str


@dataclass(frozen=True, slots=True)
class CensusRow:
    """One file's share of the log: marked lines, and how many distinct sentences."""

    path: str
    lines: int
    distinct: int


@dataclass(frozen=True, slots=True)
class Census:
    """The per-file counts, every sentence's places, and the files that could not be read."""

    rows: list[CensusRow] = field(default_factory=list)
    texts: dict[str, list[Place]] = field(default_factory=dict)
    nfiles: int = 0
    unread: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Kinds:
    """Each marked line by where it lives; `unparsed` when the tokenizer could not say."""

    comment: list[Hit] = field(default_factory=list)
    docstring: list[Hit] = field(default_factory=list)
    executable: list[Hit] = field(default_factory=list)
    unparsed: list[Hit] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Block:
    """One incident as a BLOCK: its extent, the def or class that owns it, what it cites."""

    path: str
    start: int
    end: int
    enclosing: str | None
    cited: list[str]
    text: str


@dataclass(frozen=True, slots=True)
class Blocks:
    """The incident blocks found, and the files that could not be read."""

    found: list[Block] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Lost:
    """What a split dropped and gained, by sentence, and where each dropped sentence came from.

    ⚑ `absent_before` NAMES THE PATHS THE BASELINE DID NOT HAVE: a new sibling is absent by
    construction, and a whole tree absent at a wrong ref is the same shape — the caller can tell
    them apart only if the list is shown.
    """

    lost: list[str]
    gained: list[str]
    n_before: int
    n_after: int
    origins: dict[str, list[str]]
    absent_before: list[str]
    unread: list[str]


def mark_hit(mark: str, line: str) -> bool:
    r"""Report whether `mark` occurs in `line` AS A MARK, rather than inside a word.

    ⚑⚑ A BARE SUBSTRING TEST FIRES A TWO-LETTER MARK ON ANY WORD CONTAINING IT: `NB` inside
    "UNBALANCED". ⚑ THE BOUNDARY IS CONDITIONAL, because a glyph is not a word character: `\b`
    around `⚑` would never match and report the corpus empty. Alphanumeric ends get a boundary;
    symbolic ends are matched raw. An empty mark matches nothing.

    Returns:
        whether the mark is present as a mark.

    """
    if not mark:
        return False
    lead = r"\b" if mark[0].isalnum() else ""
    trail = r"\b" if mark[-1].isalnum() else ""
    return re.search(lead + re.escape(mark) + trail, line) is not None


def commentary_key(line: str) -> str:
    """Normalize one marked line to its SENTENCE.

    ⚑ A RELOCATION RE-INDENTS AND RE-COMMENTS: moving a note from a def body to a `#` block
    changes its bytes and not its sentence. Leading sigils and quotes are stripped and every
    whitespace run collapsed, so a moved line is not reported lost-and-gained at once.

    Returns:
        the normalized sentence.

    """
    return re.sub(r"\s+", " ", line.strip().lstrip(_KEY_STRIP).strip())


def _marked(line: str, marks: Sequence[str]) -> bool:
    return any(mark_hit(m, line) for m in marks)


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def commentary_census(paths: Sequence[str], marks: Sequence[str] = COMMENTARY_MARKS) -> Census:
    """Count the log per file, and index every sentence by its places.

    ⚑ EVERY LINE CARRYING A MARK COUNTS, not only comment lines: a corpus writes notes in `#`
    comments, docstrings and the strings a CLI prints, and a split that drops a printed caveat must
    not read as clean.

    Returns:
        the census, with the files that could not be read.

    """
    out = Census(nfiles=len(paths))
    for path in paths:
        src = _read(path)
        if src is None:
            out.unread.append(path)
            continue
        count, seen = 0, set[str]()
        for number, line in enumerate(src.splitlines(), 1):
            if not _marked(line, marks):
                continue
            count += 1
            key = commentary_key(line)
            seen.add(key)
            out.texts.setdefault(key, []).append((path, number))
        if count:
            out.rows.append(CensusRow(path, count, len(seen)))
    return out


def _token_lines(src: str) -> tuple[set[int], set[int]] | None:
    comments, strings = set[int](), set[int]()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                comments.update(range(tok.start[0], tok.end[0] + 1))
            elif tok.type == tokenize.STRING:
                strings.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, SyntaxError):
        return None
    return comments, strings


def _docstring_lines(src: str) -> set[int]:
    out = set[int]()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if ast.get_docstring(node, clean=False) is None:
            continue
        first = node.body[0]
        out.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return out


def commentary_kinds(paths: Sequence[str], marks: Sequence[str] = COMMENTARY_MARKS) -> Kinds:
    """File each marked line as comment, docstring or EXECUTABLE — a string the program emits.

    ⚑⚑ AN EXECUTABLE MARK IS BEHAVIOUR, NOT DOCUMENTATION: a refusal message or a test named by its
    claim. ⚑ `tokenize` DRAWS THE LINE, not a regex; a file that will not tokenize files its marks
    under `unparsed` rather than dropping them.

    Returns:
        the marked lines by kind, with the files that could not be read.

    """
    out = Kinds()
    for path in paths:
        src = _read(path)
        if src is None:
            out.unread.append(path)
            continue
        hits = [
            Hit(path, number, commentary_key(line))
            for number, line in enumerate(src.splitlines(), 1)
            if _marked(line, marks)
        ]
        tokens = _token_lines(src) if hits else None
        if tokens is None:
            out.unparsed.extend(hits)
            continue
        comments, strings = tokens
        docs = _docstring_lines(src)
        for hit in hits:
            if hit.line in comments or hit.line not in strings:
                out.comment.append(hit)
            elif hit.line in docs:
                out.docstring.append(hit)
            else:
                out.executable.append(hit)
    return out


def scope_index(src: str) -> dict[int, str]:
    """Map each line to the qualified def or class that OWNS it; innermost wins.

    ⚑ FROM `ast`, NOT INDENTATION. A parent is visited before its children, so overwriting yields
    the innermost owner in one pass. Source that does not parse owns nothing.

    Returns:
        line number to qualified name.

    """
    out: dict[int, str] = {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    stack: list[tuple[ast.AST, str]] = [(tree, "")]
    while stack:
        node, prefix = stack.pop(0)
        for child in ast.iter_child_nodes(node):
            name = prefix
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}.{child.name}" if prefix else child.name
                for number in range(child.lineno, (child.end_lineno or child.lineno) + 1):
                    out[number] = name
            stack.append((child, name))
    return out


def cited_symbols(text: str) -> list[str]:
    """Return the backticked flags and identifiers a block names, sorted and distinct.

    Returns:
        the cited symbols.

    """
    out = set[str]()
    for match in _BACKTICKED.finditer(text):
        got = match.group(1)
        if isinstance(got, str):
            out.add(got)
    return sorted(out)


def _block_end(lines: list[str], start: int, marks: Sequence[str]) -> int:
    end = start + 1
    while end < len(lines):
        text = lines[end].strip()
        if not text or text.startswith(_QUOTES) or _marked(text, marks):
            break
        end += 1
    return end


def commentary_blocks(paths: Sequence[str], marks: Sequence[str] = COMMENTARY_MARKS) -> Blocks:
    """Group each incident into its BLOCK, with its owner and the symbols it cites.

    ⚑⚑⚑ THE LINE IS NOT THE UNIT OF AN INCIDENT: only a paragraph's first line carries the mark,
    so a line census sees a fragment. A block runs to the first blank line, closing quote or next
    mark — never to the next mark alone, or every block would be one line long. ⚑ The backticked
    symbols are the edge from a defect to the tool that answers it.

    Returns:
        the blocks found, with the files that could not be read.

    """
    out = Blocks()
    for path in paths:
        src = _read(path)
        if src is None:
            out.unread.append(path)
            continue
        lines = src.splitlines()
        owners = scope_index(src)
        index = 0
        while index < len(lines):
            if not _marked(lines[index], marks):
                index += 1
                continue
            end = _block_end(lines, index, marks)
            text = " ".join(commentary_key(x) for x in lines[index:end])
            out.found.append(
                Block(path, index + 1, end, owners.get(index + 1), cited_symbols(text), text)
            )
            index = end
    return out


def commentary_lost(
    paths: Sequence[str],
    root: Path,
    show: Callable[[str], str | None],
    marks: Sequence[str] = COMMENTARY_MARKS,
) -> Lost:
    """Name the marked sentences a SPLIT dropped: a set difference across a revision.

    ⚑ COUNTING IS NOT ENOUGH: a split that drops one note and adds another keeps the total. `show`
    returns a path's text at the baseline (relative to `root`), or None when the path is absent
    there — a new sibling is absent by construction, so absence contributes nothing, and is listed.
    ⚑ The ORIGIN of every lost sentence is returned, because a baseline behind the split's real
    starting point attributes someone else's removal to it.

    Returns:
        the lost and gained sentences, the counts, their origins and the absent paths.

    """
    before: dict[str, list[str]] = {}
    absent: list[str] = []
    for path in paths:
        rel = Path(path).absolute().relative_to(root.absolute()).as_posix()
        old = show(rel)
        if old is None:
            absent.append(rel)
            continue
        for line in old.splitlines():
            if _marked(line, marks):
                before.setdefault(commentary_key(line), []).append(rel)
    after = commentary_census(paths, marks)
    return Lost(
        lost=sorted(set(before) - set(after.texts)),
        gained=sorted(set(after.texts) - set(before)),
        n_before=sum(len(v) for v in before.values()),
        n_after=sum(len(v) for v in after.texts.values()),
        origins=before,
        absent_before=absent,
        unread=after.unread,
    )

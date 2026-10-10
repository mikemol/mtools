# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-htmlstruct VERB FILE [ARG]`: the HTML and MHTML readers as a command (mtools:W908).

Verbs: `outline`, `links`, `tables`, `meta` and `text FILE ID` read an HTML file, or the root part
of an `.mhtml`/`.mht` archive; `parts FILE` lists an archive and `part FILE LOCATION` writes one
part's decoded bytes. Output is one record per line, fields separated by a tab.

⚑ EXIT CODES SAY WHICH KIND OF NOTHING THIS IS: 0 an answer; 1 a MISS (a valid question with no
answer: an id or a location that names nothing); 2 a usage refusal (an unknown verb, a wrong
operand count, a file that is not there); 3 a SKIP (the input is not a document: bytes that are not
text, or a file that is not an archive). An empty answer is never printed for any of the last
three: a caller must be able to tell "no headings" from "could not read it".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.htmlstruct import links, mhtml, outline, tables, text, tree
from mikemol.htmlstruct import meta as metadata

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

EXIT_OK = 0
EXIT_MISS = 1
EXIT_USAGE = 2
EXIT_SKIP = 3

_STDOUT_FD = 1
_ARCHIVE_SUFFIXES = frozenset({".mhtml", ".mht"})
_FIXED_ARGS = 2
_USAGE = (
    "usage: mikemol-htmlstruct outline|links|tables|meta FILE\n"
    "       mikemol-htmlstruct text FILE ID\n"
    "       mikemol-htmlstruct parts FILE\n"
    "       mikemol-htmlstruct part FILE LOCATION\n"
)


def _outline(root: tree.Node) -> list[str]:
    return [f"{h.level}\t{h.ident or '-'}\t{h.text}" for h in outline.outline(root)]


def _links(root: tree.Node) -> list[str]:
    return [f"{k.href}\t{k.rel or '-'}\t{k.text}" for k in links.links(root)]


def _tables(root: tree.Node) -> list[str]:
    out: list[str] = []
    for number, table in enumerate(tables.tables(root), start=1):
        out.append(f"TABLE {number}")
        out.extend("\t".join(f"*{c.text}" if c.header else c.text for c in row) for row in table)
    return out


def _meta(root: tree.Node) -> list[str]:
    found = metadata.meta(root)
    head = [] if found.title is None else [f"title\t{found.title}"]
    return [*head, *(f"{key}\t{value}" for key, value in found.entries)]


_HTML_VERBS: dict[str, Callable[[tree.Node], list[str]]] = {
    "outline": _outline,
    "links": _links,
    "tables": _tables,
    "meta": _meta,
}
_OPERANDS = {**dict.fromkeys(_HTML_VERBS, 0), "text": 1, "parts": 0, "part": 1}


def _well_formed(args: Sequence[str]) -> bool:
    """Say whether the arguments are a known verb, a file, and exactly the operands it takes.

    Returns:
        True when the verb is known and the operand count matches.

    """
    if len(args) < _FIXED_ARGS or args[0] not in _OPERANDS:
        return False
    return len(args) - _FIXED_ARGS == _OPERANDS[args[0]]


def _document(path: Path) -> tree.Node | tree.Skip:
    data = path.read_bytes()
    if path.suffix.lower() not in _ARCHIVE_SUFFIXES:
        return tree.parse(data)
    archive = mhtml.read(data)
    return archive if isinstance(archive, tree.Skip) else mhtml.root_tree(archive)


def _skip(reason: str) -> int:
    sys.stderr.write(f"SKIP {reason}\n")
    return EXIT_SKIP


def _lines(rows: Sequence[str]) -> int:
    sys.stdout.write("".join(f"{row}\n" for row in rows))
    return EXIT_OK


def _emit(payload: bytes) -> None:
    """Write raw bytes to standard output through its descriptor, text buffer flushed first."""
    sys.stdout.flush()
    pending = memoryview(payload)
    while pending:
        pending = pending[os.write(_STDOUT_FD, pending) :]


def _archive_verb(verb: str, path: Path, operand: str) -> int:
    archive = mhtml.read(path.read_bytes())
    if isinstance(archive, tree.Skip):
        return _skip(archive.reason)
    if verb == "parts":
        return _lines(
            [f"{p.location or '-'}\t{p.content_type}\t{len(p.payload)}" for p in archive.parts]
        )
    found = mhtml.part_at(archive, operand)
    if isinstance(found, mhtml.Miss):
        sys.stderr.write(f"MISS no part at {found.location}\n")
        return EXIT_MISS
    _emit(found.payload)
    return EXIT_OK


def _html_verb(verb: str, path: Path, operand: str) -> int:
    root = _document(path)
    if isinstance(root, tree.Skip):
        return _skip(root.reason)
    if verb == "text":
        found = text.by_id(root, operand)
        if isinstance(found, text.Miss):
            sys.stderr.write(f"MISS no element has id {found.ident}\n")
            return EXIT_MISS
        return _lines([found])
    return _lines(_HTML_VERBS[verb](root))


def main(argv: Sequence[str] | None = None) -> int:
    """Run one verb over one file.

    Returns:
        0 for an answer, 1 for a miss, 2 for a usage refusal, 3 for a skip.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not _well_formed(args):
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    verb, path, operand = args[0], Path(args[1]), "".join(args[_FIXED_ARGS:])
    if not path.is_file():
        sys.stderr.write(f"mikemol-htmlstruct: {path} is not a file\n")
        return EXIT_USAGE
    if verb in {"parts", "part"}:
        return _archive_verb(verb, path, operand)
    return _html_verb(verb, path, operand)

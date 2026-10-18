# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Audit a memory directory against its project's transcripts, read-only (W1545, W1541).

⚑ THE OPERATOR ASKED FOR THIS VERBATIM (2026-10-18, after el-openglo swarmed on a stale note): the
memory files are audited against the same "verify against the transcript, find the operator
ruling" principles as a card. For each note this prints one row per finding and writes nothing:
a GRANT row for each line that grants a permission or lifts a rule (priority review), a
WARRANTED or UNWARRANTED row for each claimed operator quote (WARRANTED names the record), and
up to `SHOWN` POSSIBLY-SUPERSEDED rows naming the newest later utterances on the note's subject.

⚑ THE TRANSCRIPTS ARE THE MEMORY DIRECTORY'S PARENT (`~/.claude/projects/<project>/memory`), the
top-level `*.jsonl` only: a subagent's transcript is not the operator's. Each session reviews its
own directory and corrects or deletes; nothing here edits a note.
CONSUMED BY: the `--audit-memory` mode of `mikemol-transcriptstruct`.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.transcriptstruct import memclaims, memfind, memgrants
from mikemol.transcriptstruct.memfind import Utterance
from mikemol.transcriptstruct.query import grep_prose
from mikemol.transcriptstruct.records import read_path

SHOWN = 3
GRANT = "GRANT"
SUPERSEDED = "POSSIBLY-SUPERSEDED"
LINKED_NEWER = "LINKED-NEWER"
LINK_OVERLAP = 2
ELSEWHERE = "ELSEWHERE"
_UNFOUND = frozenset({memfind.UNWARRANTED, memfind.RELAYED})
INDEX = "MEMORY.md"
_DATE = re.compile(r"\b20[0-9]{2}-[0-9]{2}-[0-9]{2}\b")
_SUBJECT = re.compile(r"^(?:name|description):")
_LINK = re.compile(r"\[\[([^\]\n]+)\]\]")
_MODIFIED = re.compile(r"^\s*modified:\s*(\S+)", re.MULTILINE)
_DETAIL = 100
_END_OF_DAY = "T99"


@dataclass(frozen=True)
class Row:
    """One finding about one line of one note."""

    note: str
    line: int
    status: str
    detail: str
    claim: str = ""

    def text(self) -> str:
        """Spell the finding as one line.

        Returns:
            `<note>:<line>  <STATUS>  <detail>`.

        """
        return f"{self.note}:{self.line}  {self.status}  {self.detail}"


def utterances_of(project: Path) -> list[Utterance]:
    """Collect what the operator said in a project's top-level transcripts.

    Returns:
        every human utterance, file by file in name order.

    """
    found: list[Utterance] = []
    for path in sorted(project.glob("*.jsonl")):
        result = grep_prose(read_path(path), ".", speakers={"human"})
        found.extend(Utterance(str(path), h.line, h.uuid, h.at, h.text) for h in result.hits)
    return found


def _subject(text: str) -> frozenset[str]:
    """Take the key terms of a note's name and description lines.

    Returns:
        the terms, empty when the note has neither line.

    """
    lines = [raw for raw in text.splitlines() if _SUBJECT.match(raw)]
    return memfind.terms(" ".join(lines))


def _latest(texts: list[str]) -> str:
    """Find the newest date a note's claims mention, as a cut-off past the end of that day.

    Returns:
        `<date>T99` for the newest date, or "" when no claim carries one.

    """
    dates: list[str] = []
    for text in texts:
        dates.extend(cast("list[str]", _DATE.findall(text)))
    return f"{max(dates)}{_END_OF_DAY}" if dates else ""


def _modified(text: str) -> str:
    """Read a note's `modified:` stamp.

    Returns:
        the stamp, or "" when the note has none.

    """
    found = _MODIFIED.search(text)
    return found.group(1) if found is not None else ""


def linked_newer(name: str, text: str, notes: dict[str, str]) -> list[Row]:
    """Report the notes this one links to that are newer and share its subject.

    ⚑ A LINK IS THE AUTHOR'S OWN CLAIM OF RELATEDNESS (github-8f, 2026-10-18, W1550): when a note
    it points at was modified after it and shares `LINK_OVERLAP` of its key terms, that newer note
    may contradict it, a stronger signal than term overlap with an utterance. It cannot tell
    contradiction from agreement, so the row names the pair for a reviewer.

    Returns:
        one `LINKED-NEWER` row per such link, in link-name order.

    """
    mine = _modified(text)
    subject = _subject(text)
    rows: list[Row] = []
    for link in sorted(set(cast("list[str]", _LINK.findall(text)))):
        other = notes.get(f"{link}.md")
        if other is None or _modified(other) <= mine:
            continue
        if len(subject & _subject(other)) >= LINK_OVERLAP:
            rows.append(Row(name, 0, LINKED_NEWER, f"{link}.md modified {_modified(other)}"))
    return rows


def audit_note(name: str, text: str, utterances: list[Utterance]) -> list[Row]:
    """Audit one note.

    Returns:
        its GRANT rows, then a row per claim, then the newest later utterances on its subject.

    """
    rows = [Row(name, g.line, GRANT, ",".join(g.words)) for g in memgrants.grants(text)]
    claims = memclaims.claims(text)
    for found in (memfind.warrant_for(c, utterances) for c in claims):
        record = found.record
        where = found.claim.text[:_DETAIL]
        if record is not None:
            where = f"{record.path}:{record.line} uuid={record.uuid}"
        unfound = found.claim.text if found.status in _UNFOUND else ""
        rows.append(Row(name, found.claim.line, found.status, where, unfound))
    since = _latest([c.text for c in claims])
    if since:
        later = memfind.superseded_by(_subject(text), since, utterances)
        rows.extend(
            Row(name, 0, SUPERSEDED, f"{u.at} {u.path}:{u.line} uuid={u.uuid}: {u.text[:_DETAIL]}")
            for u in later[:SHOWN]
        )
    return rows


def elsewhere(rows: list[Row], projects: Iterable[Path]) -> list[Row]:
    """Look each unfound quote up in other projects' transcripts, and say where it was found.

    ⚑ A RULING IS OFTEN GIVEN IN ANOTHER SESSION (github-8f, 2026-10-18, W1552): luthen's or
    cassian's transcripts hold words a note in this project's memory quotes, so a quote this
    project's transcripts do not carry is not yet unwarranted. Each project is read only while an
    unfound quote remains, and a quote found becomes `ELSEWHERE <path>:<line> uuid=<uuid>`.

    Returns:
        the rows, with each quote found in another project's transcripts re-stated as ELSEWHERE.

    """
    out = list(rows)
    pending = [i for i, row in enumerate(out) if row.claim]
    for project in projects:
        if not pending:
            break
        utterances = utterances_of(project)
        for i in list(pending):
            row = out[i]
            found = memfind.warrant_for(memclaims.Claim(row.line, "quote", row.claim), utterances)
            if found.record is not None:
                record = found.record
                where = f"{record.path}:{record.line} uuid={record.uuid}"
                out[i] = Row(row.note, row.line, ELSEWHERE, where)
                pending.remove(i)
    return out


def _siblings(memory: Path) -> list[Path]:
    """Name the other projects beside this memory directory's project.

    Returns:
        their directories in name order; empty when the projects directory cannot be listed.

    """
    try:
        beside = sorted(memory.parent.parent.iterdir())
    except OSError:
        return []
    return [p for p in beside if p.is_dir() and p != memory.parent]


def audit(memory: Path) -> list[Row]:
    """Audit every note of a memory directory against its project's transcripts.

    Returns:
        the findings, note by note in name order; `MEMORY.md` is the index and is skipped.

    """
    utterances = utterances_of(memory.parent)
    notes = {p.name: p.read_text(encoding="utf-8") for p in sorted(memory.glob("*.md"))}
    rows: list[Row] = []
    for name, text in notes.items():
        if name != INDEX:
            rows.extend(audit_note(name, text, utterances))
            rows.extend(linked_newer(name, text, notes))
    return elsewhere(rows, _siblings(memory))

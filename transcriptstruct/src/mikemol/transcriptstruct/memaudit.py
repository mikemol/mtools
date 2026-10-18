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
INDEX = "MEMORY.md"
_DATE = re.compile(r"\b20[0-9]{2}-[0-9]{2}-[0-9]{2}\b")
_SUBJECT = re.compile(r"^(?:name|description):")
_DETAIL = 100
_END_OF_DAY = "T99"


@dataclass(frozen=True)
class Row:
    """One finding about one line of one note."""

    note: str
    line: int
    status: str
    detail: str

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
        rows.append(Row(name, found.claim.line, found.status, where))
    since = _latest([c.text for c in claims])
    if since:
        later = memfind.superseded_by(_subject(text), since, utterances)
        rows.extend(
            Row(name, 0, SUPERSEDED, f"{u.at} {u.path}:{u.line} uuid={u.uuid}: {u.text[:_DETAIL]}")
            for u in later[:SHOWN]
        )
    return rows


def audit(memory: Path) -> list[Row]:
    """Audit every note of a memory directory against its project's transcripts.

    Returns:
        the findings, note by note in name order; `MEMORY.md` is the index and is skipped.

    """
    utterances = utterances_of(memory.parent)
    rows: list[Row] = []
    for path in sorted(memory.glob("*.md")):
        if path.name != INDEX:
            rows.extend(audit_note(path.name, path.read_text(encoding="utf-8"), utterances))
    return rows

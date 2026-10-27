# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A hold on a human is lifted by a verified record of the operator's own words (W1525).

Standing 5 says a hold on a human is lifted by the operator, not from a session. Until now the only
lift was a signed ruling (`--lift JWS`, a key the operator rarely uses), so held cards sat after the
operator had already answered in the transcript. The operator ruled (AskUserQuestion, 2026-10-18,
and retyped as their own message at host session 695f3e0a line 77606): a verified transcript
record of their own words, naming the card and attached as its warrant, also releases it.

⚑ THE RECORD IS READ AGAIN AT LIFT TIME, NOT TRUSTED FROM THE QUEUE. A warrant stored on a card is a
claim that a record said something; this module asks the transcript reader whether it did, now:
the record must verify as origin human (`--verify ... --claim operator`), and the same line must
match the card's symbol. A tool result, a peer's message or a record that names another card does
not lift.

⚑ THE READER COMMAND STORED IN A WARRANT IS NEVER RUN. A queue file is editable by any session, so
running a command it names would let a crafted warrant exit 0. The warrant supplies a path, a uuid
and a line; the reader is this module's own, found by name.

⚑ THE HOOK ONLY READS: a lifted row is left out of the held set the policy reads, and the writer
makes the change. A failure to read anything leaves the row held.

CONSUMED BY: `standing_facts.held_symbols`.
"""

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

Run = Callable[[Sequence[str]], tuple[int, str]]

READER_ENV = "TRANSCRIPTSTRUCT_BIN"
READER_NAME = "mikemol-transcriptstruct"
_FILE_PREFIX = "file://"
_URN_PREFIX = "urn:claude:transcript:"
_FRAGMENT = "#"
_ITEM = re.compile(r"^[ \t]*(\d+)[.)][ \t]*", re.MULTILINE)
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{5,}")
_GENERIC = frozenset(
    {"decide", "question", "options", "operator", "should", "whether", "because", "between"}
    | {"before", "after", "which", "there", "their", "about", "would", "could", "being", "using"}
)
_SHARED_NEEDED = 2
_WINDOW = 400
_CHECKOUT = ("github", "mtools", "transcriptstruct", ".venv", "bin", READER_NAME)


def reader_path(env: Mapping[str, str]) -> str | None:
    """Find the transcript reader: the env override, PATH, then the mtools checkout.

    Returns:
        its path, or None when none is found (every hold then stays held).

    """
    named = env.get(READER_ENV)
    on_path = shutil.which(READER_NAME, path=env.get("PATH", ""))
    checkout = Path.home().joinpath(*_CHECKOUT)
    candidates = [Path(p) for p in (named, on_path) if p] + [checkout]
    return next((str(c) for c in candidates if c.is_file()), None)


def run_reader(argv: Sequence[str]) -> tuple[int, str]:
    """Run the transcript reader once.

    Returns:
        (exit code, stdout); (-1, "") when it could not start.

    """
    try:
        done = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    except OSError:
        return -1, ""
    return done.returncode, done.stdout


def cited(warrant: object) -> tuple[str, str, int] | None:
    """Read the record a warrant cites: its transcript path, uuid and line.

    Returns:
        `(path, uuid, line)`, or None when the warrant is not shaped as the writer writes it.

    """
    if not isinstance(warrant, dict):
        return None
    derived = cast("dict[str, object]", warrant).get("prov:wasDerivedFrom")
    if not isinstance(derived, dict):
        return None
    fields = cast("dict[str, object]", derived)
    ident, line = fields.get("@id"), fields.get("mtools:line")
    if not isinstance(ident, str) or not isinstance(line, int):
        return None
    if ident.startswith(_URN_PREFIX):
        # The form the writer writes now: `urn:claude:transcript:<project>/<session>#<uuid>`.
        where, _, found = ident[len(_URN_PREFIX) :].partition(_FRAGMENT)
        home = Path.home() / ".claude" / "projects" / f"{where}.jsonl"
        return (str(home), found, line) if where and found else None
    if not ident.startswith(_FILE_PREFIX):
        return None
    path, _, uuid = ident[len(_FILE_PREFIX) :].partition(_FRAGMENT)
    return (path, uuid, line) if path and uuid else None


def numbered(text: str) -> dict[int, str]:
    """Split a message into its numbered items.

    Returns:
        item number to the item's whole text, up to the next numbered line; the first use of a
        number wins.

    """
    marks = list(_ITEM.finditer(text))
    items: dict[int, str] = {}
    for at, mark in enumerate(marks):
        end = marks[at + 1].start() if at + 1 < len(marks) else len(text)
        items.setdefault(int(str(mark[1])), text[mark.end() : end])
    return items


def _words(text: str) -> set[str]:
    return {str(m[0]).lower() for m in _WORD.finditer(text)} - _GENERIC


def quotes_ask(item: str, ask: str) -> bool:
    """Say whether a numbered question quotes a card's ask.

    ⚑ QUOTING IS SHARED DISTINCTIVE WORDS, NOT A PARAPHRASE JUDGED BY EYE (the operator, host line
    104311: "an answer to a numbered question quoting a card's ask counts as naming it"). Words of
    six letters or more, without the generic ones, that the question and the ask both use; two are
    needed, so a list that merely mentions "ratchet" does not release a card about a stub.

    Returns:
        True when at least two such words are shared.

    """
    return len(_words(item) & _words(ask)) >= _SHARED_NEEDED


def _rows(said: str) -> list[dict[str, object]]:
    # The JSON objects among the reader's lines; its `#` footer and any torn line are skipped.
    rows: list[dict[str, object]] = []
    for raw in said.splitlines():
        if not raw.startswith("{"):
            continue
        try:
            row: object = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(cast("dict[str, object]", row))
    return rows


def answers_ask(reader: str, path: str, line: int, ask: str, run: Run) -> bool:
    """Say whether the human record at `line` answers a numbered question that quotes the ask.

    ⚑ THE QUESTION IS THE ASSISTANT MESSAGE IMMEDIATELY BEFORE THE ANSWER, and only the items the
    answer numbers are read: "2. (a)" answers item 2 of that message and no other.

    Returns:
        True when some item the record answers quotes `ask`; False when the reader fails, the
        record is not found, or no assistant message precedes it within the window.

    """
    start = max(1, line - _WINDOW)
    code, said = run([reader, path, "--prose", "--since", str(start), "--until", str(line)])
    if code != 0:
        return False
    rows = _rows(said)
    answer = next((r for r in rows if r.get("line") == line and r.get("kind") == "human"), None)
    asked = [r for r in rows if r.get("kind") == "assistant" and int(str(r.get("line"))) < line]
    if answer is None or not asked:
        return False
    questions = numbered(str(asked[-1].get("text", "")))
    given = numbered(str(answer.get("text", "")))
    return any(quotes_ask(questions[n], ask) for n in given if n in questions)


def verifies(reader: str, warrant: object, symbol: str, run: Run, ask: str = "") -> bool:
    """Say whether a warrant's record is the operator's own words and names `symbol`.

    With `ask` (the card's title and blocked-on text), a record that answers a numbered question
    quoting it counts as naming the card too (W1525, widened once by the operator, 2026-10-26).

    Returns:
        True when the record verifies as origin human and either its line matches the card's symbol
        or it answers a numbered question that quotes the ask.

    """
    got = cited(warrant)
    if got is None or not symbol:
        return False
    path, uuid, line = got
    code, said = run([reader, path, "--verify", uuid, "--claim", "operator", "--line", str(line)])
    if code != 0:
        return False
    try:
        verdict: object = json.loads(said.splitlines()[0])
    except (ValueError, IndexError):
        return False
    if not isinstance(verdict, dict) or cast("dict[str, object]", verdict).get("ok") is not True:
        return False
    pattern = rf"\b{re.escape(symbol)}\b"
    _code, hits = run(
        [reader, "--human", pattern, "--since", str(line), "--until", str(line), path]
    )
    named = any(row.startswith("{") for row in hits.splitlines())
    return named or (bool(ask) and answers_ask(reader, path, line, ask, run))


def lifted(
    row: Mapping[str, object],
    run: Run = run_reader,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Say whether a held card carries a warrant that lifts its hold.

    Returns:
        True when some warrant on the card verifies now; False when none does or no reader exists.

    """
    warrants = row.get("warrants")
    symbol = row.get("symbol")
    reader = reader_path(os.environ if env is None else env)
    if reader is None or not isinstance(warrants, list) or not isinstance(symbol, str):
        return False
    held_on = row.get("blocked_on")
    waits = (
        " ".join(str(b) for b in cast("list[object]", held_on)) if isinstance(held_on, list) else ""
    )
    ask = f"{row.get('title', '')} {waits}"
    return any(verifies(reader, w, symbol, run, ask) for w in cast("list[object]", warrants))

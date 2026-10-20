# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ledger line (skill section 6): structured columns, so the mechanism column exists.

⚑ summit's columns — `stamp kind symbol outcome mechanism "note" evidence=` — because
el-openglo's free-text `--ledger LINE` loses the mechanism column, and section 3's bias check
("six `sweep` entries in a row") reads that column and nothing else.

⚑ A COLUMN WITH WHITESPACE IN IT IS REFUSED, and so is a note with a newline: either would shift
every later column of the line for a reader splitting on whitespace.

⚑ THE LINE READS BACK (nemik, 2026-09-25): `parse` is the inverse of `line`, so a consumer never
re-splits the columns itself, and a legacy line comes back as `Unparsed`, never an exception.
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC
from pathlib import Path

from mikemol.pathsforward import lock, ownership
from mikemol.pathsforward.model import NO_SYMBOL, is_reference


class MalformedEntryError(ValueError):
    """A ledger entry that would not parse back into its columns."""


def is_symbol(sym: str) -> bool:
    """Say whether a symbol column is legal: `--`, a local `W<n>`, or another repo's `repo:W<n>`.

    ⚑ A CROSS-REPO SYMBOL IS A LEGAL COLUMN (nemik, 2026-09-25): ledgers already write
    `luthen-observability:W55`, and nemik resolves it into a cross-repo edge.

    Returns:
        True for any of the three forms.

    """
    return sym == NO_SYMBOL or is_reference(sym)


def is_stamp(stamp: str) -> bool:
    """Say whether a stamp is exactly what `lock.stamp` writes: a whole ISO-UTC second.

    ⚑ nemik (2026-09-25) measured `2026-09-24T` in a stamp column: one token, so the column split
    held and the line read as structured with an instant nobody can order. A stamp is accepted
    only if it parses as an aware time AND writes back byte-identical.

    Returns:
        True for `YYYY-MM-DDTHH:MM:SSZ` naming a real instant.

    """
    parsed = lock.parse_time(stamp)
    return parsed is not None and lock.stamp(parsed) == stamp


def utc_stamp(stamp: str) -> str | None:
    """Read any RFC 3339 instant with an offset as the `Z` form `line` writes.

    ⚑ THE READER IS WIDER THAN THE WRITER (el-openglo, 2026-10-17): 162 lines of its append-only
    ledger carry `+00:00` instead of `Z`, and rewriting history to please the reader is the wrong
    direction. `line` still refuses anything but the `Z` form (`is_stamp`); `parse` accepts a
    whole second at any numeric offset and reports it in UTC. A fraction of a second is refused,
    because dropping it would change the instant, and a naive or partial stamp is refused as before.

    Returns:
        the stamp as `YYYY-MM-DDTHH:MM:SSZ`, or None when it is not a whole-second aware instant.

    """
    parsed = lock.parse_time(stamp)
    if parsed is None or parsed.microsecond:
        return None
    return lock.stamp(parsed.astimezone(UTC))


@dataclass(frozen=True)
class Entry:
    """One ledger line's columns."""

    kind: str
    symbol: str
    outcome: str
    mechanism: str
    note: str
    evidence: str = ""
    session: str = ""
    actor: str = ""


def line_break(text: str) -> str | None:
    """Find the first character `str.splitlines()` treats as a line boundary.

    ⚑ DERIVED FROM PYTHON, NOT LISTED: the reader splits with `splitlines()`, so a character it
    splits on must never be written inside a note, and asking `splitlines()` itself cannot drift.

    Returns:
        the first boundary character in `text`, or None when `text` is one line.

    """
    for ch in text:
        if len(f"a{ch}b".splitlines()) > 1:
            return ch
    return None


def line(entry: Entry, stamp: str) -> str:
    """Format one entry.

    Returns:
        the line, without a trailing newline.

    Raises:
        MalformedEntryError: on an empty or whitespace-bearing column, a symbol that is none of
            `--`, `W<n>` or `repo:W<n>`, or a multi-line note.

    """
    if not is_stamp(stamp):
        msg = f"ledger stamp {stamp!r} is not YYYY-MM-DDTHH:MM:SSZ"
        raise MalformedEntryError(msg)
    columns = (entry.kind, entry.symbol, entry.outcome, entry.mechanism)
    if any(not c or any(ch.isspace() for ch in c) for c in columns):
        msg = f"ledger columns must be non-empty single tokens: {columns}"
        raise MalformedEntryError(msg)
    if not is_symbol(entry.symbol):
        msg = f"ledger symbol {entry.symbol!r} is neither {NO_SYMBOL}, W<n> nor repo:W<n>"
        raise MalformedEntryError(msg)
    if entry.session and not _UUID.fullmatch(entry.session):
        msg = f"ledger session {entry.session!r} is not a lower-case UUID"
        raise MalformedEntryError(msg)
    if entry.actor and not _ACTOR.fullmatch(entry.actor):
        msg = f"ledger actor {entry.actor!r} is not a lower-case word"
        raise MalformedEntryError(msg)
    for text in (entry.note, entry.evidence):
        broken = line_break(text)
        if broken is not None:
            msg = f"a ledger note is one line: U+{ord(broken):04X} is a line boundary"
            raise MalformedEntryError(msg)
    # ⚑ THE BACKSLASH IS ESCAPED FIRST: a note ending in one would otherwise make its closing
    # quote read as escaped (measured 2026-09-25), and no reader could recover the note.
    note = entry.note.replace("\\", "\\\\").replace('"', '\\"')
    out = f'{stamp}  {entry.kind:5} {entry.symbol:4} {entry.outcome:9} {entry.mechanism:9} "{note}"'
    if entry.session:
        out = f"{out}  session={entry.session}"
    if entry.actor:
        out = f"{out}  actor={entry.actor}"
    return f"{out}  evidence={entry.evidence}" if entry.evidence else out


SESSION_ENV = "CLAUDE_CODE_SESSION_ID"
OPERATOR = "operator"
"""The one actor a line names: an act carrying the operator's signature (`--lift JWS`, W1790)."""
_ACTOR = re.compile(r"[a-z][a-z0-9-]*")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def session_id(environ: Mapping[str, str]) -> str:
    """Read the session's transcript UUID from the environment the harness gives a tool call.

    ⚑ THE LOCK'S HOLDER IS A PROCESS, NOT THIS ID (nemik-84, 2026-10-18, measured): `session.own()`
    names the `claude` process by pid and start time, while luthen labels a session by its
    transcript file stem, which the harness exports as `CLAUDE_CODE_SESSION_ID` (it equalled the
    stem of this session's .jsonl). A value that is not a UUID is no answer.

    Returns:
        the UUID, or "" when the variable is unset or not a lower-case UUID (cron, a terminal).

    """
    value = environ.get(SESSION_ENV, "")
    return value if _UUID.fullmatch(value) else ""


def actor_of(opts: Mapping[str, object]) -> str:
    """Name who acted, for the lines one invocation writes (W1790, nemik:W770).

    ⚑ THE OPERATOR ONLY WHERE THE WRITER HOLDS PROOF: `--lift` is verified against the operator's
    public key before anything is saved, so a line written after it is the operator's act. Every
    other line leaves the actor empty, meaning the session named by `session=`. An act a session
    performs because the operator ruled something is still the session's; the ruling rides on the
    card as a warrant, and nemik joins the two.

    Returns:
        `operator` for a lift, else the empty string.

    """
    return OPERATOR if opts.get("lift") else ""


def own_line(entry: Entry, stamp: str) -> str:
    """Format one entry carrying the writing session's id when the entry names none (W1546).

    Returns:
        the line, as `line` writes it, with `session=<uuid>` when the environment names one.

    """
    return line(replace(entry, session=entry.session or session_id(os.environ)), stamp)


def append(path: Path, text: str) -> None:
    """Append one line; the ledger is never rewritten."""
    with ownership.open_append(path) as fh:
        fh.write(text + "\n")


# stamp, four single-token columns, a quoted note (escapes allowed), optional evidence.
_LINE = re.compile(
    r"^(?P<stamp>\S+)\s+(?P<kind>\S+)\s+(?P<symbol>\S+)\s+(?P<outcome>\S+)\s+(?P<mechanism>\S+)"
    r'\s+"(?P<note>(?:[^"\\]|\\.)*)"(?:\s+session=(?P<session>[0-9a-f-]{36}))?'
    r"(?:\s+actor=(?P<actor>[a-z][a-z0-9-]*))?"
    r"(?:\s+evidence=(?P<evidence>.*))?$"
)
_ESCAPE = re.compile(r"\\(.)")


@dataclass(frozen=True)
class Parsed:
    """A ledger line read back into its stamp and entry."""

    stamp: str
    entry: Entry


@dataclass(frozen=True)
class Unparsed:
    """A line this reader could not read as a structured entry — returned, never raised.

    ⚑ LEGACY LINES ARE DATA: the pre-structured ledger (a trailing `state_hash=…` in place of
    `evidence=`, a free-text line) is kept whole in `raw`, with `why` it did not parse.
    """

    raw: str
    why: str


def _group(match: re.Match[str], name: str) -> str:
    got = match.group(name)
    return got if isinstance(got, str) else ""


def parse(text: str) -> Parsed | Unparsed:
    """Read one ledger line back into its columns: the inverse of `line`.

    ⚑ nemik (2026-09-25): every consumer re-split the columns itself, which is the drift this
    package exists to end. A line `line` could have written parses to exactly what it wrote.

    Returns:
        the parsed line, or `Unparsed` naming why it is not a structured entry.

    """
    raw = text.rstrip("\n")
    match = _LINE.match(raw)
    if match is None:
        return Unparsed(raw, "not stamp, four columns, a quoted note and optional evidence=")
    stamp = utc_stamp(_group(match, "stamp"))
    if stamp is None:
        return Unparsed(raw, f"stamp {_group(match, 'stamp')!r} is not YYYY-MM-DDTHH:MM:SSZ")
    symbol = _group(match, "symbol")
    if not is_symbol(symbol):
        return Unparsed(raw, f"symbol {symbol!r} is neither {NO_SYMBOL}, W<n> nor repo:W<n>")
    entry = Entry(
        _group(match, "kind"),
        symbol,
        _group(match, "outcome"),
        _group(match, "mechanism"),
        _ESCAPE.sub(r"\1", _group(match, "note")),
        _group(match, "evidence"),
        _group(match, "session"),
        _group(match, "actor"),
    )
    return Parsed(stamp, entry)


def read(path: Path) -> list[Parsed | Unparsed]:
    """Read every line of a ledger, blank lines skipped.

    Returns:
        each line, parsed or not, in file order.

    """
    return [parse(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

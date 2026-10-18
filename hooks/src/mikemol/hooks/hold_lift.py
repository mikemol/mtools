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
_FRAGMENT = "#"
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
    if not ident.startswith(_FILE_PREFIX):
        return None
    path, _, uuid = ident[len(_FILE_PREFIX) :].partition(_FRAGMENT)
    return (path, uuid, line) if path and uuid else None


def verifies(reader: str, warrant: object, symbol: str, run: Run) -> bool:
    """Say whether a warrant's record is the operator's own words and names `symbol`.

    Returns:
        True when the record verifies as origin human and its line matches the card's symbol.

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
    return any(row.startswith("{") for row in hits.splitlines())


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
    return any(verifies(reader, w, symbol, run) for w in cast("list[object]", warrants))

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Attach a W3C PROV-O warrant to a card, after reading the cited record (mtools:W1384).

⚑⚑ A DECLARED JUDGEMENT NEEDS ITS PROVENANCE, THE JUSTIFICATION INCLUDED (operator, 2026-10-16:
"that's why we call them warrants"). A card that says "the operator ruled X" carries, beside the
prose, a JSON-LD object saying which transcript record it came from, when, and who spoke. The shape
is nemik's `WarrantRecordShape` (nemik 70d76c5): the card `prov:wasDerivedFrom` a record that is a
`prov:Entity` with `prov:generatedAtTime`, `prov:wasAttributedTo` a `prov:Agent` and
`prov:wasGeneratedBy` a `prov:Activity`. It is stored on the card as the list `warrants`.

⚑ THE RECORD IS READ AT WRITE TIME, THROUGH THE ONE READER OF TRANSCRIPTS. The reader is
`mikemol-transcriptstruct --verify` (mtools:W1385); this module runs it, never re-implements it, and
refuses what it refuses: a missing record, a wrong line, a missing timestamp, and a claimed operator
whose record is not human. The reader's command line is kept in the warrant (`mtools:reader`), so a
later reader can re-run the exact check.

⚑ ONE RECORD, ONE WARRANT PER CARD: attaching the same record twice changes nothing.
"""

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.pathsforward.model import Json, RefusedError, State, text

OPERATOR = "operator"
READER = "mikemol-transcriptstruct"
OPERATOR_AGENT = "urn:nemik:operator"
CONTEXT: Json = {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "mtools": "urn:mtools:warrant#",
}
Run = Callable[[Sequence[str]], tuple[int, str]]


def run_reader(argv: Sequence[str]) -> tuple[int, str]:
    """Run the transcript reader and capture what it printed.

    Returns:
        (exit code, stdout).

    """
    proc = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    code: int = proc.returncode
    out: str = proc.stdout
    return code, out


@dataclass(frozen=True, slots=True)
class Citation:
    """The record a warrant cites, as the operator typed it on the command line."""

    transcript: Path
    uuid: str
    claim: str | None = None
    line: int | None = None


def read(cited: Citation, reader: str = READER, run: Run = run_reader) -> tuple[Json, list[str]]:
    """Read the cited record through the reader and return its verdict.

    Returns:
        the reader's verdict object ({ok, reason, line, timestamp, kind}) for an accepted record,
        and the command line that produced it.

    Raises:
        RefusedError: when the reader is missing, prints nothing parseable, or refuses the record;
            the message carries the reader's own reason.

    """
    argv = [reader, str(cited.transcript), "--verify", cited.uuid]
    if cited.claim is not None:
        argv += ["--claim", cited.claim]
    if cited.line is not None:
        argv += ["--line", str(cited.line)]
    try:
        code, out = run(argv)
    except OSError as caught:
        msg = f"the transcript reader {reader} could not run: {caught}"
        raise RefusedError(msg) from caught
    first = out.strip().splitlines()[0] if out.strip() else ""
    try:
        verdict = cast("Json", json.loads(first))
    except ValueError as caught:
        msg = f"the transcript reader {reader} printed no verdict (exit {code})"
        raise RefusedError(msg) from caught
    if code != 0 or verdict.get("ok") is not True:
        msg = f"warrant refused: {text(verdict, 'reason') or f'reader exit {code}'}"
        raise RefusedError(msg)
    return verdict, argv


def build(card: str, cited: Citation, verdict: Json, reader: Sequence[str]) -> Json:
    """Spell one verified record as the card's PROV-O JSON-LD warrant.

    Returns:
        the JSON-LD object: the card derived from the record, which carries its time, speaker
        and utterance.

    """
    speaker = OPERATOR_AGENT if text(verdict, "kind") == "human" else None
    agent = speaker or f"urn:nemik:speaker/{text(verdict, 'kind')}"
    record: Json = {
        "@id": f"{cited.transcript.resolve().as_uri()}#{cited.uuid}",
        "@type": "prov:Entity",
        "prov:generatedAtTime": {"@value": text(verdict, "timestamp"), "@type": "xsd:dateTime"},
        "prov:wasAttributedTo": {"@id": agent, "@type": "prov:Agent"},
        "prov:wasGeneratedBy": {
            "@id": f"urn:nemik:utterance/{cited.uuid}",
            "@type": "prov:Activity",
        },
        "mtools:line": verdict.get("line"),
        "mtools:reader": " ".join(reader),
    }
    return {"@context": CONTEXT, "@id": card, "prov:wasDerivedFrom": record}


def attach(state: State, symbol: str, warrant: Json) -> bool:
    """Append the warrant to the card's `warrants` unless that record is already there.

    Returns:
        True when it was added, False when the card already carried a warrant for the record.

    Raises:
        RefusedError: when the symbol is not a card of this queue.

    """
    wanted = cast("Json", warrant["prov:wasDerivedFrom"])["@id"]
    for card in state.waypoints:
        if text(card, "symbol") != symbol:
            continue
        held = cast("list[Json]", card.setdefault("warrants", []))
        if any(cast("Json", w["prov:wasDerivedFrom"])["@id"] == wanted for w in held):
            return False
        held.append(warrant)
        return True
    msg = f"{symbol} is not a card of this queue"
    raise RefusedError(msg)

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 8: one PROV-O entity per human-origin utterance, with its needle (mtools:W1386).

⚑⚑ THE REASONING THE OPERATOR LAID OUT MUST NOT BE LOST IN THE TRANSCRIPTS (operator, 2026-10-16:
"this is why we mechanize"). A ruling lives as a line in one of hundreds of session files; a card
that cites it needs the line found again later, by something other than recall. This stage turns
each utterance the operator typed into one JSON-LD entity in the shape nemik's `WarrantRecordShape`
reads (nemik 70d76c5): a `prov:Entity` whose IRI is `file:///path/to/transcript.jsonl#<uuid>`, with
`prov:generatedAtTime`, `prov:wasAttributedTo` the operator and `prov:wasGeneratedBy` the
utterance. The text itself rides beside it as `mtools:needle`, whole, so a query can search it.

⚑ ONLY WHAT `provenance.classify` CALLS HUMAN. A peer's message, a harness injection and tool
output wearing the user role are not rulings, so none is harvested; a record with no uuid or no
timestamp cannot be cited, so it is skipped, and the skip is counted, never silent.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from mikemol.transcriptstruct.provenance import classify
from mikemol.transcriptstruct.records import AssistantRecord, AttachmentRecord, Record, UserRecord

OPERATOR_AGENT = "urn:nemik:operator"
CONTEXT: dict[str, object] = {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "mtools": "urn:mtools:warrant#",
}


@dataclass(slots=True)
class Harvest:
    """The entities found in one transcript, and the human utterances that could not be cited."""

    entities: list[dict[str, object]] = field(default_factory=list)
    uncitable: int = 0


def _entity(
    record: UserRecord | AttachmentRecord, transcript: Path, text: str
) -> dict[str, object] | None:
    uuid = record.raw.get("uuid")
    stamp = record.raw.get("timestamp")
    if not isinstance(uuid, str) or not uuid or not isinstance(stamp, str) or not stamp:
        return None
    session = record.raw.get("sessionId")
    return {
        "@context": CONTEXT,
        "@id": f"{transcript.resolve().as_uri()}#{uuid}",
        "@type": "prov:Entity",
        "prov:generatedAtTime": {"@value": stamp, "@type": "xsd:dateTime"},
        "prov:wasAttributedTo": {"@id": OPERATOR_AGENT, "@type": "prov:Agent"},
        "prov:wasGeneratedBy": {"@id": f"urn:nemik:utterance/{uuid}", "@type": "prov:Activity"},
        "mtools:line": record.line,
        "mtools:session": session if isinstance(session, str) else None,
        "mtools:needle": text,
    }


def harvest(records: Iterable[Record], transcript: Path, scheduled: Sequence[str] = ()) -> Harvest:
    """Collect the operator's utterances of one transcript as PROV-O entities.

    Returns:
        the entities in line order, and how many human utterances had no uuid or timestamp.

    """
    found = Harvest()
    for record in records:
        if isinstance(record, AssistantRecord) or not isinstance(
            record, (UserRecord, AttachmentRecord)
        ):
            continue
        spoken = classify(record, scheduled)
        if spoken.kind != "human" or not spoken.text.strip():
            continue
        entity = _entity(record, transcript, spoken.text.strip())
        if entity is None:
            found.uncitable += 1
        else:
            found.entities.append(entity)
    return found

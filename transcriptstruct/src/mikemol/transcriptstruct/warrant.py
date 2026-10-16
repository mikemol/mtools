# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 7: read the record a warrant cites, and judge whether the claimed speaker said it.

⚑⚑ A WARRANT IS ONLY AS GOOD AS THE RECORD IT POINTS AT (mtools:W1385, the operator's 2026-10-16
ruling that a declared judgement needs its provenance). The writer that attaches one reads the
cited record through this module at write time and refuses what it cannot find:

- the uuid names no record of the transcript;
- a line was cited and the record with that uuid is on another line;
- the record carries no timestamp (the shape needs `prov:generatedAtTime`);
- the speaker is claimed to be the operator and the record's provenance kind is not `human`
  (a peer session's message, a harness injection or tool output wearing the user role).

⚑ THE CLASSIFICATION IS `provenance.classify`, NOT A ROLE TEST: an `is-it-the-user` check would
accept a cross-session message as the operator, which is exactly the forgery a warrant exists to
refuse. A refusal names its reason so the caller can print it whole.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from mikemol.transcriptstruct.provenance import classify
from mikemol.transcriptstruct.records import (
    AssistantRecord,
    AttachmentRecord,
    Record,
    UserRecord,
)

OPERATOR = "operator"
_HUMAN = "human"


@dataclass(frozen=True, slots=True)
class Verdict:
    """What reading the cited record found: whether it holds, and why not when it does not."""

    ok: bool
    reason: str
    line: int | None
    timestamp: str | None
    kind: str | None


def _refused(reason: str, line: int | None = None, kind: str | None = None) -> Verdict:
    return Verdict(ok=False, reason=reason, line=line, timestamp=None, kind=kind)


def _has_uuid(record: Record, uuid: str) -> bool:
    # Only the three decoded envelope kinds carry a uuid worth citing.
    if not isinstance(record, (UserRecord, AssistantRecord, AttachmentRecord)):
        return False
    return record.raw.get("uuid") == uuid


def verify(
    records: Iterable[Record],
    uuid: str,
    claim: str | None = None,
    line: int | None = None,
    scheduled: Sequence[str] = (),
) -> Verdict:
    """Read the record a warrant cites and judge the citation.

    Returns:
        an ok verdict carrying the record's line, timestamp and speaker kind, or a refusal whose
        reason says which check failed.

    """
    found = next((r for r in records if _has_uuid(r, uuid)), None)
    if found is None or not isinstance(found, (UserRecord, AssistantRecord, AttachmentRecord)):
        return _refused(f"no record with uuid {uuid} in the transcript")
    kind = classify(found, scheduled).kind
    if line is not None and found.line != line:
        return _refused(f"uuid {uuid} is on line {found.line}, not line {line}", found.line, kind)
    stamp = found.raw.get("timestamp")
    if not isinstance(stamp, str) or not stamp:
        return _refused(f"the record on line {found.line} carries no timestamp", found.line, kind)
    if claim == OPERATOR and kind != _HUMAN:
        return _refused(
            f"claimed operator, but the record on line {found.line} is {kind}, not human",
            found.line,
            kind,
        )
    return Verdict(ok=True, reason="", line=found.line, timestamp=stamp, kind=kind)

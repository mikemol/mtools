# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count the turns of a session that failed authentication, from record metadata only (W2040).

An expired login makes every turn of a session fail, and a failing session runs no hook, so the
detector reads the transcript from outside. The harness records a failed turn as a synthetic
assistant record: model `<synthetic>`, top-level `error` of `authentication_failed`,
`isApiErrorMessage` true, and zero token usage.

⚑ METADATA ONLY (luthen-observability:W1681): a transcript holds the operator's words. This module
reads `type`, `model`, `error`, `isApiErrorMessage`, `sessionId` and `timestamp` of a record and
never its content, so nothing it returns can carry a sentence of the conversation.
⚑ A SERIES LABEL IS A SESSION ID AND A PROJECT NAME, NEVER A PATH: a path is an address-like literal
in a series. The project is the name of the directory that holds the transcript file.
⚑ THE TAIL RUN IS THE PAGE-WORTHY FIGURE: two or more failed turns at the end of the session with no
successful assistant record after them. A session that failed once and recovered has a run of 0.

CONSUMED BY: luthen-observability, which publishes `mikemol.session.auth_failed{session}`.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import cast

from mikemol.transcriptstruct.records import AssistantRecord, Record

ERROR = "authentication_failed"
SYNTHETIC = "<synthetic>"


@dataclass(frozen=True, slots=True)
class AuthFailed:
    """What a session's transcript says about authentication failures."""

    session: str
    project: str
    failed: int
    tail_run: int
    newest: str | None


def _meta(record: AssistantRecord) -> tuple[bool, str | None, str | None]:
    """Read the metadata of one assistant record.

    Returns:
        whether the record is a failed-authentication turn, its session id and its timestamp.

    """
    raw = record.raw
    message = raw.get("message")
    model = cast("dict[str, object]", message).get("model") if isinstance(message, dict) else None
    session, stamp = raw.get("sessionId"), raw.get("timestamp")
    failed = (
        raw.get("error") == ERROR and raw.get("isApiErrorMessage") is True and model == SYNTHETIC
    )
    return (
        failed,
        session if isinstance(session, str) else None,
        stamp if isinstance(stamp, str) else None,
    )


def summarize(records: Iterable[Record], project: str) -> AuthFailed:
    """Count the failed-authentication turns of one transcript.

    Returns:
        the session id (empty when no assistant record names one), the project, the failed count,
        the run of failed turns at the end, and the newest failed timestamp (None for none).

    """
    session = ""
    failed = tail = 0
    newest: str | None = None
    for record in records:
        if not isinstance(record, AssistantRecord):
            continue
        bad, sid, stamp = _meta(record)
        session = session or sid or ""
        if bad:
            failed += 1
            tail += 1
            newest = stamp or newest
        else:
            tail = 0
    return AuthFailed(session, project, failed, tail, newest)

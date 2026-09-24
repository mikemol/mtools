# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 4: every record gets one speaker kind, and the operator is not over-counted.

Every fixture is SYNTHETIC and built inline. Real transcript excerpts are held by substrate's
operator and do not enter this tree.
"""

from __future__ import annotations

import json

from mikemol.transcriptstruct.provenance import Provenance, classify
from mikemol.transcriptstruct.records import parse_line

_TICK = "[synthetic tick]"


def _user(content: object, **flags: object) -> str:
    """Build a synthetic user line, with any extra envelope flags.

    Returns:
        the JSONL line.

    """
    message: dict[str, object] = {"role": "user", "content": content}
    envelope: dict[str, object] = {"type": "user", "message": message, **flags}
    return json.dumps(envelope)


def _queued(origin: str | None, prompt: str) -> str:
    """Build a synthetic queued-command attachment line.

    Returns:
        the JSONL line.

    """
    body: dict[str, object] = {"type": "queued_command", "prompt": prompt}
    if origin is not None:
        body["origin"] = {"kind": origin}
    envelope: dict[str, object] = {"type": "attachment", "message": None, "attachment": body}
    return json.dumps(envelope)


def test_plain_user_prose_is_human() -> None:
    """Text the operator typed, with nothing wrapped around it, is `human`."""
    assert classify(parse_line(_user("drain the tier"), 1)) == Provenance("human", "drain the tier")


def test_a_system_reminder_is_stripped_and_what_remains_is_human() -> None:
    """A reminder injected around the operator's words is removed; the words stay `human`."""
    text = "<system-reminder>be careful</system-reminder>go ahead"
    assert classify(parse_line(_user(text), 1)) == Provenance("human", "go ahead")


def test_text_that_is_only_harness_plumbing_is_harness() -> None:
    """A task notification alone leaves nothing typed: `harness`, with no text to search."""
    text = "<task-notification><task-id>x</task-id><status>done</status></task-notification>"
    assert classify(parse_line(_user(text), 1)) == Provenance("harness", "")


def test_tool_output_wearing_the_user_role_is_tool_result() -> None:
    """User-role content made only of tool_result blocks is `tool_result`, never the operator."""
    content = [{"type": "tool_result", "content": "ls output"}]
    assert classify(parse_line(_user(content), 1)).kind == "tool_result"


def test_a_compaction_summary_is_its_own_kind() -> None:
    """An isCompactSummary envelope is `compact_summary`: a gloss, not the operator speaking."""
    line = _user("summary of earlier turns", isCompactSummary=True)
    assert classify(parse_line(line, 1)).kind == "compact_summary"


def test_a_queued_attachment_takes_its_nested_origin() -> None:
    """A queued command's nested `origin.kind` makes it `human` or `peer`.

    ⚑ Measured on a real transcript, 287 queued commands carried an origin and the old reader
    judged 0 of them human, so an operator's mid-turn directive did not exist to a search.
    """
    assert classify(parse_line(_queued("human", "stop"), 1)) == Provenance("human", "stop")
    assert classify(parse_line(_queued("peer", "hello"), 1)) == Provenance("peer", "hello")


def test_an_attachment_without_an_origin_is_harness() -> None:
    """A queued attachment with no origin was put there by the harness itself."""
    assert classify(parse_line(_queued(None, "resume"), 1)).kind == "harness"


def test_an_unlisted_origin_kind_is_unknown_not_human() -> None:
    """An origin kind this module does not know is `unknown`: guessing `human` would over-count."""
    assert classify(parse_line(_queued("robot", "x"), 1)).kind == "unknown"


def test_a_cross_session_message_in_user_text_is_peer() -> None:
    """A `<cross-session-message>` wrapper as user text is another session speaking: `peer`."""
    text = '<cross-session-message from="s">hi</cross-session-message>'
    assert classify(parse_line(_user(text), 1)).kind == "peer"


def test_a_declared_scheduled_prefix_is_scheduled_and_undeclared_stays_human() -> None:
    """A tick prompt is `scheduled` only when the caller names its prefix (study shape 5).

    ⚑ Nothing in the envelope marks a cron prompt, so the arm pins both sides: declared, it is
    `scheduled`; undeclared, it is `human`, which is the old behaviour and is not guessed away.
    """
    record = parse_line(_user(f"{_TICK} run one tick"), 1)
    assert classify(record, scheduled=[_TICK]).kind == "scheduled"
    assert classify(record).kind == "human"


def test_unknown_and_malformed_lines_are_unknown() -> None:
    """A record stage 1 could not decode has no speaker: `unknown`, never dropped."""
    assert classify(parse_line('{"type": "summary"}', 1)).kind == "unknown"
    assert classify(parse_line("{not json", 1)).kind == "unknown"

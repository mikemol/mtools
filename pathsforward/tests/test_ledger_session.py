# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ledger line carries the writing session's transcript UUID when the environment names one."""

import pytest

from mikemol.pathsforward import ledger
from mikemol.pathsforward.ledger import Entry, MalformedEntryError, Parsed

_STAMP = "2026-10-18T12:00:00Z"
_UUID = "0709aae6-1dba-4fe5-bfbe-24d21edd31e0"
_OTHER = "ca6f3699-66ac-4ffa-a3ca-6ececbab791f"


def _entry(session: str = "", evidence: str = "") -> Entry:
    return Entry("tick", "W7", "advanced", "unblock", "did it", evidence, session)


def test_a_line_with_a_session_reads_back_to_the_same_entry_before_the_evidence() -> None:
    """session= sits between the note and evidence=, so the free-text evidence stays last."""
    entry = _entry(_UUID, "commit abc")
    text = ledger.line(entry, _STAMP)
    assert text.endswith(f'"did it"  session={_UUID}  evidence=commit abc')
    assert ledger.parse(text) == Parsed(_STAMP, entry)


def test_a_line_without_a_session_is_unchanged_and_an_old_line_parses_with_none() -> None:
    """Nothing is added for an empty session, so every line already in a ledger still reads."""
    text = ledger.line(_entry(), _STAMP)
    assert "session=" not in text
    parsed = ledger.parse(text)
    assert isinstance(parsed, Parsed)
    assert not parsed.entry.session


def test_a_session_that_is_not_a_uuid_is_refused_on_write() -> None:
    """The column is a join key for luthen's label, so a loose string would join nothing."""
    with pytest.raises(MalformedEntryError):
        ledger.line(_entry("not-a-uuid"), _STAMP)


def test_own_line_fills_the_session_from_the_environment_and_keeps_an_explicit_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The harness's CLAUDE_CODE_SESSION_ID is the id; an entry that names its own keeps it."""
    monkeypatch.setenv(ledger.SESSION_ENV, _UUID)
    assert f"session={_UUID}" in ledger.own_line(_entry(), _STAMP)
    assert f"session={_OTHER}" in ledger.own_line(_entry(_OTHER), _STAMP)


def test_own_line_leaves_the_session_empty_when_unset_or_not_a_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cron job or a terminal has no session: the field is absent, never a guess."""
    monkeypatch.delenv(ledger.SESSION_ENV, raising=False)
    assert "session=" not in ledger.own_line(_entry(), _STAMP)
    monkeypatch.setenv(ledger.SESSION_ENV, "claude-nemik")
    assert "session=" not in ledger.own_line(_entry(), _STAMP)

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `after_compaction`: the notes and the live facts come back after a compact."""

from __future__ import annotations

import io
import json
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import after_compaction, entry, hook_argv
from mikemol.hooks.host_facts import GIB, Headroom, HostLock
from mikemol.hooks.tick_gate import facts_line

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

HEALTHY = Headroom(used=GIB, limit=100 * GIB, ratio=1.5)
FREE = HostLock(holder=None, taken_at=None)
NOTES_TEXT = "Durable state: read .claude/host-visitor.md\nThe loop is off.\n"
EMPTY_QUEUE: dict[str, list[str]] = {"waypoints": []}


def _healthy() -> Headroom | None:
    """Stand in for the zram reader on a healthy device.

    Returns:
        a device 1 GiB into a 100 GiB ceiling.

    """
    return HEALTHY


def _project(root: Path, notes: str | None) -> None:
    """Make `root` a project with a free queue and, if given, an after-compaction notes file."""
    (root / ".claude").mkdir(exist_ok=True)
    queue = root / ".claude" / "paths-forward.json"
    queue.write_text(json.dumps(EMPTY_QUEUE), encoding="utf-8")
    if notes is not None:
        (root / ".claude" / "after-compaction.md").write_text(notes, encoding="utf-8")


def _expected(root: Path, notes: str | None) -> str:
    """Return the exact line `run` prints for a healthy, free host.

    Returns:
        the SessionStart JSON line, newline included.

    """
    body = after_compaction.context(root, notes, facts_line(HEALTHY, FREE))
    added: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": body}
    }
    return json.dumps(added) + "\n"


def test_the_notes_file_is_read_whole_when_it_fits(tmp_path: Path) -> None:
    """A short notes file comes back exactly, with no cut marker."""
    _project(tmp_path, NOTES_TEXT)
    assert after_compaction.read_notes(tmp_path) == NOTES_TEXT


def test_a_notes_file_over_the_cap_is_cut_and_says_so(tmp_path: Path) -> None:
    """Pointers are short: one that is not is cut at the cap with a marker, never silently."""
    cap = after_compaction.MAX_NOTES_CHARS
    _project(tmp_path, "x" * (cap + 50))
    notes = after_compaction.read_notes(tmp_path)
    assert notes is not None
    assert notes.startswith("x" * cap)
    assert notes.endswith("(notes cut here)")
    _project(tmp_path, "y" * cap)
    assert after_compaction.read_notes(tmp_path) == "y" * cap


def test_a_missing_or_unreadable_notes_file_is_none(tmp_path: Path) -> None:
    """Absent is None, so the context can say there are no notes rather than inventing some."""
    assert after_compaction.read_notes(tmp_path) is None
    (tmp_path / ".claude" / "after-compaction.md").mkdir(parents=True)
    assert after_compaction.read_notes(tmp_path) is None


def test_the_context_names_where_missing_notes_would_be(tmp_path: Path) -> None:
    """Without notes, the context says so and names the path, so a project can write one."""
    text = after_compaction.context(tmp_path, None, "FACTS")
    assert str(tmp_path / ".claude" / "after-compaction.md") in text
    assert "no notes file" in text
    assert text.endswith("\nFACTS")


def test_the_context_puts_the_notes_before_the_live_facts(tmp_path: Path) -> None:
    """The notes come first, then the facts, joined by one newline, trailing space trimmed."""
    text = after_compaction.context(tmp_path, "pointer one\n\n", "FACTS")
    assert text == (
        "after compaction, this project's notes (.claude/after-compaction.md):\npointer one\nFACTS"
    )


def test_a_compact_session_start_gets_the_notes_and_the_live_facts(tmp_path: Path) -> None:
    """After a compaction, the notes file and the host facts are added as SessionStart context."""
    _project(tmp_path, NOTES_TEXT)
    out = io.StringIO()
    payload: dict[str, object] = {"source": "compact", "cwd": str(tmp_path)}
    assert after_compaction.run(payload, _healthy, out) == 0
    assert out.getvalue() == _expected(tmp_path, NOTES_TEXT)


def test_a_session_start_from_another_source_is_left_untouched(tmp_path: Path) -> None:
    """A fresh startup, a resume or a clear is not a compaction: nothing is added."""
    _project(tmp_path, NOTES_TEXT)
    for source in ("startup", "resume", "clear"):
        out = io.StringIO()
        payload: dict[str, object] = {"source": source, "cwd": str(tmp_path)}
        assert after_compaction.run(payload, _healthy, out) == 0
        assert not out.getvalue()


def test_a_payload_without_a_source_is_treated_as_the_matcher_having_chosen_it(
    tmp_path: Path,
) -> None:
    """The settings matcher selects compact; a payload that omits `source` is not second-guessed."""
    _project(tmp_path, None)
    out = io.StringIO()
    assert after_compaction.run({"cwd": str(tmp_path)}, _healthy, out) == 0
    assert out.getvalue() == _expected(tmp_path, None)


def test_main_reads_the_payload_on_stdin_and_adds_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through main, with the real zram reader, a compact start prints SessionStart context."""
    _project(tmp_path, NOTES_TEXT)
    stdin_payload: dict[str, str] = {"source": "compact", "cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(stdin_payload)))
    assert after_compaction.main() == 0
    out = capsys.readouterr().out
    assert out.startswith('{"hookSpecificOutput": {"hookEventName": "SessionStart"')
    assert "The loop is off." in out


def test_main_adds_nothing_for_a_payload_that_is_not_json_and_says_so(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A session start must not be blocked by an unreadable payload."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert after_compaction.main() == 0
    captured = capsys.readouterr()
    assert not captured.out
    assert "not JSON" in captured.err


def test_the_console_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The argv contract: a hook takes no arguments, and the refusal names the program."""
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-after-compaction", "--help"])
    assert entry.after_compaction_main() == hook_argv.EXIT_REFUSED
    assert "mikemol-hook-after-compaction" in capsys.readouterr().err

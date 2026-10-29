# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `after_compaction`: the notes and the live facts come back after a compact."""

from __future__ import annotations

import io
import json
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

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
NOW = datetime(2026, 10, 29, 5, 0, tzinfo=UTC)
SHORT = 3
LONGER = 5


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


def _transcript(directory: Path, lines: int) -> Path:
    """Write a transcript of `lines` lines in a project directory.

    Returns:
        the transcript's path.

    """
    path = directory / "sess.jsonl"
    path.write_text('{"type": "user"}\n' * lines, encoding="utf-8")
    return path


def _record(path: Path) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))


def test_a_precompact_payload_freezes_the_bound_the_path_and_the_trigger(tmp_path: Path) -> None:
    """W2117: the record holds the transcript line bound, its path and the trigger, numbered 1."""
    transcript = _transcript(tmp_path, SHORT)
    payload: dict[str, object] = {
        "transcript_path": str(transcript),
        "session_id": "s1",
        "trigger": "auto",
    }
    frozen = after_compaction.freeze(payload, NOW)
    assert frozen == tmp_path / "compaction" / "s1" / "1.json"
    assert frozen is not None
    assert _record(frozen) == {
        "n": 1,
        "session": "s1",
        "trigger": "auto",
        "transcript": str(transcript),
        "line_bound": SHORT,
        "prior": "",
        "at": NOW.isoformat(),
    }


def test_a_second_compaction_is_numbered_next_and_names_the_prior_record(tmp_path: Path) -> None:
    """The chain: record 2 names record 1's path, and its bound is the longer transcript's."""
    transcript = _transcript(tmp_path, SHORT)
    payload: dict[str, object] = {"transcript_path": str(transcript), "session_id": "s1"}
    first = after_compaction.freeze(payload, NOW)
    _transcript(tmp_path, LONGER)
    second = after_compaction.freeze(payload, NOW)
    assert first is not None
    assert second is not None
    assert second.name == "2.json"
    assert _record(second)["prior"] == str(first)
    assert _record(second)["line_bound"] == LONGER
    assert after_compaction.latest_freeze(second.parent) == second


def test_a_payload_without_a_readable_transcript_freezes_nothing(tmp_path: Path) -> None:
    """A compaction is never blocked: no path, or a path that is not there, writes no record."""
    assert after_compaction.freeze({}, NOW) is None
    gone: dict[str, object] = {"transcript_path": str(tmp_path / "gone.jsonl")}
    assert after_compaction.freeze(gone, NOW) is None
    assert not (tmp_path / "compaction").exists()


def test_a_compact_session_start_names_the_frozen_record_for_the_validator(tmp_path: Path) -> None:
    """W2117: after a freeze, the SessionStart(compact) output ends with the validator line."""
    _project(tmp_path, NOTES_TEXT)
    transcript = _transcript(tmp_path, SHORT)
    frozen_payload: dict[str, object] = {"transcript_path": str(transcript), "session_id": "s1"}
    frozen = after_compaction.freeze(frozen_payload, NOW)
    assert frozen is not None
    out = io.StringIO()
    start: dict[str, object] = {
        "source": "compact",
        "cwd": str(tmp_path),
        "transcript_path": str(transcript),
        "session_id": "s1",
    }
    assert after_compaction.run(start, _healthy, out) == 0
    body = after_compaction.context(tmp_path, NOTES_TEXT, facts_line(HEALTHY, FREE), frozen)
    assert body.endswith(f"\nrun the compaction-summary validator over {frozen}")
    added: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": body}
    }
    assert out.getvalue() == json.dumps(added) + "\n"


def test_a_session_with_no_frozen_record_gets_no_validator_line(tmp_path: Path) -> None:
    """The control: the same start payload without a PreCompact record adds no such line."""
    _project(tmp_path, NOTES_TEXT)
    transcript = _transcript(tmp_path, SHORT)
    out = io.StringIO()
    start: dict[str, object] = {
        "source": "compact",
        "cwd": str(tmp_path),
        "transcript_path": str(transcript),
        "session_id": "s1",
    }
    assert after_compaction.run(start, _healthy, out) == 0
    assert out.getvalue() == _expected(tmp_path, NOTES_TEXT)


def test_precompact_reads_stdin_freezes_and_never_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through the console function: a payload freezes a record; a non-JSON payload says so."""
    transcript = _transcript(tmp_path, SHORT)
    stdin_payload: dict[str, str] = {"transcript_path": str(transcript), "session_id": "s1"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(stdin_payload)))
    assert after_compaction.precompact() == 0
    assert (tmp_path / "compaction" / "s1" / "1.json").is_file()
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert after_compaction.precompact() == 0
    assert "not JSON" in capsys.readouterr().err


def test_nothing_frozen_always_says_why_on_stderr_and_still_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2125: no transcript_path, an unreadable transcript and a frozen record each read apart."""
    gone = str(tmp_path / "gone.jsonl")
    nameless: dict[str, str] = {}
    missing: dict[str, str] = {"transcript_path": gone}
    for payload, said in (
        (nameless, "the payload names no transcript_path"),
        (missing, f"the transcript {gone} cannot be read"),
    ):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
        assert after_compaction.precompact() == 0
        assert f"precompact: nothing frozen: {said}" in capsys.readouterr().err
    readable: dict[str, str] = {"transcript_path": str(_transcript(tmp_path, SHORT))}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(readable)))
    assert after_compaction.precompact() == 0
    assert "nothing frozen" not in capsys.readouterr().err


def test_the_precompact_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The argv contract holds for the new hook too, and the refusal names it."""
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-precompact", "--help"])
    assert entry.precompact_main() == hook_argv.EXIT_REFUSED
    assert "mikemol-hook-precompact" in capsys.readouterr().err

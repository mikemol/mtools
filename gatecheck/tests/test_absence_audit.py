# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `absence_audit`: an absence claim without the owning tool's run is flagged."""

from __future__ import annotations

import io
import json
import sys
from typing import TYPE_CHECKING

import pytest

from mikemol.gatecheck import absence_audit

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_FOUND = 2
_CLIP = 140
_SHOWN = 8
_CLAIM = "No warrant covers the sweep table in paperkit."
_QUALIFIED = "No warrant covers the sweep table in paperkit: UNAVAILABLE, not refuted."
_Row = dict[str, object]


@pytest.fixture()
def log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the report log at tmp_path, so no test writes to the real home.

    Returns:
        the log path.

    """
    path = tmp_path / "logs" / "absence.log"
    monkeypatch.setenv(absence_audit.LOG_ENV, str(path))
    return path


def _user() -> _Row:
    return {"type": "user", "message": {"role": "user", "content": "go"}}


def _says(text: str) -> _Row:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _runs(command: str) -> _Row:
    item = {"type": "tool_use", "name": "Bash", "input": {"command": command}}
    return {"type": "assistant", "message": {"content": [item]}}


def _transcript(tmp_path: Path, *rows: Mapping[str, object]) -> str:
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return str(path)


def _hook_json(transcript: str) -> str:
    payload: dict[str, str] = {"transcript_path": transcript}
    return json.dumps(payload)


def test_the_log_path_follows_the_environment_and_defaults_under_home(
    tmp_path: Path, log: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`$ABSENCE_AUDIT_LOG` wins; without it the log is `~/.claude/absence-audit.log`."""
    assert absence_audit.log_path() == log
    monkeypatch.delenv(absence_audit.LOG_ENV)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert absence_audit.log_path() == tmp_path / ".claude" / "absence-audit.log"


def test_rows_parses_non_blank_lines_and_reads_a_non_object_as_empty(tmp_path: Path) -> None:
    """Blank lines are skipped; a JSON array or scalar row reads as an empty mapping."""
    path = tmp_path / "r.jsonl"
    path.write_text('{"a": 1}\n\n   \n[1, 2]\n3\n', encoding="utf-8")
    assert absence_audit.rows(str(path)) == [{"a": 1}, {}, {}]


def test_a_user_row_is_recognised_by_type_or_by_message_role() -> None:
    """Either spelling marks a turn boundary; an assistant row or a malformed message does not."""
    assert absence_audit.is_user({"type": "user"})
    assert absence_audit.is_user({"message": {"role": "user"}})
    assert not absence_audit.is_user({"type": "assistant", "message": {"role": "assistant"}})
    assert not absence_audit.is_user({"message": "not a mapping"})
    assert not absence_audit.is_user({})


def test_last_turn_starts_at_the_last_user_row_or_keeps_everything() -> None:
    """The turn is the slice from the final user row; with none, every row."""
    first, reply, second, answer = _user(), _says("a"), _user(), _says("b")
    assert absence_audit.last_turn([first, reply, second, answer]) == [second, answer]
    assert absence_audit.last_turn([reply, answer]) == [reply, answer]


def test_scan_turn_joins_assistant_text_and_ignores_thinking() -> None:
    """Text items are the claims; a thinking item and a non-list content are not read."""
    thinking = {"type": "assistant", "message": {"content": [{"type": "thinking", "text": "x"}]}}
    plain = {"type": "assistant", "message": {"content": "just a string"}}
    odd = {"type": "assistant", "message": {"content": ["bare", {"type": "text", "text": 7}]}}
    text, searched = absence_audit.scan_turn([_says("one"), thinking, plain, odd, _says("two")])
    assert text == "one\n\ntwo"
    assert not searched


def test_scan_turn_reads_content_at_the_row_when_there_is_no_message() -> None:
    """A row carrying `content` directly is read the same way."""
    row: _Row = {"content": [{"type": "text", "text": "direct"}]}
    assert absence_audit.scan_turn([row]) == ("direct", False)


def test_a_tool_call_to_the_owning_tool_counts_as_clearing_evidence() -> None:
    """`bazel test` in a tool call's input is a search; a bare recursive grep is not."""
    assert absence_audit.scan_turn([_runs("bazel test //:hook")])[1]
    assert absence_audit.scan_turn([_runs("sed -i 's/a/b/' x.py")])[1]
    assert not absence_audit.scan_turn([_runs("grep -rn rests-on paperkit/")])[1]
    assert not absence_audit.scan_turn([_runs("")])[1]


def test_flags_in_reports_each_watchword_on_a_line_about_the_engine() -> None:
    """A watchword on a context line is a flag, as `(watchword, line)`, in order."""
    got = absence_audit.flags_in("fine\nNo warrant covers it, and it is ungated here\n")
    assert got == [
        ("No warrant covers", "No warrant covers it, and it is ungated here"),
        ("ungated", "No warrant covers it, and it is ungated here"),
    ]


def test_a_line_that_says_unavailable_is_the_correct_form_and_is_not_flagged() -> None:
    """The remedy must not be flagged as the violation."""
    assert absence_audit.flags_in(_QUALIFIED) == []


def test_a_watchword_with_no_engine_context_is_not_flagged() -> None:
    """The context regex is what keeps ordinary prose out."""
    assert absence_audit.flags_in("There is no meeting scheduled for Thursday.") == []


def test_a_flagged_line_is_clipped_for_the_report() -> None:
    """Only the first 140 characters of the stripped line are kept."""
    ((_word, line),) = absence_audit.flags_in("   " + _CLAIM + " " + "x" * 300)
    assert len(line) == _CLIP
    assert line.startswith("No warrant covers")


def test_report_appends_to_the_log_names_the_claims_and_returns_found(
    log: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The message goes to stderr and to the log (parent created, appended on a second call)."""
    flags = [("ungated", "it is ungated"), ("dangling", "a dangling gate")]
    assert absence_audit.report(flags) == _FOUND
    assert absence_audit.report(flags[:1]) == _FOUND
    err = capsys.readouterr().err
    assert "  • 'ungated': it is ungated\n  • 'dangling': a dangling gate\n" in err
    assert "cannot say DOES NOT EXIST" in err
    logged = log.read_text(encoding="utf-8")
    assert logged.count("---\n") == _FOUND
    assert "'dangling'" in logged


@pytest.mark.usefixtures("log")
def test_report_quotes_at_most_eight_flags(capsys: pytest.CaptureFixture[str]) -> None:
    """A long list is cut after eight bullets."""
    absence_audit.report([("w", f"line{i}") for i in range(_SHOWN + 4)])
    err = capsys.readouterr().err
    assert err.count("  • ") == _SHOWN
    assert "line7" in err
    assert "line8" not in err


def test_selftest_passes_every_arm(capsys: pytest.CaptureFixture[str]) -> None:
    """Both T and F arms hold: exit 0 and the PASS line."""
    assert absence_audit.main(["--selftest"]) == 0
    out = capsys.readouterr().out
    assert "absence-audit --selftest: PASS (8 of 8 arms)" in out
    assert "FAIL" not in out


def _no_flags(_text: str) -> list[tuple[str, str]]:
    return []


def test_selftest_fails_when_the_audit_cannot_see_what_it_looks_for(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An audit that flags nothing must read as FAIL, not as a clean tree."""
    monkeypatch.setattr(absence_audit, "flags_in", _no_flags)
    assert absence_audit.selftest() == 1
    out = capsys.readouterr().out
    assert "absence-audit --selftest: FAIL (5 of 8 arms)" in out
    assert "  FAIL T: an unqualified" in out
    assert "  ok   F: an absence claim with no engine context" in out


def test_files_mode_flags_a_file_and_skips_an_unreadable_one(
    tmp_path: Path, log: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each flagged line is prefixed by its file; a missing file is skipped; exit is 2."""
    dirty = tmp_path / "notes.txt"
    dirty.write_text(_CLAIM + "\n", encoding="utf-8")
    code = absence_audit.main(["--files", str(tmp_path / "missing.txt"), str(dirty)])
    assert code == _FOUND
    assert f"'No warrant covers': {dirty}: {_CLAIM}" in capsys.readouterr().err
    assert log.exists()


def test_files_mode_is_clean_when_no_file_holds_a_claim(tmp_path: Path, log: Path) -> None:
    """Nothing flagged: exit 0 and nothing is logged."""
    clean = tmp_path / "ok.txt"
    clean.write_text(_QUALIFIED + "\n", encoding="utf-8")
    assert absence_audit.main(["--files", str(clean)]) == 0
    assert not log.exists()


def test_transcript_mode_fails_a_claim_made_without_running_the_owning_tool(
    tmp_path: Path, log: Path
) -> None:
    """A claim in the last turn and no clearing tool call: exit 2, logged."""
    path = _transcript(tmp_path, _user(), _says(_CLAIM))
    assert absence_audit.main(["--transcript", path]) == _FOUND
    assert _CLAIM in log.read_text(encoding="utf-8")


def test_transcript_mode_passes_when_the_owning_tool_was_run_in_the_turn(
    tmp_path: Path, log: Path
) -> None:
    """The same claim after `bazel test` in the same turn is cleared: exit 0, nothing logged."""
    path = _transcript(tmp_path, _user(), _runs("bazel test //:hook"), _says(_CLAIM))
    assert absence_audit.main(["--transcript", path]) == 0
    assert not log.exists()


@pytest.mark.usefixtures("log")
def test_transcript_mode_only_reads_the_last_turn(tmp_path: Path) -> None:
    """A claim in an earlier turn is not this turn's."""
    path = _transcript(tmp_path, _user(), _says(_CLAIM), _user(), _says("all good"))
    assert absence_audit.main(["--transcript", path]) == 0


def test_a_missing_transcript_is_not_an_error(tmp_path: Path) -> None:
    """No file to audit: exit 0."""
    assert absence_audit.main(["--transcript", str(tmp_path / "gone.jsonl")]) == 0


def test_hook_mode_logs_a_claim_but_never_fails_the_turn(tmp_path: Path, log: Path) -> None:
    """Stop-hook JSON on stdin: the transcript is audited, the claim logged, the exit still 0."""
    path = _transcript(tmp_path, _user(), _says(_CLAIM))
    stdin = io.StringIO(_hook_json(path))
    assert absence_audit.main([], stdin=stdin) == 0
    assert _CLAIM in log.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "payload",
    ["not json", "[1, 2]", "{}", '{"transcript_path": ""}', '{"transcript_path": 5}'],
)
def test_hook_mode_ignores_a_payload_with_no_usable_transcript_path(payload: str) -> None:
    """Bad JSON, a non-object, or a missing, empty or non-string path: exit 0, silently."""
    assert absence_audit.main([], stdin=io.StringIO(payload)) == 0


@pytest.mark.usefixtures("log")
def test_main_reads_process_argv_and_stdin_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no arguments the flags come from `sys.argv[1:]` and the hook JSON from `sys.stdin`."""
    monkeypatch.setattr(sys, "argv", ["mikemol-absence-audit", "--selftest"])
    assert absence_audit.main() == 0
    path = _transcript(tmp_path, _user(), _says(_CLAIM))
    monkeypatch.setattr(sys, "argv", ["mikemol-absence-audit"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(_hook_json(path)))
    assert absence_audit.main() == 0

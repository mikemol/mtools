# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The inbound-asks context hook: rows surfaced once, a reader that could not run said, no refusal.

⚑ THE READER IS FAKE, A SHELL SCRIPT UNDER `tmp_path`, and the module's own subprocess runs it, so
no test here spawns anything itself. Each witness sets the project, the temp directory and PATH
under `tmp_path`, so none reads the developer's real queues, real digests or real reader.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from typing import TYPE_CHECKING

from mikemol.hooks import entry, hook_argv, inbound_asks

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

ROW = (
    "UNCLAIMED peer:W3 :: fix the thing :: mikemol-paths-forward --state /x --add "
    "Answer-peer:W3 --enables peer:W3 --caused-by peer:W3"
)
OTHER = "UNCLAIMED peer:W9 :: another :: mikemol-paths-forward --add y"
SHA256_HEX_LENGTH = 64
TIMEOUT = 20.0
SHORT = 0.3


def _project(tmp_path: Path, reader_body: str | None, *, queue: bool = True) -> Path:
    """Build a project with an optional queue file and an optional fake reader in its venv.

    Returns:
        the project directory.

    """
    project = tmp_path / "proj"
    (project / ".claude").mkdir(parents=True)
    if queue:
        (project / ".claude" / "paths-forward.json").write_text("{}", encoding="utf-8")
    if reader_body is not None:
        reader = project / ".venv" / "bin" / inbound_asks.READER
        reader.parent.mkdir(parents=True)
        reader.write_text("#!/bin/sh\n" + reader_body, encoding="utf-8")
        reader.chmod(0o755)
    return project


def _reader_of(project: Path) -> Path:
    """Locate the fake reader a project holds.

    Returns:
        the reader path.

    """
    return project / ".venv" / "bin" / inbound_asks.READER


def _env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, project: Path) -> None:
    """Point the hook at the project, an empty PATH directory and a private temp directory."""
    empty = tmp_path / "emptybin"
    empty.mkdir(exist_ok=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "tmp"))


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    event: str | None,
    session: str = "sess-1",
    timeout: float = TIMEOUT,
) -> tuple[int, str, str]:
    """Drive main with one payload on stdin.

    Returns:
        (rc, stdout, stderr).

    """
    record: dict[str, str] = {"session_id": session}
    if event is not None:
        record["hook_event_name"] = event
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(record)))
    rc = inbound_asks.main(timeout)
    got = capsys.readouterr()
    return rc, got.out, got.err


def _envelope(out: str) -> dict[str, dict[str, str]]:
    """Parse an emitted envelope.

    Returns:
        the hookSpecificOutput record, keyed by its one outer name.

    """
    parsed: dict[str, dict[str, str]] = json.loads(out)
    return parsed


def _context(out: str) -> str:
    """Return the additionalContext of an emitted envelope.

    Returns:
        the context text.

    """
    return _envelope(out)["hookSpecificOutput"]["additionalContext"]


def test_rows_present_emit_context_with_the_rows_and_the_event_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The reader's rows reach the model as additionalContext under the firing event's name."""
    project = _project(tmp_path, f"printf '%s\\n' '{ROW}'\n")
    _env(tmp_path, monkeypatch, project)
    rc, out, err = _run(monkeypatch, capsys, "SessionStart")
    assert (rc, err) == (0, "")
    assert _envelope(out)["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    context = _context(out)
    assert context == inbound_asks.context_for(ROW)
    assert ROW in context
    assert context.splitlines()[-1].startswith("to claim a row")


def test_no_rows_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reader that prints nothing produces no output and exit 0."""
    project = _project(tmp_path, "exit 0\n")
    _env(tmp_path, monkeypatch, project)
    assert _run(monkeypatch, capsys, "SessionStart") == (0, "", "")


def test_no_queue_file_is_silent_even_with_a_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A repo without a loop has no census to run, and the reader is never consulted."""
    project = _project(tmp_path, f"printf '%s\\n' '{ROW}'\n", queue=False)
    _env(tmp_path, monkeypatch, project)
    assert _run(monkeypatch, capsys, "SessionStart") == (0, "", "")


def test_absent_reader_says_so_and_does_not_claim_no_asks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With neither a venv reader nor one on PATH the notice names the absence on both channels."""
    project = _project(tmp_path, None)
    _env(tmp_path, monkeypatch, project)
    rc, out, err = _run(monkeypatch, capsys, "SessionStart")
    context = _context(out)
    assert rc == 0
    assert "COULD NOT RUN" in context
    assert "neither in .venv/bin nor on PATH" in context
    assert "not a statement that no peer ask waits" in context
    assert err == context + "\n"


def test_nonzero_reader_says_so_with_its_first_stderr_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reader that exits non-zero is reported with its code and reason, not read as empty."""
    project = _project(tmp_path, "echo 'bad state' >&2\nexit 3\n")
    _env(tmp_path, monkeypatch, project)
    rc, out, err = _run(monkeypatch, capsys, "SessionStart")
    context = _context(out)
    assert rc == 0
    assert "COULD NOT RUN (exited 3: bad state)" in context
    assert "UNCLAIMED" not in context
    assert err.startswith("inbound: the census of peer asks COULD NOT RUN")


def test_timeout_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reader that outlives the bound is killed and reported, never read as empty."""
    project = _project(tmp_path, "exec /bin/sleep 30\n")
    _env(tmp_path, monkeypatch, project)
    rc, out, _ = _run(monkeypatch, capsys, "SessionStart", timeout=SHORT)
    assert rc == 0
    assert "COULD NOT RUN (timed out after 0.3 s)" in _context(out)


def test_the_event_filter_accepts_two_events_and_ignores_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """SessionStart and UserPromptSubmit emit; Stop, a tool event and no event are ignored."""
    project = _project(tmp_path, f"printf '%s\\n' '{ROW}'\n")
    _env(tmp_path, monkeypatch, project)
    assert inbound_asks.EVENTS == ("SessionStart", "UserPromptSubmit")
    for event in ("Stop", "PreToolUse", None):
        assert _run(monkeypatch, capsys, event) == (0, "", "")
    prompt = _run(monkeypatch, capsys, "UserPromptSubmit", session="fresh")
    assert _envelope(prompt[1])["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_a_prompt_repeating_the_last_emission_is_silent_until_the_rows_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The flood guard: SessionStart emits, the next identical prompt does not, a change does."""
    project = _project(tmp_path, f"printf '%s\\n' '{ROW}'\n")
    _env(tmp_path, monkeypatch, project)
    assert _run(monkeypatch, capsys, "SessionStart")[1]
    assert _run(monkeypatch, capsys, "UserPromptSubmit") == (0, "", "")
    assert _run(monkeypatch, capsys, "SessionStart")[1]
    _reader_of(project).write_text(
        f"#!/bin/sh\nprintf '%s\\n' '{ROW}' '{OTHER}'\n", encoding="utf-8"
    )
    changed = _run(monkeypatch, capsys, "UserPromptSubmit")
    assert OTHER in _context(changed[1])


def test_a_failure_notice_is_said_once_per_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same failure on the next prompt adds nothing; the stderr line is not repeated."""
    project = _project(tmp_path, None)
    _env(tmp_path, monkeypatch, project)
    first = _run(monkeypatch, capsys, "UserPromptSubmit")
    second = _run(monkeypatch, capsys, "UserPromptSubmit")
    assert first[1]
    assert first[2]
    assert second == (0, "", "")


def test_main_exits_zero_and_stays_silent_on_a_garbage_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unparseable and non-object payloads carry no event, so nothing is emitted."""
    project = _project(tmp_path, f"printf '%s\\n' '{ROW}'\n")
    _env(tmp_path, monkeypatch, project)
    for raw in ("not json", "[1, 2]", ""):
        monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
        assert inbound_asks.main() == 0
        assert not capsys.readouterr().out


def test_read_payload_returns_the_record_or_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """A JSON object is returned as a record; anything else is an empty record."""
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"a": 1}'))
    assert inbound_asks.read_payload() == {"a": 1}
    monkeypatch.setattr(sys, "stdin", io.StringIO("{"))
    assert inbound_asks.read_payload() == {}


def test_project_dir_prefers_the_env_and_falls_back_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE_PROJECT_DIR wins; without it the working directory is the project."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "a"))
    assert inbound_asks.project_dir() == tmp_path / "a"
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    monkeypatch.chdir(tmp_path)
    assert inbound_asks.project_dir() == tmp_path


def test_find_reader_prefers_the_venv_then_path_then_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The project's venv reader is chosen over PATH; PATH is the fallback; else None."""
    project = _project(tmp_path, "exit 0\n")
    on_path = tmp_path / "pathbin"
    on_path.mkdir()
    path_reader = on_path / inbound_asks.READER
    path_reader.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path_reader.chmod(0o755)
    monkeypatch.setenv("PATH", str(on_path))
    assert inbound_asks.find_reader(project) == str(_reader_of(project))
    bare = _project(tmp_path / "bare", None)
    assert inbound_asks.find_reader(bare) == str(path_reader)
    monkeypatch.setenv("PATH", str(tmp_path / "nothing"))
    assert inbound_asks.find_reader(bare) is None


def test_find_reader_skips_a_non_executable_venv_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A venv file without the execute bit is not a reader."""
    project = _project(tmp_path, "exit 0\n")
    _reader_of(project).chmod(0o644)
    monkeypatch.setenv("PATH", str(tmp_path / "nothing"))
    assert inbound_asks.find_reader(project) is None


def test_reader_argv_is_constants_plus_the_state_as_one_word(tmp_path: Path) -> None:
    """The argv is a list, the state path is one element, and nothing is shell-joined."""
    state = tmp_path / "a b" / "paths-forward.json"
    assert inbound_asks.reader_argv("/r", state) == ["/r", "--state", str(state), "--inbound"]


def test_run_reader_reports_ok_nonzero_timeout_and_unstartable(tmp_path: Path) -> None:
    """The four outcomes of one bounded run."""
    state = tmp_path / "s.json"
    ok = _reader_of(_project(tmp_path / "ok", "echo hi\n"))
    assert inbound_asks.run_reader(str(ok), state, TIMEOUT) == ("hi\n", "")
    bad = _reader_of(_project(tmp_path / "bad", "exit 2\n"))
    assert inbound_asks.run_reader(str(bad), state, TIMEOUT) == (None, "exited 2")
    slow = _reader_of(_project(tmp_path / "slow", "exec /bin/sleep 30\n"))
    assert inbound_asks.run_reader(str(slow), state, SHORT) == (None, "timed out after 0.3 s")
    missing = inbound_asks.run_reader(str(tmp_path / "no-such"), state, TIMEOUT)
    assert missing[0] is None
    assert missing[1].startswith("could not start:")


def test_context_for_wraps_rows_and_drops_blank_lines() -> None:
    """The heading, the non-blank rows in order, then the one claim-or-decline line."""
    lines = inbound_asks.context_for(f"{ROW}\n\n{OTHER}\n").splitlines()
    assert lines[1:3] == [ROW, OTHER]
    assert lines[0].startswith("inbound: peer ask(s)")
    assert len(lines) == len((ROW, OTHER)) + 2
    assert not inbound_asks.context_for("\n  \n")


def test_failure_notice_names_the_reason_and_the_manual_command() -> None:
    """The notice carries the reason, refuses the no-asks reading and names the hand command."""
    got = inbound_asks.failure_notice("why")
    assert "(why)" in got
    assert "not a statement that no peer ask waits" in got
    assert "mikemol-paths-forward --state .claude/paths-forward.json --inbound" in got


def test_build_context_distinguishes_silent_rows_and_failure(tmp_path: Path) -> None:
    """No queue is silent, rows are context, a failing reader is a flagged notice."""
    no_queue = _project(tmp_path / "a", "echo x\n", queue=False)
    assert inbound_asks.build_context(no_queue, TIMEOUT) == ("", False)
    rows = _project(tmp_path / "b", "echo x\n")
    assert inbound_asks.build_context(rows, TIMEOUT) == (inbound_asks.context_for("x"), False)
    broken = _project(tmp_path / "c", "exit 1\n")
    assert inbound_asks.build_context(broken, TIMEOUT) == (
        inbound_asks.failure_notice("exited 1"),
        True,
    )


def test_digest_path_is_per_session_and_refuses_an_unusable_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A safe id maps under the temp directory; empty or path-like ids map to nothing."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    assert inbound_asks.digest_path("abc-1") == tmp_path / "mikemol-inbound-asks" / "abc-1"
    assert inbound_asks.digest_path("") is None
    assert inbound_asks.digest_path("../x") is None


def test_digest_of_is_stable_and_distinguishes_text() -> None:
    """Equal text hashes equal; different text hashes differently."""
    assert inbound_asks.digest_of("a") == inbound_asks.digest_of("a")
    assert inbound_asks.digest_of("a") != inbound_asks.digest_of("b")
    assert len(inbound_asks.digest_of("a")) == SHA256_HEX_LENGTH


def test_unchanged_since_last_records_and_compares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first sight is new, a repeat prompt is unchanged, a repeat SessionStart is not."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    assert not inbound_asks.unchanged_since_last("UserPromptSubmit", "s", "t1")
    assert inbound_asks.unchanged_since_last("UserPromptSubmit", "s", "t1")
    assert not inbound_asks.unchanged_since_last("SessionStart", "s", "t1")
    assert not inbound_asks.unchanged_since_last("UserPromptSubmit", "s", "t2")
    assert not inbound_asks.unchanged_since_last("UserPromptSubmit", "", "t2")
    assert not inbound_asks.unchanged_since_last("UserPromptSubmit", "", "t2")


def test_unchanged_since_last_survives_an_unwritable_temp_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A temp directory that cannot be written means emit, never crash."""
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(tempfile, "tempdir", str(blocker))
    assert not inbound_asks.unchanged_since_last("UserPromptSubmit", "s", "t")
    assert not inbound_asks.unchanged_since_last("UserPromptSubmit", "s", "t")


def test_the_console_entry_refuses_an_argument_and_runs_without_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The entry point goes through the argv contract, then runs the hook."""
    project = _project(tmp_path, f"printf '%s\\n' '{ROW}'\n")
    _env(tmp_path, monkeypatch, project)
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-inbound-asks", "--help"])
    assert entry.inbound_asks_main() == hook_argv.EXIT_REFUSED
    assert "refusing argument(s)" in capsys.readouterr().err
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-inbound-asks"])
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name": "SessionStart"}'))
    assert entry.inbound_asks_main() == 0
    assert ROW in _context(capsys.readouterr().out)

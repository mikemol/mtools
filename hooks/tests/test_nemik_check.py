# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The nemik-check context hook: this repo's rows only, a failed reader said, no refusal.

⚑ THE READER IS FAKE, A SHELL SCRIPT UNDER `tmp_path` that prints a canned report, and the module's
own subprocess runs it, so no test here spawns anything itself. Each witness sets the project, the
temp directory, PATH and NEMIK_CHECK under `tmp_path`, so none reads the developer's real queues,
real digests or real reader. The project's basename is the repo the hook reports on.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from typing import TYPE_CHECKING

from mikemol.hooks import entry, hook_argv, nemik_check

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

REPO = "myrepo"
HEADER = f"OK        {REPO}"
WARN = "  Warning   W7     blocked_on names a waypoint that has already landed: trim it"
WARN2 = "  Warning   --     more than one working card: keep one, return the others to ready"
NEWROW = "  Warning   W99    a row that appeared between two prompts"
VIOL = "  VIOLATES  W9     a blocked waypoint must carry blockedOn and blockedKind"
OTHER_ROW = "  Warning   W1     another repo's row that must never reach this session"
REPORT = (
    f"provenance: nemik abc123\nprovenance: queue myrepo uncommitted\n"
    f"OK        alpha\n{OTHER_ROW}\n"
    f"{HEADER}\n{WARN}\n{WARN2}\nOK        omega\n{OTHER_ROW}\n"
)
SHA256_HEX_LENGTH = 64
TIMEOUT = 20.0
SHORT = 0.3
RC_THREE = 3


def _script(path: Path, body: str) -> Path:
    """Write an executable shell script at `path`.

    Returns:
        the path.

    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, report: str | None, *, exit_code: int = 0
) -> Path:
    """Build the project, a fake reader printing `report`, and the environment pointing at both.

    Returns:
        the project directory, whose basename is REPO.

    """
    project = tmp_path / "fleet" / REPO
    project.mkdir(parents=True)
    empty = tmp_path / "emptybin"
    empty.mkdir(exist_ok=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "tmp"))
    if report is None:
        monkeypatch.delenv("NEMIK_CHECK", raising=False)
        return project
    canned = tmp_path / "report.txt"
    canned.write_text(report, encoding="utf-8")
    reader = _script(tmp_path / "reader", f"/bin/cat '{canned}'\nexit {exit_code}\n")
    monkeypatch.setenv("NEMIK_CHECK", str(reader))
    return project


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
    rc = nemik_check.main(timeout)
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


def test_this_repos_rows_are_quoted_and_another_repos_rows_are_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The rows under this repo's header reach the model verbatim; neighbours' rows do not."""
    _setup(tmp_path, monkeypatch, REPORT)
    rc, out, err = _run(monkeypatch, capsys, "SessionStart")
    assert (rc, err) == (0, "")
    assert _envelope(out)["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    context = _context(out)
    assert WARN in context
    assert WARN2 in context
    assert REPO in context
    assert OTHER_ROW not in context
    assert "alpha" not in context
    assert "omega" not in context
    assert "provenance" not in context
    assert "A Warning is not cosmetic" in context
    assert "fix them" in context


def test_a_clean_repo_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A header with no indented row beneath it produces no output."""
    _setup(tmp_path, monkeypatch, f"provenance: x\n{HEADER}\nOK        zeta\n{OTHER_ROW}\n")
    assert _run(monkeypatch, capsys, "SessionStart") == (0, "", "")


def test_a_repo_absent_from_the_output_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reader that does not mention this repo says nothing about it, and the hook is silent."""
    _setup(tmp_path, monkeypatch, f"OK        alpha\n{OTHER_ROW}\n")
    assert _run(monkeypatch, capsys, "SessionStart") == (0, "", "")


def test_violates_rows_and_header_are_quoted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A VIOLATES header and VIOLATES rows are handed over like warnings."""
    header = f"VIOLATES  {REPO}"
    _setup(tmp_path, monkeypatch, f"{header}\n{VIOL}\n")
    context = _context(_run(monkeypatch, capsys, "UserPromptSubmit")[1])
    assert header in context
    assert VIOL in context


def test_the_reader_is_run_with_the_fleet_root_as_one_word(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The reader receives `--root <project parent>`; the argv holds exactly that."""
    _setup(tmp_path, monkeypatch, "")
    argv_file = tmp_path / "argv.txt"
    _script(tmp_path / "reader", f"printf '%s|' \"$@\" > '{argv_file}'\n")
    _run(monkeypatch, capsys, "SessionStart")
    assert argv_file.read_text(encoding="utf-8") == f"--root|{tmp_path / 'fleet'}|"


def test_absent_reader_says_so_and_does_not_claim_the_queue_is_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no env reader, none on PATH and no sibling venv, the notice is said on both channels."""
    _setup(tmp_path, monkeypatch, None)
    rc, out, err = _run(monkeypatch, capsys, "SessionStart")
    context = _context(out)
    assert rc == 0
    assert "COULD NOT RUN" in context
    assert "not on PATH" in context
    assert "not a statement that the queue is clean" in context
    assert err == context + "\n"


def test_nonzero_reader_with_no_block_says_so_with_its_first_stderr_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reader that exits non-zero and shows no block for this repo is a failure, not empty."""
    _setup(tmp_path, monkeypatch, "")
    _script(tmp_path / "reader", f"/bin/echo 'bad root' >&2\nexit {RC_THREE}\n")
    rc, out, err = _run(monkeypatch, capsys, "SessionStart")
    assert rc == 0
    assert "COULD NOT RUN (exited 3: bad root)" in _context(out)
    assert err.startswith("nemik: the check of this repo's queue COULD NOT RUN")


def test_nonzero_reader_with_this_repos_block_is_still_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reader that exits 1 because some repo violates still has this repo's rows read."""
    _setup(tmp_path, monkeypatch, REPORT, exit_code=1)
    rc, out, err = _run(monkeypatch, capsys, "SessionStart")
    assert (rc, err) == (0, "")
    context = _context(out)
    assert WARN in context
    assert "COULD NOT RUN" not in context


def test_timeout_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reader that outlives the bound is killed and reported, never read as clean."""
    _setup(tmp_path, monkeypatch, "")
    _script(tmp_path / "reader", "exec /bin/sleep 30\n")
    rc, out, _ = _run(monkeypatch, capsys, "SessionStart", timeout=SHORT)
    assert rc == 0
    assert "COULD NOT RUN (timed out after 0.3 s)" in _context(out)


def test_the_event_filter_accepts_two_events_and_ignores_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """SessionStart and UserPromptSubmit emit; Stop, a tool event and no event are ignored."""
    _setup(tmp_path, monkeypatch, REPORT)
    assert nemik_check.EVENTS == ("SessionStart", "UserPromptSubmit")
    for event in ("Stop", "PreToolUse", None):
        assert _run(monkeypatch, capsys, event) == (0, "", "")
    prompt = _run(monkeypatch, capsys, "UserPromptSubmit", session="fresh")
    assert _envelope(prompt[1])["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_a_prompt_repeating_the_last_emission_is_silent_until_the_rows_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The flood guard: SessionStart emits, the next identical prompt does not, a change does."""
    _setup(tmp_path, monkeypatch, REPORT)
    assert _run(monkeypatch, capsys, "SessionStart")[1]
    assert _run(monkeypatch, capsys, "UserPromptSubmit") == (0, "", "")
    assert _run(monkeypatch, capsys, "SessionStart")[1]
    changed_report = REPORT.replace(WARN2, WARN2 + "\n" + NEWROW)
    (tmp_path / "report.txt").write_text(changed_report, encoding="utf-8")
    changed = _run(monkeypatch, capsys, "UserPromptSubmit")
    assert NEWROW in _context(changed[1])


def test_a_failure_notice_is_said_once_per_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same failure on the next prompt adds nothing; the stderr line is not repeated."""
    _setup(tmp_path, monkeypatch, None)
    first = _run(monkeypatch, capsys, "UserPromptSubmit")
    second = _run(monkeypatch, capsys, "UserPromptSubmit")
    assert first[1]
    assert first[2]
    assert second == (0, "", "")


def test_main_exits_zero_and_stays_silent_on_a_garbage_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unparseable and non-object payloads carry no event, so nothing is emitted."""
    _setup(tmp_path, monkeypatch, REPORT)
    for raw in ("not json", "[1, 2]", ""):
        monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
        assert nemik_check.main() == 0
        assert not capsys.readouterr().out


def test_read_payload_returns_the_record_or_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """A JSON object is returned as a record; anything else is an empty record."""
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"a": 1}'))
    assert nemik_check.read_payload() == {"a": 1}
    monkeypatch.setattr(sys, "stdin", io.StringIO("{"))
    assert nemik_check.read_payload() == {}


def test_project_dir_prefers_the_env_and_falls_back_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE_PROJECT_DIR wins; without it the working directory is the project."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "a"))
    assert nemik_check.project_dir() == tmp_path / "a"
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    monkeypatch.chdir(tmp_path)
    assert nemik_check.project_dir() == tmp_path


def test_is_runnable_wants_an_executable_file(tmp_path: Path) -> None:
    """A file with the execute bit is runnable; a plain file and a directory are not."""
    assert nemik_check.is_runnable(_script(tmp_path / "x", "exit 0\n"))
    plain = tmp_path / "plain"
    plain.write_text("x", encoding="utf-8")
    assert not nemik_check.is_runnable(plain)
    assert not nemik_check.is_runnable(tmp_path)


def test_find_reader_prefers_env_then_path_then_the_sibling_venv_then_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The three places in their order, and None when none holds a reader."""
    project = tmp_path / "fleet" / REPO
    project.mkdir(parents=True)
    sibling = _script(tmp_path / "fleet" / "nemik" / ".venv" / "bin" / "nemik-check", "exit 0\n")
    on_path = _script(tmp_path / "pathbin" / "nemik-check", "exit 0\n")
    named = _script(tmp_path / "named", "exit 0\n")
    monkeypatch.setenv("PATH", str(on_path.parent))
    monkeypatch.setenv("NEMIK_CHECK", str(named))
    assert nemik_check.find_reader(project) == str(named)
    monkeypatch.delenv("NEMIK_CHECK")
    assert nemik_check.find_reader(project) == str(on_path)
    monkeypatch.setenv("PATH", str(tmp_path / "nothing"))
    assert nemik_check.find_reader(project) == str(sibling)
    sibling.chmod(0o644)
    assert nemik_check.find_reader(project) is None


def test_find_reader_skips_a_non_executable_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An env-named file without the execute bit is not a reader; the search goes on."""
    project = tmp_path / "fleet" / REPO
    project.mkdir(parents=True)
    named = _script(tmp_path / "named", "exit 0\n")
    named.chmod(0o644)
    monkeypatch.setenv("NEMIK_CHECK", str(named))
    monkeypatch.setenv("PATH", str(tmp_path / "nothing"))
    assert nemik_check.find_reader(project) is None


def test_reader_argv_is_constants_plus_the_root_as_one_word(tmp_path: Path) -> None:
    """The argv is a list, the root is one element, and nothing is shell-joined."""
    root = tmp_path / "a b"
    assert nemik_check.reader_argv("/r", root) == ["/r", "--root", str(root)]


def test_run_reader_reports_ok_nonzero_timeout_and_unstartable(tmp_path: Path) -> None:
    """The four outcomes of one bounded run; a non-zero exit still carries its stdout."""
    ok = _script(tmp_path / "ok", "/bin/echo hi\n")
    assert nemik_check.run_reader(str(ok), tmp_path, TIMEOUT) == ("hi\n", "")
    bad = _script(tmp_path / "bad", "/bin/echo out\nexit 2\n")
    assert nemik_check.run_reader(str(bad), tmp_path, TIMEOUT) == ("out\n", "exited 2")
    slow = _script(tmp_path / "slow", "exec /bin/sleep 30\n")
    assert nemik_check.run_reader(str(slow), tmp_path, SHORT) == (None, "timed out after 0.3 s")
    missing = nemik_check.run_reader(str(tmp_path / "no-such"), tmp_path, TIMEOUT)
    assert missing[0] is None
    assert missing[1].startswith("could not start:")


def test_is_header_of_wants_a_status_word_and_exactly_the_repo() -> None:
    """OK and VIOLATES headers of the named repo match; other repos, words and blanks do not."""
    assert nemik_check.is_header_of("OK        r", "r")
    assert nemik_check.is_header_of("VIOLATES  r", "r")
    assert not nemik_check.is_header_of("OK        rr", "r")
    assert not nemik_check.is_header_of("provenance: queue r committed", "r")
    assert not nemik_check.is_header_of("OK        r extra", "r")
    assert not nemik_check.is_header_of("", "r")


def test_repo_block_takes_the_header_and_only_its_indented_rows() -> None:
    """The block ends at the next unindented line; an absent repo is None; headers are kept."""
    assert nemik_check.repo_block(REPORT, REPO) == (HEADER, [WARN, WARN2])
    assert nemik_check.repo_block(REPORT, "nobody") is None
    assert nemik_check.repo_block(f"{HEADER}\n\n{WARN}\n", REPO) == (HEADER, [WARN])
    assert nemik_check.repo_block(f"{WARN}\n{HEADER}\n", REPO) == (HEADER, [])


def test_context_for_names_the_repo_quotes_the_rows_and_says_to_fix_them() -> None:
    """The heading, the header, the rows in order, then the one fix-them line; no rows is empty."""
    lines = nemik_check.context_for(REPO, HEADER, [WARN, VIOL]).splitlines()
    assert lines[0] == f"nemik: the fleet reader reports on {REPO}:"
    assert lines[1:4] == [HEADER, WARN, VIOL]
    assert lines[-1].startswith("these are nemik's shapes: fix them")
    assert len(lines) == len((WARN, VIOL)) + 3
    assert not nemik_check.context_for(REPO, HEADER, [])


def test_failure_notice_names_the_reason_and_refuses_the_clean_reading() -> None:
    """The notice carries the reason, refuses the clean-queue reading and names the hand command."""
    got = nemik_check.failure_notice("why")
    assert "(why)" in got
    assert "not a statement that the queue is clean" in got
    assert "run `nemik-check` by hand" in got


def test_build_context_distinguishes_silent_rows_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean block is silent, rows are context, an unreadable run is a flagged notice."""
    project = _setup(tmp_path, monkeypatch, f"{HEADER}\n")
    assert nemik_check.build_context(project, TIMEOUT) == ("", False)
    (tmp_path / "report.txt").write_text(REPORT, encoding="utf-8")
    assert nemik_check.build_context(project, TIMEOUT) == (
        nemik_check.context_for(REPO, HEADER, [WARN, WARN2]),
        False,
    )
    _script(tmp_path / "reader", "exit 1\n")
    assert nemik_check.build_context(project, TIMEOUT) == (
        nemik_check.failure_notice("exited 1"),
        True,
    )


def test_digest_path_is_per_session_and_refuses_an_unusable_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A safe id maps under the temp directory; empty or path-like ids map to nothing."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    assert nemik_check.digest_path("abc-1") == tmp_path / "mikemol-nemik-check" / "abc-1"
    assert nemik_check.digest_path("") is None
    assert nemik_check.digest_path("../x") is None


def test_digest_of_is_stable_and_distinguishes_text() -> None:
    """Equal text hashes equal; different text hashes differently."""
    assert nemik_check.digest_of("a") == nemik_check.digest_of("a")
    assert nemik_check.digest_of("a") != nemik_check.digest_of("b")
    assert len(nemik_check.digest_of("a")) == SHA256_HEX_LENGTH


def test_unchanged_since_last_records_and_compares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first sight is new, a repeat prompt is unchanged, a repeat SessionStart is not."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    assert not nemik_check.unchanged_since_last("UserPromptSubmit", "s", "t1")
    assert nemik_check.unchanged_since_last("UserPromptSubmit", "s", "t1")
    assert not nemik_check.unchanged_since_last("SessionStart", "s", "t1")
    assert not nemik_check.unchanged_since_last("UserPromptSubmit", "s", "t2")
    assert not nemik_check.unchanged_since_last("UserPromptSubmit", "", "t2")
    assert not nemik_check.unchanged_since_last("UserPromptSubmit", "", "t2")


def test_unchanged_since_last_survives_an_unwritable_temp_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A temp directory that cannot be written means emit, never crash."""
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(tempfile, "tempdir", str(blocker))
    assert not nemik_check.unchanged_since_last("UserPromptSubmit", "s", "t")
    assert not nemik_check.unchanged_since_last("UserPromptSubmit", "s", "t")


def test_the_console_entry_refuses_an_argument_and_runs_without_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The entry point goes through the argv contract, then runs the hook."""
    _setup(tmp_path, monkeypatch, REPORT)
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-nemik-check", "--help"])
    assert entry.nemik_check_main() == hook_argv.EXIT_REFUSED
    assert "refusing argument(s)" in capsys.readouterr().err
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-nemik-check"])
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"hook_event_name": "SessionStart"}'))
    assert entry.nemik_check_main() == 0
    assert WARN in _context(capsys.readouterr().out)


def _stateful(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, exit_code: int = 0, queue: bool = True
) -> tuple[Path, Path]:
    """Build a project whose fake reader counts its spawns, with an optional queue file.

    Returns:
        (project, counter file): the counter holds one `x` per reader spawn.

    """
    project = _setup(tmp_path, monkeypatch, REPORT, exit_code=exit_code)
    if queue:
        (project / ".claude").mkdir()
        (project / ".claude" / "paths-forward.json").write_text("{}", encoding="utf-8")
    counter = tmp_path / "counter.txt"
    _script(
        tmp_path / "reader",
        f"printf x >> '{counter}'\n/bin/cat '{tmp_path / 'report.txt'}'\nexit {exit_code}\n",
    )
    return project, counter


def _spawns(counter: Path) -> int:
    """Count the reader spawns recorded so far.

    Returns:
        the number of spawns.

    """
    return len(counter.read_text(encoding="utf-8")) if counter.exists() else 0


def test_an_unchanged_queue_file_means_the_next_prompt_does_not_spawn_the_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """After a successful run, a prompt with a byte-identical queue file is silent, no spawn."""
    _, counter = _stateful(tmp_path, monkeypatch)
    assert _run(monkeypatch, capsys, "UserPromptSubmit")[1]
    assert _spawns(counter) == 1
    assert _run(monkeypatch, capsys, "UserPromptSubmit") == (0, "", "")
    assert _spawns(counter) == 1


def test_a_changed_queue_file_means_the_next_prompt_spawns_the_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A queue file that differs from the recorded one runs the reader again."""
    project, counter = _stateful(tmp_path, monkeypatch)
    _run(monkeypatch, capsys, "UserPromptSubmit")
    (project / ".claude" / "paths-forward.json").write_text('{"a": 1}', encoding="utf-8")
    _run(monkeypatch, capsys, "UserPromptSubmit")
    assert _spawns(counter) == len("xx")


def test_session_start_always_spawns_the_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """SessionStart ignores the recorded queue digest."""
    _, counter = _stateful(tmp_path, monkeypatch)
    _run(monkeypatch, capsys, "SessionStart")
    assert _run(monkeypatch, capsys, "SessionStart")[1]
    assert _spawns(counter) == len("xx")


def test_a_missing_queue_file_never_skips_the_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without a readable queue file there is nothing to compare, so every prompt spawns."""
    _, counter = _stateful(tmp_path, monkeypatch, queue=False)
    _run(monkeypatch, capsys, "UserPromptSubmit")
    _run(monkeypatch, capsys, "UserPromptSubmit")
    assert _spawns(counter) == len("xx")


def test_a_failed_run_records_no_queue_digest_so_the_next_prompt_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A run that could not read this repo is not recorded; the same queue file spawns again."""
    _, counter = _stateful(tmp_path, monkeypatch, exit_code=1)
    (tmp_path / "report.txt").write_text("", encoding="utf-8")
    _run(monkeypatch, capsys, "UserPromptSubmit")
    _run(monkeypatch, capsys, "UserPromptSubmit")
    assert _spawns(counter) == len("xx")


def test_an_unwritable_temp_directory_never_skips_the_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """If the digest cannot be recorded, every prompt spawns the reader."""
    _, counter = _stateful(tmp_path, monkeypatch)
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(tempfile, "tempdir", str(blocker))
    _run(monkeypatch, capsys, "UserPromptSubmit")
    _run(monkeypatch, capsys, "UserPromptSubmit")
    assert _spawns(counter) == len("xx")


def test_state_digest_hashes_the_queue_file_and_is_none_when_missing(tmp_path: Path) -> None:
    """The digest is the sha256 of the bytes; a missing file is None, never an empty digest."""
    assert nemik_check.state_digest(tmp_path) is None
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "paths-forward.json").write_text("a", encoding="utf-8")
    assert nemik_check.state_digest(tmp_path) == nemik_check.digest_of("a")


def test_state_digest_path_sits_beside_the_emission_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A usable id maps to `<id>.state` under the same directory; an unusable id maps to None."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    assert nemik_check.state_digest_path("abc") == tmp_path / "mikemol-nemik-check" / "abc.state"
    assert nemik_check.state_digest_path("") is None


def test_record_state_and_state_unchanged_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing is unchanged until recorded; then equal is unchanged, and different is not."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    assert not nemik_check.state_unchanged("s", "d1")
    nemik_check.record_state("s", "d1")
    assert nemik_check.state_unchanged("s", "d1")
    assert not nemik_check.state_unchanged("s", "d2")
    assert not nemik_check.state_unchanged("", "d1")
    nemik_check.record_state("", "d1")


def test_record_state_survives_an_unwritable_temp_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A temp directory that cannot be written records nothing and does not crash."""
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(tempfile, "tempdir", str(blocker))
    nemik_check.record_state("s", "d1")
    assert not nemik_check.state_unchanged("s", "d1")

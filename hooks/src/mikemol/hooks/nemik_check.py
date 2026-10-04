# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""SessionStart and UserPromptSubmit: surface nemik's findings about THIS repo's queue as context.

⚑ THE SIBLING OF `inbound_asks`. `nemik-check` validates every workstream's queue against nemik's
SHACL shapes and prints one block per repo: a header line `OK        <repo>` or
`VIOLATES  <repo>`, then indented rows (`  Warning   <W-or-->    <message>`, `  VIOLATES ...`)
until the next unindented line, after `provenance:` lines. A session learned of its own rows only
when it ran the reader. This hook runs it and hands the model ONLY this project's rows as
ADDITIONAL CONTEXT; the repo is the basename of the project directory.

⚑ IT NEVER REFUSES AND HAS NO STOP BEHAVIOUR, ON PURPOSE, exactly like `inbound_asks`: the exit
status is always 0 and the only output is context. The contract is the same one: exit 0 with
`{"hookSpecificOutput": {"hookEventName": <event>, "additionalContext": <text>}}` on stdout; a
stderr line reaches the user's transcript and not the model, so a failure is stated in both.

⚑ A TOOL THAT CANNOT BE RUN IS SAID, NEVER READ AS 'THE QUEUE IS CLEAN'. An absent reader, a
timeout, and a non-zero exit with no block for this repo each produce one notice that does not
claim the queue is clean. A non-zero exit that DOES carry this repo's block is output: the reader
may exit non-zero because some repo violates, and that is not a failure to read this one.

⚑ SILENT when this repo's block has no indented rows, or the repo is absent from the output.

⚑ THE FLOOD GUARD IS ONE DIGEST FILE PER SESSION under the temp directory, as in `inbound_asks`:
SessionStart always emits what it finds, UserPromptSubmit only when the text changed, a failure
notice is said once, and a payload without a usable session id emits every time.

⚑ THE READER IS SLOW (MEASURED BY THE COORDINATOR: 12.3 s wall over 19 repos, exit 0), so
UserPromptSubmit does not spawn it when this project's `.claude/paths-forward.json` is
byte-identical (sha256) to the file at the last SUCCESSFUL run, recorded in `<session_id>.state`
beside the emission digest. The findings are a function of the queues, so an unchanged queue file
means unchanged findings of this repo's own making. SessionStart always runs it. A missing or
unreadable queue file, no session id, an unwritable temp directory and a failed run (never
recorded, so the next prompt retries) all mean run it: the skip is never taken on doubt.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from mikemol.hooks.payload import as_record, text_of

READER = "nemik-check"
READER_ENV = "NEMIK_CHECK"
STATE_RELATIVE = Path(".claude") / "paths-forward.json"
EVENTS = ("SessionStart", "UserPromptSubmit")
READER_TIMEOUT = 60.0
PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"
_SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
_STATUSES = ("OK", "VIOLATES")
_FOOTER = (
    "these are nemik's shapes: fix them (the remedy is in each row). A Warning is not cosmetic."
)


def project_dir() -> Path:
    """Return the project the hook serves: CLAUDE_PROJECT_DIR, else the working directory.

    Returns:
        the project directory.

    """
    return Path(os.environ.get(PROJECT_DIR_ENV) or Path.cwd()).absolute()


def is_runnable(path: Path) -> bool:
    """Say whether a path is an executable file.

    Returns:
        True when it is a file with the execute bit.

    """
    return path.is_file() and os.access(path, os.X_OK)


def find_reader(project: Path) -> str | None:
    """Find the reader: the NEMIK_CHECK env, then PATH, then the sibling nemik checkout's venv.

    Returns:
        the reader path, or None when none of the three holds one.

    """
    named = os.environ.get(READER_ENV, "")
    if named and is_runnable(Path(named)):
        return named
    found = shutil.which(READER)
    if found:
        return found
    sibling = project.parent / "nemik" / ".venv" / "bin" / READER
    return str(sibling) if is_runnable(sibling) else None


def reader_argv(reader: str, root: Path) -> list[str]:
    """Spell the reader's argv: module constants plus the fleet root as one word.

    Returns:
        the argv, never passed through a shell.

    """
    return [reader, "--root", str(root)]


def run_reader(reader: str, root: Path, timeout: float) -> tuple[str | None, str]:
    """Run the reader once, bounded.

    Returns:
        (stdout, why): why is empty on exit 0 and names the non-zero status otherwise, stdout
        still carried; (None, why) when it could not start or timed out.

    """
    try:
        done = subprocess.run(
            reader_argv(reader, root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout:g} s"
    except OSError as err:
        return None, f"could not start: {err}"
    if done.returncode != 0:
        detail = done.stderr.strip().splitlines()
        return done.stdout, f"exited {done.returncode}" + (f": {detail[0]}" if detail else "")
    return done.stdout, ""


def is_header_of(line: str, repo: str) -> bool:
    """Say whether an unindented line is the status header of the named repo.

    Returns:
        True for `OK <repo>` or `VIOLATES <repo>`.

    """
    words = line.split()
    return words[:1] != [] and words[0] in _STATUSES and words[1:] == [repo]


def repo_block(output: str, repo: str) -> tuple[str, list[str]] | None:
    """Extract one repo's header line and indented rows from the reader's output.

    Returns:
        (header, rows), or None when the repo has no header line in the output.

    """
    header: str | None = None
    rows: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        if line[0] not in " \t":
            if header is not None:
                break
            if is_header_of(line, repo):
                header = line.rstrip()
        elif header is not None:
            rows.append(line.rstrip())
    if header is None:
        return None
    return header, rows


def context_for(repo: str, header: str, rows: list[str]) -> str:
    """Wrap the repo's rows in a heading naming it and the one fix-them line.

    Returns:
        the context text, or the empty string when there is no row.

    """
    if not rows:
        return ""
    heading = f"nemik: the fleet reader reports on {repo}:"
    return "\n".join([heading, header, *rows, _FOOTER])


def failure_notice(why: str) -> str:
    """State that the check could not run, without claiming the queue is clean.

    Returns:
        the notice text.

    """
    return (
        f"nemik: the check of this repo's queue COULD NOT RUN ({why}). This is not a statement "
        f"that the queue is clean; run `{READER}` by hand."
    )


def build_context(project: Path, timeout: float) -> tuple[str, bool]:
    """Decide what the session should be told for this project.

    Returns:
        (text, failed): empty text when there is nothing to say; failed marks a notice.

    """
    reader = find_reader(project)
    if reader is None:
        why = f"{READER} is not named by {READER_ENV}, not on PATH, and not in a sibling nemik venv"
        return failure_notice(why), True
    out, why = run_reader(reader, project.parent, timeout)
    block = repo_block(out, project.name) if out is not None else None
    if block is not None:
        return context_for(project.name, *block), False
    if why:
        return failure_notice(why), True
    return "", False


def digest_path(session_id: str) -> Path | None:
    """Locate the per-session digest file, or None for an unusable session id.

    Returns:
        the path under the temp directory.

    """
    if not _SESSION_ID.fullmatch(session_id):
        return None
    return Path(tempfile.gettempdir()) / "mikemol-nemik-check" / session_id


def digest_of(text: str) -> str:
    """Hash the context text.

    Returns:
        the hex digest.

    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def unchanged_since_last(event: str, session_id: str, text: str) -> bool:
    """Say whether UserPromptSubmit would repeat the last emission, and record this one.

    Returns:
        True when the event is UserPromptSubmit and the digest matches the stored one.

    """
    path = digest_path(session_id)
    if path is None:
        return False
    digest = digest_of(text)
    try:
        same = path.read_text(encoding="utf-8") == digest
    except OSError:
        same = False
    if same and event == "UserPromptSubmit":
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(digest, encoding="utf-8")
    except OSError:
        return False
    return False


def read_payload() -> dict[str, object]:
    """Read the harness payload from stdin; anything unreadable is an empty record.

    Returns:
        the payload record.

    """
    try:
        raw: object = json.load(sys.stdin)
    except (ValueError, OSError):
        return {}
    return as_record(raw)


def state_digest(project: Path) -> str | None:
    """Hash the project's queue file.

    Returns:
        the hex digest, or None when the file is missing or unreadable (never skip on doubt).

    """
    try:
        return hashlib.sha256((project / STATE_RELATIVE).read_bytes()).hexdigest()
    except OSError:
        return None


def state_digest_path(session_id: str) -> Path | None:
    """Locate the per-session file holding the queue digest of the last successful run.

    Returns:
        the path beside the emission digest (a dot cannot occur in a session id), or None.

    """
    path = digest_path(session_id)
    return None if path is None else path.with_name(path.name + ".state")


def state_unchanged(session_id: str, current: str) -> bool:
    """Say whether the queue file is byte-identical to the one the last successful run saw.

    Returns:
        True only when a stored digest is readable and equals `current`.

    """
    path = state_digest_path(session_id)
    if path is None:
        return False
    try:
        return path.read_text(encoding="utf-8") == current
    except OSError:
        return False


def record_state(session_id: str, current: str) -> None:
    """Record the queue digest of a successful run; an unwritable directory records nothing."""
    path = state_digest_path(session_id)
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(current, encoding="utf-8")
    except OSError:
        return


def main(timeout: float = READER_TIMEOUT) -> int:
    """Run the hook: context on stdout when there is something to say, always exit 0.

    Returns:
        0 always; a context hook decides through its payload, never through its status.

    """
    payload = read_payload()
    event = text_of(payload.get("hook_event_name"))
    if event not in EVENTS:
        return 0
    session = text_of(payload.get("session_id"))
    project = project_dir()
    current = state_digest(project)
    if event == "UserPromptSubmit" and current is not None and state_unchanged(session, current):
        return 0
    text, failed = build_context(project, timeout)
    if current is not None and not failed:
        record_state(session, current)
    if not text:
        return 0
    if unchanged_since_last(event, session, text):
        return 0
    if failed:
        sys.stderr.write(text + "\n")
    out: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": text}
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""SessionStart and UserPromptSubmit: surface the repo's unclaimed inbound peer asks as context.

⚑ THE INTERACTIVE HALF OF mtools:W577. `mikemol-paths-forward --inbound` lists the peer cards that
wait on this repo with no local waypoint claiming them, and its payload form already reaches loop
ticks. A session that is not running a loop learned of an ask only when a peer nudged it. This hook
runs that reader and hands the rows to the model as ADDITIONAL CONTEXT.

⚑ IT NEVER REFUSES AND HAS NO STOP BEHAVIOUR, ON PURPOSE. A Stop block on an unanswered row would
trap a session that cannot satisfy it: the ask may not be theirs, and declining is a letter, not a
queue state a hook can read. So the exit status is always 0 and the only output is context.

⚑ THE CONTRACT USED (Claude Code hooks documentation; no sibling in this distribution injects
context, so this is the first): for SessionStart and UserPromptSubmit, exit 0 with
`{"hookSpecificOutput": {"hookEventName": <event>, "additionalContext": <text>}}` on stdout adds
the text to the model's context. A stderr line at exit 0 reaches the user's transcript and not the
model, so a failure is stated in the context text AND on stderr.

⚑ A TOOL THAT CANNOT BE RUN IS SAID, NEVER READ AS 'NOTHING TO REPORT'. An absent reader, a
non-zero exit and a timeout each produce one notice that does not claim there are no asks. A repo
with no queue file has no census to run and stays silent; so does a reader that prints nothing.

⚑ THE FLOOD GUARD IS ONE DIGEST FILE PER SESSION under the temp directory. SessionStart always
emits what it finds; UserPromptSubmit emits only when the text differs from the last emission, so a
failure notice is also said once. The cost is one reader spawn per prompt, bounded by the timeout,
and one small file write per change. A payload without a usable session id emits every time.
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

READER = "mikemol-paths-forward"
STATE_RELATIVE = Path(".claude") / "paths-forward.json"
EVENTS = ("SessionStart", "UserPromptSubmit")
READER_TIMEOUT = 20.0
PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"
_SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
_HEADING = "inbound: peer ask(s) wait on this repo with no claiming waypoint:"
_FOOTER = (
    "to claim a row, run its --add command; to decline, send the peer a letter "
    "(a decline is not a queue state)."
)


def project_dir() -> Path:
    """Return the project the hook serves: CLAUDE_PROJECT_DIR, else the working directory.

    Returns:
        the project directory.

    """
    return Path(os.environ.get(PROJECT_DIR_ENV) or Path.cwd()).absolute()


def find_reader(project: Path) -> str | None:
    """Find the reader: the project venv first, then PATH.

    Returns:
        the reader path, or None when neither holds one.

    """
    local = project / ".venv" / "bin" / READER
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    return shutil.which(READER)


def reader_argv(reader: str, state: Path) -> list[str]:
    """Spell the reader's argv: module constants plus the state path as one word.

    Returns:
        the argv, never passed through a shell.

    """
    return [reader, "--state", str(state), "--inbound"]


def run_reader(reader: str, state: Path, timeout: float) -> tuple[str | None, str]:
    """Run the reader once, bounded.

    Returns:
        (stdout, "") on exit 0; (None, why) when it could not run, timed out or exited non-zero.

    """
    try:
        done = subprocess.run(
            reader_argv(reader, state),
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
        return None, f"exited {done.returncode}" + (f": {detail[0]}" if detail else "")
    return done.stdout, ""


def context_for(rows: str) -> str:
    """Wrap the reader's rows in the stable heading and the one claim-or-decline line.

    Returns:
        the context text, or the empty string when the reader printed no row.

    """
    lines = [line for line in rows.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join([_HEADING, *lines, _FOOTER])


def failure_notice(why: str) -> str:
    """State that the census could not run, without claiming there are no asks.

    Returns:
        the notice text.

    """
    return (
        f"inbound: the census of peer asks COULD NOT RUN ({why}). This is not a statement that "
        f"no peer ask waits on this repo; run `{READER} --state "
        f"{STATE_RELATIVE} --inbound` by hand."
    )


def build_context(project: Path, timeout: float) -> tuple[str, bool]:
    """Decide what the session should be told for this project.

    Returns:
        (text, failed): empty text when there is nothing to say; failed marks a notice.

    """
    state = project / STATE_RELATIVE
    if not state.is_file():
        return "", False
    reader = find_reader(project)
    if reader is None:
        return failure_notice(f"{READER} is neither in .venv/bin nor on PATH"), True
    out, why = run_reader(reader, state, timeout)
    if out is None:
        return failure_notice(why), True
    return context_for(out), False


def digest_path(session_id: str) -> Path | None:
    """Locate the per-session digest file, or None for an unusable session id.

    Returns:
        the path under the temp directory.

    """
    if not _SESSION_ID.fullmatch(session_id):
        return None
    return Path(tempfile.gettempdir()) / "mikemol-inbound-asks" / session_id


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


def main(timeout: float = READER_TIMEOUT) -> int:
    """Run the hook: context on stdout when there is something to say, always exit 0.

    Returns:
        0 always; a context hook decides through its payload, never through its status.

    """
    payload = read_payload()
    event = text_of(payload.get("hook_event_name"))
    if event not in EVENTS:
        return 0
    text, failed = build_context(project_dir(), timeout)
    if not text:
        return 0
    if unchanged_since_last(event, text_of(payload.get("session_id")), text):
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

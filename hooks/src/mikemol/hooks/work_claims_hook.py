# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""SessionStart, UserPromptSubmit and SessionEnd: claim the touches of the card being worked (W994).

⚑ A WORKING CARD'S TOUCHES TAGS ARE CLAIMED BY THE SESSION (mtools:W912, W889). On each prompt the
hook reads this project's queue, takes `claim:label:touch:<repo>:<tag>` through the fence `claim`
verb for every tag of a `working` card, and releases the ones this session holds for tags no card
works any more. At SessionEnd it releases them all. The pure choices (which labels, which process,
what to take and drop) are `work_claims`; this module is the effectful edge.

⚑ THE CLAIM IS OWNED BY THE SESSION, NOT BY THIS COMMAND. The hook's own process exits in a second,
so the owner is the nearest `claude` ancestor, and the ledger's gc reaps the claim when the session
dies. SessionEnd's release is best effort inside the harness's short budget; a missed one costs
nothing, because the dead owner is reaped by the next reader.

⚑ ADVISORY, AND IT NEVER REFUSES. A claim another session holds is printed as one context line
naming the holder (`work_claims.advice`); the exit status is always 0 and there is no block. Two
sessions can have good reason to share a tag, and the commit claim is the only true mutex. This file
must not spell the arming variable the blocking hooks read.

⚑ A TOOL THAT CANNOT RUN CLAIMS NOTHING AND SAYS SO. No `mikemol-membudget` in the project's fence
venv, or no `claude` ancestor, yields one notice when there was something to claim, never silence
that reads as 'claimed'. The flood guard is one digest per session: a line repeats only when it
changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import work_claims
from mikemol.hooks.payload import as_record, text_of

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type Runner = Callable[[Sequence[str], float], tuple[int, str]]
type StatReader = Callable[[int], str | None]

MEMBUDGET = Path("fence") / ".venv" / "bin" / "mikemol-membudget"
QUEUE = Path(".claude") / "paths-forward.json"
PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"
EVENTS = ("SessionStart", "UserPromptSubmit", "SessionEnd")
PROMPT_TIMEOUT_S = 5.0
END_TIMEOUT_S = 1.0
EXIT_REFUSED = 3
_SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
_NOT_STARTED = 127
_TIMED_OUT = 124


def run_both(argv: Sequence[str], timeout: float) -> tuple[int, str]:
    """Run a command with stderr folded into stdout, bounded.

    Returns:
        (exit code, combined output); 127 when it could not start and 124 when it timed out.

    """
    try:
        done = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return _TIMED_OUT, ""
    except OSError:
        return _NOT_STARTED, ""
    return done.returncode, done.stdout + done.stderr


def read_stat(pid: int) -> str | None:
    """Read `/proc/<pid>/stat`.

    Returns:
        the line, or None when the process is gone or unreadable.

    """
    try:
        return Path("/proc", str(pid), "stat").read_text(encoding="utf-8")
    except OSError:
        return None


def comm_in(stat: str) -> str | None:
    """Read the command name from a stat line: what lies between its first `(` and last `)`.

    Returns:
        the name, or None when the line has no parenthesised field.

    """
    first, last = stat.find("("), stat.rfind(")")
    return stat[first + 1 : last] if 0 <= first < last else None


def queue_of(project: Path) -> object:
    """Read the project's queue file.

    Returns:
        the parsed JSON, or None when it is missing or not JSON (so nothing is claimed).

    """
    try:
        loaded: object = json.loads((project / QUEUE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded


def claim_lines(
    project: Path, event: str, run: Runner, stat_of: StatReader, hook_pid: int
) -> list[str]:
    """Take, release and report this session's claims for the project's working cards.

    ⚑ AT SessionEnd NOTHING IS WANTED, so every claim this session holds is released.

    Returns:
        the advisory lines: one per claim another session holds, one notice when a wanted claim
        could not be attempted. Empty when there was nothing to say.

    """
    want = [] if event == "SessionEnd" else work_claims.wanted(queue_of(project), project.name)
    tool = project / MEMBUDGET
    if not tool.is_file() or not os.access(tool, os.X_OK):
        return ["work claim: not taken (the fence membudget venv is not built)"] if want else []
    session = work_claims.session_pid(
        hook_pid,
        lambda pid: comm_in(stat_of(pid) or ""),
        lambda pid: work_claims.parent_of(stat_of(pid) or ""),
    )
    owner = work_claims.owner_string(session, stat_of(session) or "") if session else None
    if session is None or owner is None:
        return ["work claim: not taken (no claude session process above this hook)"] if want else []
    timeout = END_TIMEOUT_S if event == "SessionEnd" else PROMPT_TIMEOUT_S
    held = work_claims.claims_of(run([str(tool), "claims"], timeout)[1])
    todo = work_claims.plan(want, held, owner)
    pid = str(session)
    for label in todo.release:
        run([str(tool), "release", label, "--owner-pid", pid], timeout)
    lines: list[str] = []
    for label in todo.take:
        code, said = run([str(tool), "claim", label, "--owner-pid", pid], timeout)
        if code == EXIT_REFUSED:
            lines.append(work_claims.advice(label, said))
    return lines


def digest_path(session_id: str) -> Path | None:
    """Locate the per-session digest of the last emitted lines.

    Returns:
        the path under the temp directory, or None for an unusable session id.

    """
    if not _SESSION_ID.fullmatch(session_id):
        return None
    return Path(tempfile.gettempdir()) / "mikemol-work-claims" / session_id


def unchanged_since_last(session_id: str, text: str) -> bool:
    """Say whether these lines repeat the last emission, and record them.

    Returns:
        True when the stored digest equals this text's.

    """
    path = digest_path(session_id)
    if path is None:
        return False
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    try:
        if path.read_text(encoding="utf-8") == digest:
            return True
    except OSError:
        pass
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(digest, encoding="utf-8")
    except OSError:
        return False
    return False


def main() -> int:
    """Run the hook: advisory context on stdout when a claim is held elsewhere, always exit 0.

    Returns:
        0 always; a context hook decides through its payload, never through its status.

    """
    try:
        raw: object = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    payload = as_record(raw)
    event = text_of(payload.get("hook_event_name"))
    if event not in EVENTS:
        return 0
    project = Path(os.environ.get(PROJECT_DIR_ENV) or Path.cwd()).absolute()
    lines = claim_lines(project, event, run_both, read_stat, os.getpid())
    if event == "SessionEnd" or not lines:
        return 0
    text = "\n".join(lines)
    if unchanged_since_last(text_of(payload.get("session_id")), text):
        return 0
    out: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": text}
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

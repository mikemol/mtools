# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""PostToolUseFailure(Bash): put a failed build's reason into context, from BuildBuddy (W829).

Every gate is a bazel build and bazel prints `Streaming build results to: <url>/invocation/<id>`,
so a failed command that ran one carries the id of the log that holds WHY it failed. Reading that
log is `mikemol-buildlog <id> --failures` (W827): the failing tests' output and the ERROR and FAILED
lines, a handful of lines out of thousands. This runs it for the model, so a build failure arrives
with its cause instead of with a request to go and find it (operator, 2026-10-06).

⚑ EXIT 2 CARRIES THE REPORT: for this event the harness feeds stderr back to the model, which is
the channel the operator named. The report is bounded (`MAX_CHARS`) and ends naming the full
command, so a long failure is never silently clipped.

⚑ FOREGROUND FAILURES ONLY, AND SAID SO: a command the harness moved to the background reports its
failure later as a task notification, which is not a failed tool call and never reaches this hook.
Those are read by id with the same command by hand, and the precommits ask for the cause themselves
through `report_main` (`mikemol-build-failure`), on the bazel line that failed.

⚑ NOTHING TO SAY IS SILENCE, A GAP IS STATED: a failure with no invocation id exits 0 untouched. A
failure WITH an id whose log could not be read still exits 2, naming the id and the command to run,
so an unreadable log is never mistaken for a failure with no cause.

CONSUMED BY: the `mikemol-hook-build-failure` and `mikemol-build-failure` console scripts.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import tool_path
from mikemol.hooks.payload import as_record, text_of

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import TextIO

BUILDLOG_ENV = "BUILDLOG_BIN"
BUILDLOG = "mikemol-buildlog"
FAILURE_EVENT_TOOL = "Bash"
EXIT_FEEDBACK = 2
EXIT_USAGE = 2
MAX_CHARS = 6_000
READ_TIMEOUT_S = 45
FALLBACK_TAIL = "40"
STDIN_FD = 0
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
INVOCATION = re.compile(rf"invocation/({_UUID})")


def invocation_ids(text: str) -> list[str]:
    """Return the BuildBuddy invocation ids named in `text`, each once, in order of appearance.

    Returns:
        the ids; empty when the text names none.

    """
    seen: list[str] = []
    for found in INVOCATION.finditer(text):
        found_id = found.string[found.start(1) : found.end(1)]
        if found_id not in seen:
            seen.append(found_id)
    return seen


def run_reader(argv: Sequence[str]) -> str | None:
    """Run the log reader and return its stdout.

    Returns:
        stdout when it exited 0, None when it could not run, timed out or exited non-zero.

    """
    try:
        done = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            check=False,
            timeout=READ_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def bounded(text: str, command: str) -> str:
    """Cap the report at MAX_CHARS, saying how to read the rest.

    Returns:
        `text` when it fits, else its head and a line naming `command`.

    """
    if len(text) <= MAX_CHARS:
        return text
    return f"{text[:MAX_CHARS]}\n... (truncated; the whole log: {command} --all)\n"


def report_for(
    text: str,
    root: Path,
    env: Mapping[str, str],
    run: Callable[[Sequence[str]], str | None],
) -> str | None:
    """Build the failure report for a failed command's output, or None when it ran no build.

    ⚑ THE LAST ID IS THE FAILED BUILD: a gate prints one per bazel run, in order, and the run that
    failed is the one it stopped at. The failures view is tried first; a log with none in that
    shape falls back to its last lines, so a failure is never reported as an empty section.

    Returns:
        the report text, or None when `text` names no invocation.

    """
    ids = invocation_ids(text)
    if not ids:
        return None
    invoked = ids[-1]
    command = f"{BUILDLOG} {invoked}"
    reader = tool_path.find(BUILDLOG, BUILDLOG_ENV, root, env)
    if reader is None:
        return f"build-failure: invocation {invoked} failed; {BUILDLOG} not found. Run: {command}\n"
    picked = run([str(reader), invoked, "--failures"])
    if picked is None:
        return f"build-failure: invocation {invoked}'s log could not be read. Run: {command}\n"
    if not picked.strip():
        picked = run([str(reader), invoked, "--tail", FALLBACK_TAIL]) or ""
    head = f"build-failure: invocation {invoked} (from BuildBuddy, {command} --failures)\n"
    return head + bounded(picked, command)


def run(
    record: Mapping[str, object],
    env: Mapping[str, str],
    reader: Callable[[Sequence[str]], str | None],
    err: TextIO,
) -> int:
    """Feed a failed Bash command's build log back to the model, if it ran a build.

    Returns:
        EXIT_FEEDBACK with the report on `err`, or 0 when there is nothing to add.

    """
    if text_of(record.get("tool_name")) != FAILURE_EVENT_TOOL:
        return 0
    text = text_of(record.get("error")) or text_of(record.get("tool_response"))
    root = Path(env.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    report = report_for(text, root, env, reader)
    if report is None:
        return 0
    err.write(report)
    return EXIT_FEEDBACK


def _stdin_text() -> str:
    """Read all of stdin as text, once, from its file descriptor.

    Returns:
        what was sent, undecodable bytes replaced.

    """
    with open(STDIN_FD, encoding="utf-8", errors="replace", closefd=False) as stream:
        return stream.read()


def report_main(
    argv: Sequence[str] | None = None,
    read_stdin: Callable[[], str] = _stdin_text,
) -> int:
    """Read a failed build's raw output on stdin and print its cause: the precommit's one call.

    ⚑ THE GATE'S OWN FAILURES NEVER REACH THE FAILURE HOOK (operator, 2026-10-06): a commit runs
    as a background task and fails later as a notification, not as a failed tool call. So the
    precommit asks for the cause itself, on each bazel line that can fail:
    `bazel ... || { mikemol-build-failure <log; false; }`. (Not `cmd || report && false`, which
    shell reads as `(cmd || report) && false` and so fails a passing command.)

    Returns:
        0 with the report on stdout, 1 when the output named no build (nothing printed), 2 for any
        argument (this takes none).

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        sys.stderr.write("usage: mikemol-build-failure < build-output   (no arguments)\n")
        return EXIT_USAGE
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    report = report_for(read_stdin(), root, dict(os.environ), run_reader)
    if report is None:
        return 1
    sys.stdout.write(report)
    return 0


def main() -> int:
    """Read the PostToolUseFailure payload on stdin and report the failed build's cause.

    An unreadable payload says nothing: a context hook has nothing to refuse.

    Returns:
        the exit code from `run`, or 0.

    """
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        return 0
    return run(as_record(raw), dict(os.environ), run_reader, sys.stderr)

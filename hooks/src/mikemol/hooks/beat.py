# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-hook-beat`: every tool call leaves the session heartbeat (W1475, github-8f 2026-10-17).

The idle watchdog (`watchdog.py`) measures how long a session has been quiet, and until now only the
writer, `mikemol-commit` and `mikemol-scratch` beat, so a long Bash build, a read or an edit left no
beat and el-openglo's session was woken twice while it worked. The operator's rule is that USING THE
TOOLING IS THE HEARTBEAT. The harness runs a hook around every tool call, so a PostToolUse hook that
writes the stamp is that rule, literally, for every tool and with no transcript reader.

⚑ A BEAT IS THE SESSION'S OWN ACTION. A hook runs because the session called a tool, so it cannot be
fooled by the background-task notifications and peer messages the harness writes into a transcript
while the session is idle, which is why this is the primary signal and a transcript check only a
second opinion before firing.

⚑ IT NEVER BLOCKS. Exit 0 whatever the payload, the project or the file system is: a heartbeat that
cannot be written is a missed sample (`heartbeat.try_beat`), and a hook that refused a tool call
over it would stop the work it exists to witness.

⚑ IT SPEAKS IN ONE CASE (W1557, github-8f 2026-10-18): the exit-8 rule lived in a prompt, and
sessions let their watchdog lapse through a long gate wait while ready cards waited. Prompt text did
not hold, so the next tool call tells the session. When no live watchdog holds this repo's pid file
(`watchdog.running`) and the writer counts ready cards, the hook returns `additionalContext` naming
the restart command and the kinds of work to do first. It asks at most once per `NOTICE_EVERY_S`,
so a session busy elsewhere is not nagged on every call, and a quiet repo costs one file read.

⚑ THE PROJECT IS THE ONE THE HARNESS NAMES: `CLAUDE_PROJECT_DIR`, then the payload's `cwd`. A
project whose `.git` is not a directory (a worktree) is skipped, as the writer's beat is.

CONSUMED BY: the `PostToolUse` and `PostToolUseFailure` entries of a repo's `.claude/settings.json`.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TextIO, cast

from mikemol.hooks import heartbeat, hook_argv, watchdog

PROG = "mikemol-hook-beat"
PROJECT_ENV = "CLAUDE_PROJECT_DIR"
UNKNOWN_TOOL = "tool"
PRE_EVENT = "PreToolUse"
NOTICE_EVERY_S = 120
NOTICE_MARK = "watchdog.notice"
DOWN_MARK = "watchdog.down"
HOOK_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})
HOOK_DIRS = (("hooks", "src"), ("hooks", "bin"))
ENTRY_MODULE = "mikemol.hooks.entry"
_NS_PER_S = 1_000_000_000
_NOT_FOUND = 127
_WRITER = "mikemol-paths-forward"
_WORK = (
    "Then do work: prepare the next stack, triage, atomize coarse cards, add manifests, or "
    "warrant rulings."
)


def run_probe(argv: Sequence[str]) -> tuple[int, str]:
    """Run a command and report its exit code and what it wrote to stderr (W1584).

    Returns:
        the exit code and stderr text; 127 and the error text when the program cannot start.

    """
    try:
        done = subprocess.run(
            list(argv), capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL
        )
    except OSError as err:
        return _NOT_FOUND, str(err)
    return done.returncode, done.stderr


IMPORT_PROBE: Callable[[Sequence[str]], tuple[int, str]] = run_probe
"""The seam for the import check: a test replaces it so no interpreter is started."""


def _field(raw: object, key: str) -> str | None:
    # A non-empty string field of the payload, or None for anything else.
    if not isinstance(raw, dict):
        return None
    value = cast("dict[str, object]", raw).get(key)
    return value if isinstance(value, str) and value else None


def tool_of(raw: object) -> str:
    """Name the tool a PostToolUse payload reports.

    Returns:
        the payload's `tool_name`, or a generic word when it has none.

    """
    return _field(raw, "tool_name") or UNKNOWN_TOOL


def project_of(raw: object, env: Mapping[str, str]) -> Path | None:
    """Find the project directory the beat belongs to.

    Returns:
        `CLAUDE_PROJECT_DIR` when set, else the payload's `cwd`, else None.

    """
    named = env.get(PROJECT_ENV) or _field(raw, "cwd")
    return Path(named) if named else None


def writer_of(project: Path) -> str | None:
    """Find the paths-forward writer this repo uses: its own venv, mtools' dist, then PATH.

    Returns:
        the writer's path, or None when none exists.

    """
    for candidate in (
        project / ".venv" / "bin" / _WRITER,
        project / "pathsforward" / ".venv" / "bin" / _WRITER,
    ):
        if candidate.is_file():
            return str(candidate)
    return shutil.which(_WRITER)


def _due(git_dir: Path, now_ns: int, name: str = NOTICE_MARK) -> bool:
    # True when the last stamp named `name` is older than the interval, and stamps this one.
    mark = git_dir / "mtools" / name
    try:
        if now_ns - mark.stat().st_mtime_ns < NOTICE_EVERY_S * _NS_PER_S:
            return False
        mark.touch()
    except FileNotFoundError:
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.touch()
    except OSError:
        return False
    return True


def restart_command(writer: str, state: Path) -> str:
    """Spell the command that starts this repo's watchdog in the background.

    Returns:
        the same command the writer's `--watchdog-line` prints: the hooks venv's interpreter under
        the mtools checkout (this interpreter when that is absent), the module, the state file and
        the writer.

    """
    venv = Path.home() / "github" / "mtools" / "hooks" / ".venv" / "bin" / "python"
    python = str(venv) if venv.is_file() else sys.executable
    return f"{python} -m mikemol.hooks.watchdog --state {state} --writer {writer}"


def notice(project: Path, now_ns: int) -> str | None:
    """Say what the session should do when its watchdog is gone and cards are waiting.

    Returns:
        the text for `additionalContext`, or None when a watchdog lives, nothing is ready, the
        notice was given lately or the writer cannot answer.

    """
    git_dir = project / ".git"
    state = project / ".claude" / "paths-forward.json"
    writer = writer_of(project)
    if writer is None or not state.is_file() or watchdog.running(git_dir):
        return None
    if not _due(git_dir, now_ns):
        return None
    waiting = watchdog.ready_from(writer, state)
    if not waiting:
        return None
    head = f"No live watchdog holds this repo's pid file and {waiting} cards are ready."
    said = f"{head} Start it in the background: {restart_command(writer, state)}. {_WORK}"
    # ⚑ THE NOTICE CARRIES ITS OWN NEXT ACTION (W1565, as the exit line does, W1591): a stackable
    # card and a leaf to atomize, from nemik-stackable, when it is there to ask.
    hint = watchdog.cached_hint(git_dir)
    return f"{said} {hint}" if hint else said


def mark_down(
    project: Path,
    env: Mapping[str, str],
    now_ns: int,
    spawn: Callable[[Sequence[str]], None],
) -> bool:
    """Tell the store this repo has no live watchdog, at most once per `NOTICE_EVERY_S` (W1558).

    ⚑ THE ZERO IS WHAT GIVES THE ALERT A SERIES (github-8f, 2026-10-18): the watchdog sends
    `mikemol.watchdog.armed{repo}=1` while it runs, so a repo whose watchdog never started or died
    sends nothing, and a freshness rule over silence cannot be told from a repo that is not in the
    fleet. The hook runs on every tool call of a live session, so it is the one place that knows
    the session is active and unwatched.

    Returns:
        True when a sample was sent; False when a watchdog lives or the last one was lately.

    """
    git_dir = project / ".git"
    if watchdog.running(git_dir) or not _due(git_dir, now_ns, DOWN_MARK):
        return False
    watchdog.armed_publisher(env, project.name, spawn, watchdog.ARMED_DOWN)()
    return True


def _edited_path(raw: object) -> str | None:
    # The file path of an Edit or Write payload, or None.
    inner = cast("dict[str, object]", raw).get("tool_input") if isinstance(raw, dict) else None
    return _field(inner, "file_path")


def edited_hook(raw: object, project: Path) -> str | None:
    """Name the hook file an Edit or Write touched, relative to the project.

    Returns:
        the path when the tool is an edit and the file sits under `hooks/src` or `hooks/bin`; None
        for any other tool or file.

    """
    path = _edited_path(raw)
    if tool_of(raw) not in HOOK_TOOLS or path is None:
        return None
    try:
        relative = Path(path).relative_to(project)
    except ValueError:
        return None
    return str(relative) if relative.parts[:2] in HOOK_DIRS else None


def import_failure(project: Path) -> str | None:
    """Import the hook entry module with the built venv's interpreter, as a launcher does.

    ⚑ THE SAME IMPORT THE HARNESS'S LAUNCHERS MAKE (W1584, github-8f 2026-10-18): the Bash guard
    died with `ImportError` because a module it imports was not in the built venv, and a guard that
    crashes fails OPEN. `mikemol.hooks.entry` imports every hook module, so one import says whether
    any hook can start. It uses the built venv (`bazel-bin/hooks/.venv`, resolved as the launchers
    resolve it), runs without writing bytecode, and starts nothing else.

    Returns:
        the last stderr line when the import fails; None when it works or no venv is built.

    """
    python = (project / "bazel-bin" / "hooks" / ".venv").resolve() / "bin" / "python3"
    if not python.is_file():
        return None
    code, err = IMPORT_PROBE([str(python), "-B", "-c", f"import {ENTRY_MODULE}"])
    if code == 0:
        return None
    lines = [line for line in err.splitlines() if line.strip()]
    return lines[-1] if lines else f"exit {code}"


def hook_break(raw: object, project: Path) -> str | None:
    """Say so when an edit under `hooks/` leaves the hooks unable to import.

    Returns:
        the message naming the file and the error, or None when the edit was elsewhere or the hooks
        still import.

    """
    touched = edited_hook(raw, project)
    failure = import_failure(project) if touched is not None else None
    if touched is None or failure is None:
        return None
    return (
        f"A hook module you edited does not import ({touched}): {failure}. Every hook that loads "
        "it fails, and a guard hook that crashes fails OPEN, so its protection is off until this "
        f"is fixed. Fix it, or restore the file now: git checkout HEAD -- {touched}"
    )


def run(
    stdin: TextIO,
    env: Mapping[str, str],
    now_ns: Callable[[], int] = time.time_ns,
    out: TextIO | None = None,
    spawn: Callable[[Sequence[str]], None] | None = None,
) -> int:
    """Leave one beat for the tool call the payload reports, and speak if the watchdog is gone.

    `spawn` is the sender of the zero sample; with none given nothing is sent, so a test that
    calls `run` cannot reach the real store. `main` passes the detached spawner.

    Returns:
        0 always.

    """
    try:
        raw: object = json.load(stdin)
    except ValueError:
        raw = None
    project = project_of(raw, env)
    if project is not None and (project / ".git").is_dir():
        # ⚑ A PRE-CALL EVENT STAMPS THE START AND DOES NOT BEAT (github-8f, 2026-10-18, W1617): a
        # session sitting inside one foreground call is a stall, so the call's start must not look
        # like activity. The stamp only lets the watchdog's exit say the silence was in a call.
        if _field(raw, "hook_event_name") == PRE_EVENT:
            heartbeat.mark_call(project / ".git", tool_of(raw), now_ns())
            return 0
        heartbeat.clear_call(project / ".git")
        heartbeat.try_beat(project / ".git", f"hook:{tool_of(raw)}", now_ns())
        if spawn is not None:
            mark_down(project, env, now_ns(), spawn)
        said = " ".join(m for m in (notice(project, now_ns()), hook_break(raw, project)) if m)
        if said:
            event: dict[str, str] = {"hookEventName": "PostToolUse", "additionalContext": said}
            body: dict[str, dict[str, str]] = {"hookSpecificOutput": event}
            (out or sys.stdout).write(json.dumps(body) + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the hook.

    Returns:
        0 always, or the argv contract's refusal for an argument.

    """
    args = list(sys.argv if argv is None else argv)
    if hook_argv.mode(PROG, args) is not None:
        return hook_argv.EXIT_REFUSED
    return run(sys.stdin, os.environ, spawn=watchdog.DETACHED)


if __name__ == "__main__":
    raise SystemExit(main())

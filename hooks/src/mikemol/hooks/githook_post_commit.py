# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-githook-post-commit`: the shared git post-commit, shipped as a package.

Handed over by substrate (inbox/2026-09-23-substrate-githooks-handover.md); the shell version it
replaces, substrate's `.githooks/post-commit`, is the specification. A repo depends on
mikemol-hooks and its `.githooks/post-commit` is one line:

    exec <venv>/bin/mikemol-githook-post-commit

⚑ THE MARKER. What substrate's `pre-push.local` checks is not a file: it is the text
`post-commit advisory (auto-captured)` in the tip's commit message, written here by amending the
commit just made. el-openglo's own post-commit writes the same marker, so the two agree.

What it does, in order:

1. Guard: if `_POST_COMMIT_AMENDING` is set, this is the hook re-fired by its own amend; do nothing.
2. THE EXTENSION POINT, the post-commit twin of pre-push.local: if
   `<toplevel>/.githooks/post-commit.local` is executable, run it and take its stdout as the
   repo's advisory body (substrate's grounding and tautology reports, el-openglo's partial-recovery
   roster). Its stderr passes through. A missing or non-executable one is not an error.
3. Print the advisory (a header line plus that body) to stdout.
4. Skip the amend while a rebase, merge, cherry-pick or revert is in flight (it would rewrite the
   wrong commit), and when the message already carries the marker (idempotent across `--amend`).
5. Otherwise amend the commit, `--no-verify` and with the guard set, so the message gains the
   marker and the advisory beneath it.

⚑ A FAILURE IS REPORTED, NOT SWALLOWED. The shell version ended its amend in `|| true`. A failed
amend leaves no marker, and substrate's pre-push then refuses the tip with a message about a race;
the cause was lost. Here the failed amend, a git that cannot answer, and a run outside a
repository each write a line to stderr and exit 1. Git ignores a post-commit exit status, so the
commit is never harmed; the report is for the person reading the terminal.

⚑ IT NEVER PUSHES. A repo that auto-pushes after a commit (mtools' own `.githooks/post-commit`,
el-openglo's) does so in its own stub, after this script returns: that is repo policy, not part of
the shared hook.

⚑ NOT named `mikemol-hook-…`: those are Claude-harness hooks. This one is wired by git.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = "post-commit advisory (auto-captured)"
HEADER = "── post-commit advisory (non-blocking; gates ran pre-commit) ──"
GUARD = "_POST_COMMIT_AMENDING"
_IN_FLIGHT = ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD")
_LOCAL = Path(".githooks") / "post-commit.local"


class GitUnavailableError(RuntimeError):
    """No `git` on PATH: the hook cannot do its work, and says so rather than skipping."""


def run_git(
    *args: str, stdin: str | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run git in the current directory and hand back the result, whatever its status.

    Returns:
        the completed process, with text stdout and stderr captured.

    Raises:
        GitUnavailableError: when no git is on PATH.

    """
    git = shutil.which("git")
    if git is None:
        msg = "post-commit: no git on PATH — cannot write the advisory marker"
        raise GitUnavailableError(msg)
    return subprocess.run(
        [git, *args], input=stdin, capture_output=True, text=True, check=False, env=env
    )


def in_flight(git_dir: Path) -> str | None:
    """Name the first in-flight operation marker present in `git_dir`.

    Returns:
        the marker's name, or None when no operation is in flight.

    """
    return next((name for name in _IN_FLIGHT if (git_dir / name).exists()), None)


def advisory(toplevel: Path) -> str:
    """Build the advisory: the header, then the repo's post-commit.local stdout if it has one.

    A local hook that exits non-zero keeps whatever it printed, and the advisory says it failed:
    its failure is part of what the person reads, not something to hide.

    Returns:
        the advisory text, with no trailing newline.

    """
    lines = [HEADER]
    local = toplevel / _LOCAL
    if local.is_file() and os.access(local, os.X_OK):
        done = subprocess.run(
            [str(local)], capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL
        )
        sys.stderr.write(done.stderr)
        body = done.stdout.rstrip("\n")
        if body:
            lines.append(body)
        if done.returncode != 0:
            lines.append(f"post-commit.local FAILED (exit {done.returncode})")
    return "\n".join(lines)


def folded(message: str, text: str) -> str:
    """Append the marker and the indented advisory to a commit message.

    Returns:
        the message with the marker block beneath it.

    """
    indented = "\n".join(f"    {line}" for line in text.splitlines())
    return f"{message.rstrip()}\n\n{MARKER}:\n{indented}\n"


def _amend(text: str) -> int:
    """Amend the tip to carry the marker and the advisory, unless it must not or need not.

    Returns:
        0 when the marker is in the tip or the amend was deliberately skipped; 1 when git refused
        the amend, with its reason on stderr.

    """
    git_dir = Path(run_git("rev-parse", "--git-dir").stdout.strip()).resolve()
    message = run_git("log", "-1", "--format=%B").stdout
    if in_flight(git_dir) is not None or MARKER in message:
        return 0
    amended = run_git(
        "commit",
        "--amend",
        "--no-verify",
        "--allow-empty",
        "-F",
        "-",
        stdin=folded(message, text),
        env={**os.environ, GUARD: "1"},
    )
    if amended.returncode != 0:
        sys.stderr.write(
            f"post-commit: amend FAILED (exit {amended.returncode}) — the commit has no marker, "
            f"and pre-push will refuse it.\n{amended.stderr}"
        )
    return 1 if amended.returncode != 0 else 0


def _run() -> int:
    """Find the repository, print the advisory, and fold it into the tip.

    Returns:
        the exit status; 1 outside a repository, nothing written.

    """
    top = run_git("rev-parse", "--show-toplevel")
    if top.returncode != 0:
        sys.stderr.write(f"post-commit: not in a git repository: {top.stderr.strip()}\n")
        return 1
    text = advisory(Path(top.stdout.strip()))
    sys.stdout.write(text + "\n")
    return _amend(text)


def main() -> int:
    """Print the advisory and fold it into the commit just made.

    Returns:
        0 when the advisory is printed and the marker is in the tip (or was deliberately skipped);
        1 when the work could not be done, with the reason on stderr.

    """
    if os.environ.get(GUARD):
        return 0
    try:
        return _run()
    except GitUnavailableError as error:
        sys.stderr.write(f"{error}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

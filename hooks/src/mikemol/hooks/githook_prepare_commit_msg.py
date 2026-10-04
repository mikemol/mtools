# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-githook-prepare-commit-msg`: the shared git prepare-commit-msg, shipped as a package.

Handed over by substrate (inbox/archive/2026-09-23-substrate-githooks-handover.md); the shell
version it replaces, substrate's `.githooks/prepare-commit-msg`, is the specification. A repo
depends on mikemol-hooks and its `.githooks/prepare-commit-msg` is one line, which must pass git's
arguments on:

    exec <venv>/bin/mikemol-githook-prepare-commit-msg "$@"

⚑ ARGV IS THE CONTRACT HERE, unlike the harness hooks (`mikemol-hook-*`, which refuse any
argument): git calls this hook as `prepare-commit-msg <message-file> [<source> [<sha>]]`, where
source is `message`, `template`, `merge`, `squash` or `commit`. Only the first two arguments are
read; a missing source is the same as an unrecognised one.

What it does, in order:

1. No message file argument: a usage error (see below).
2. Ask git for `--absolute-git-dir` and look for `<gitdir>/precommit-report.txt`, which the repo's
   pre-commit gate writes. No report is the normal no-op (a `--no-verify` commit, or an amend
   after the report was consumed): exit 0, the message file untouched.
3. Source `merge` or `squash`: delete the report and leave the generated message alone.
4. The message already carries `pre-commit gate report (auto-captured)` (a manual `--amend`):
   delete the report and append nothing.
5. Otherwise append a blank line, that marker line with a colon, and the report with its
   `[N/total]` build-progress lines and blank lines dropped and the rest indented four spaces, so
   it never collides with git's `#` comments. Then delete the report (one-shot).

⚑ A FAILURE IS REPORTED, NOT SWALLOWED. The shell version took no `set -e` ("a failure here would
ABORT the commit") and instead guarded every step with `2>/dev/null` or `|| true`. What that hid:

- `git rev-parse` failing (no git, not a repository) made the report path `/precommit-report.txt`,
  which does not exist, so the hook exited 0 having done nothing and said nothing.
- `grep` on an unreadable message file read as "marker absent".
- the `>>` append failing (unwritable or missing-directory message file) was silent, and the
  `rm -f` after it ran anyway: THE REPORT WAS CONSUMED WITHOUT BEING FOLDED IN, lost for good.
- reading the report failing left an empty block, or none, with no word.

Here each of those writes a line to stderr and exits 1, and on a failed append the report is
KEPT, so the next commit folds it in. Git aborts a commit when this hook exits non-zero: that is
the cost of not hiding the cause, and the message names what to fix.

⚑ NOT named `mikemol-hook-…`: those are Claude-harness hooks. This one is wired by git.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

MARKER = "pre-commit gate report (auto-captured)"
REPORT_NAME = "precommit-report.txt"
_SKIPPED_SOURCES = ("merge", "squash")
_PROGRESS = re.compile(r"^\[[0-9]+/[0-9]+\] ")
_BLANK = re.compile(r"^\s*$")


class GitUnavailableError(RuntimeError):
    """No `git` on PATH: the hook cannot do its work, and says so rather than skipping."""


class HookError(RuntimeError):
    """A step the shell version swallowed; the text is the line written to stderr."""


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git in the current directory and hand back the result, whatever its status.

    Returns:
        the completed process, with text stdout and stderr captured.

    Raises:
        GitUnavailableError: when no git is on PATH.

    """
    git = shutil.which("git")
    if git is None:
        msg = "prepare-commit-msg: no git on PATH — cannot find the pre-commit report"
        raise GitUnavailableError(msg)
    return subprocess.run([git, *args], capture_output=True, text=True, check=False)


def report_path() -> Path:
    """Locate `<absolute git dir>/precommit-report.txt` for the repository in the cwd.

    Returns:
        the path (the file may not exist).

    Raises:
        HookError: when git cannot name the git directory.

    """
    found = run_git("rev-parse", "--absolute-git-dir")
    if found.returncode != 0:
        msg = f"prepare-commit-msg: git cannot name the git dir: {found.stderr.strip()}"
        raise HookError(msg)
    return Path(found.stdout.strip()) / REPORT_NAME


def folded(report: str) -> str:
    """Render a report as the block appended to the message.

    The block opens with a blank line and the marker, then the report with `[N/total]` progress
    lines and blank lines dropped and each remaining line indented four spaces.

    Returns:
        the block, newline-terminated.

    """
    kept = [
        f"    {line}"
        for line in report.split("\n")
        if not _PROGRESS.match(line) and not _BLANK.match(line)
    ]
    return "\n".join(["", f"{MARKER}:", *kept]) + "\n"


def _consume(report: Path) -> None:
    """Delete the one-shot report.

    Raises:
        HookError: when it cannot be deleted.

    """
    try:
        report.unlink(missing_ok=True)
    except OSError as error:
        msg = f"prepare-commit-msg: cannot delete {report}: {error}"
        raise HookError(msg) from error


def _fold_into(message: Path, report: Path) -> None:
    """Append the folded report to the message file, and consume the report only on success.

    Raises:
        HookError: when the message or report cannot be read, or the message cannot be appended
            to; the report is then left in place.

    """
    try:
        existing = message.read_text(encoding="utf-8", errors="replace")
        body = report.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        msg = f"prepare-commit-msg: cannot read the message or the report: {error}"
        raise HookError(msg) from error
    if MARKER in existing:
        _consume(report)
        return
    try:
        with message.open("a", encoding="utf-8") as handle:
            handle.write(folded(body))
    except OSError as error:
        msg = (
            f"prepare-commit-msg: cannot append to {message}: {error} — "
            f"the report is KEPT at {report}, not folded in."
        )
        raise HookError(msg) from error
    _consume(report)


def prepare(message: Path, source: str) -> None:
    """Fold the pre-commit report into the message file, as the shell hook did.

    A step the shell version swallowed surfaces as HookError or GitUnavailableError from the
    helpers; `main` reports both.
    """
    report = report_path()
    if not report.is_file():
        return
    if source in _SKIPPED_SOURCES:
        _consume(report)
        return
    _fold_into(message, report)


def main(argv: Sequence[str] | None = None) -> int:
    """Run as git's prepare-commit-msg: `<message-file> [<source> [<sha>]]`.

    Returns:
        0 when the message was folded, or there was nothing to fold; 1 when the work could not be
        done (no message file argument, no git, an unreadable report, an unwritable message), with
        the reason on stderr.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or not args[0]:
        sys.stderr.write("prepare-commit-msg: usage: <message-file> [<source>]\n")
        return 1
    try:
        prepare(Path(args[0]), args[1] if len(args) > 1 else "")
    except (GitUnavailableError, HookError) as error:
        sys.stderr.write(f"{error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

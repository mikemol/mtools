# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-githook-pre-push`: the shared git pre-push, shipped as a package, not a linked file.

Handed over by substrate (inbox/2026-09-23-substrate-githooks-handover.md). ⚑ INSTALL SHAPE,
ruled by substrate's operator: "don't use symlinks. Import as packages." A repo depends on
mikemol-hooks and its `.githooks/pre-push` is one line:

    exec <venv>/bin/mikemol-githook-pre-push "$@"

The shell version this replaces, `githooks/pre-push` (521d77c), is the specification. Its five
decoy-repository arms are ported to `tests/test_githook_pre_push.py`.

1. BLOCK while a git operation is in flight: index.lock, a rebase, a merge, a cherry-pick or a
   revert. Pushing then races it.
2. THE EXTENSION POINT (el-openglo's ask): if `<toplevel>/.githooks/pre-push.local` is
   executable, run it with the same arguments and the SAME stdin, byte for byte, and refuse the
   push if it fails. A repo's own policy lives there (substrate's post-commit-marker check does).
   A missing or non-executable local hook is not an error.

⚑ STDIN IS READ ONCE, HERE, before anything else runs. Git sends the ref list once. The stub
execs this script, so the stub never touches stdin; a design that ran the local hook from the
stub would have to capture stdin in every repo, which is the duplication the package removes.
It is read from file descriptor 0 as bytes, undecoded, so the replay is byte-identical.

⚑ FAILS CLOSED: no git on PATH, or a git that cannot answer, refuses the push rather than
skipping the checks — a silent skip would read as a pass.

⚑ NOT named `mikemol-hook-…`: those are Claude-harness hooks, and an arm requires each of them to
be wired in settings.json. This one is wired by git, through a repo's `.githooks/pre-push`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import BinaryIO

_IN_FLIGHT = (
    "index.lock",
    "rebase-merge",
    "rebase-apply",
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
)
_LOCAL = Path(".githooks") / "pre-push.local"
_STDIN_FD = 0


class GitUnavailableError(RuntimeError):
    """No `git` on PATH: the checks cannot run, so the push is refused, not waved through."""


def _git(*args: str) -> str:
    """Ask git, in the current directory, and fail closed if it cannot answer.

    Returns:
        git's output, stripped.

    Raises:
        GitUnavailableError: when no git is on PATH.

    """
    git = shutil.which("git")
    if git is None:
        msg = "pre-push: no git on PATH — cannot run the checks, push refused"
        raise GitUnavailableError(msg)
    return subprocess.run([git, *args], capture_output=True, text=True, check=True).stdout.strip()


def _stdin_bytes() -> bytes:
    """Read all of stdin as bytes, once, without decoding it.

    Returns:
        the bytes git sent.

    """
    with open(_STDIN_FD, "rb", closefd=False) as stream:
        return stream.read()


def in_flight(git_dir: Path) -> str | None:
    """Name the first in-flight operation marker present in `git_dir`.

    Returns:
        the marker's name, or None when no operation is in flight.

    """
    return next((name for name in _IN_FLIGHT if (git_dir / name).exists()), None)


def main(argv: Sequence[str] | None = None, refs: BinaryIO | None = None) -> int:
    """Run the shared checks, then the repo's executable pre-push.local with the same stdin.

    Returns:
        0 to allow the push; 1 to refuse it. A git that cannot answer raises, which refuses.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    ref_list = refs.read() if refs is not None else _stdin_bytes()
    blocked = in_flight(Path(_git("rev-parse", "--git-dir")))
    if blocked is not None:
        sys.stderr.write(
            f"pre-push: BLOCKED — git operation in flight ({blocked} present).\n"
            "          Wait for it to finish, then push.\n"
        )
        return 1
    local = Path(_git("rev-parse", "--show-toplevel")) / _LOCAL
    if local.is_file() and os.access(local, os.X_OK):
        status = subprocess.run([str(local), *args], input=ref_list, check=False).returncode
        if status != 0:
            sys.stderr.write(f"pre-push: refused by {local} (exit {status})\n")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W464: no untracked executable code (`.py` `.rego` `.sh`) under `.claude/`.

Operator ruling: evidence-producing code is tracked and under the bar from its first write;
`.claude/` holds notes only. Standing rule 16 (`hooks/policy/standing.rego`) refuses the Write or
Edit that would create such a file; this census is the second arm, catching one that arrived by
any other route (a shell redirect, a copy, a peer).

`.claude/worktrees/<name>/` is the workflow harness's checkout of the repository, so its prefix is
stripped (to the innermost one) before the `.claude/` test: a worktree's `hooks/x.py` is ordinary
code, while a worktree's own `.claude/x.py` is not. The same predicate as rule 16's.

⚑ The population is `git ls-files --others` WITHOUT `--exclude-standard`: a gitignored code file
under `.claude/` is still load-bearing code outside the bar, and ignoring it would be the hole.

CONSUMED BY: `.githooks/pre-commit`, as
`hooks/.venv/bin/python3 -m mikemol.hooks.claude_code_census .`.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_WORKTREE_PREFIX = re.compile(r"^.*(?:^|/)\.claude/worktrees/[^/]+/")
_UNDER_CLAUDE = re.compile(r"(?:^|/)\.claude/")
_CODE = re.compile(r"\.(?:py|rego|sh)$")


def offenders(paths: Iterable[str]) -> list[str]:
    """Select the paths that are code under `.claude/`.

    Returns:
        the offending paths, in input order.

    """
    found: list[str] = []
    for path in paths:
        rest = _WORKTREE_PREFIX.sub("", path)
        if _UNDER_CLAUDE.search(rest) and _CODE.search(rest):
            found.append(path)
    return found


def untracked(root: str) -> list[str]:
    """List every untracked path under `root`'s `.claude/`, ignored files included.

    Returns:
        repo-relative paths.

    Raises:
        FileNotFoundError: when git is not on PATH.

    """
    git = shutil.which("git")
    if git is None:
        msg = "git"
        raise FileNotFoundError(msg)
    out = subprocess.run(
        [git, "-C", root, "ls-files", "--others", "-z", "--", ".claude"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def report(paths: Iterable[str]) -> int:
    """Name each offender among `paths` on stderr.

    Returns:
        0 when none is code under `.claude/`, else 1.

    """
    found = offenders(paths)
    for path in found:
        sys.stderr.write(f"claude-code census: REFUSED — untracked code under .claude/: {path}\n")
    return 1 if found else 0


def main(argv: list[str] | None = None) -> int:
    """Census the repository named by the first argument.

    Returns:
        0 when clean, 1 when code is found under `.claude/`, 2 on bad usage or no git.

    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: claude_code_census REPO_ROOT\n")
        return 2
    try:
        paths = untracked(args[0])
    except (OSError, subprocess.CalledProcessError) as exc:
        sys.stderr.write(f"claude-code census: CANNOT CENSUS — {exc}\n")
        return 2
    return report(paths)


if __name__ == "__main__":
    sys.exit(main())

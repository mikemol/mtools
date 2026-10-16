# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse to certify a gate that reads a sibling checkout unless that checkout is at a recorded sha.

    mikemol-sibling-pin ROOT SHA

A gate that reads another repository (a sibling's files, its tests, its policy) certifies a fact
about whatever that checkout happens to hold. If it is at a different commit or has uncommitted
edits, the certificate is about a tree nobody recorded. This asks the sibling one question: is its
HEAD the sha the caller recorded, and is its working tree clean? It prints one JSON line and exits 0
only when both hold.

⚑ ROOT MUST BE ABSOLUTE (amr-skills:W297): a relative declared root resolves against the isolated
snapshot a hook runs in, so the sibling check would pass vacuously on the wrong directory.

⚑ GIT'S ENVIRONMENT IS STRIPPED FROM EVERY CALL (amr-skills:W297, c2774f9): inside the isolated
hook, `GIT_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE` are inherited and make git answer for the
COMMITTING repository instead of the sibling. The three are removed from the environment of each git
call made here, so the answer is about ROOT and only ROOT.

CONSUMED BY: `mikemol-sibling-pin`, and gates that read a sibling (W1018, W1019).
"""

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

Runner = Callable[[Sequence[str], Path], tuple[int, str]]

GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
SHA = re.compile(r"[0-9a-f]{7,40}")
USAGE = 2
ARGC = 2
NOT_FOUND = 127


@dataclass(frozen=True)
class Verdict:
    """What the sibling checkout answered."""

    root: str
    expected: str
    head: str
    clean: bool
    ok: bool
    reason: str

    def line(self) -> str:
        """Write the verdict as one JSON line.

        Returns:
            the line, keys sorted, with a trailing newline.

        """
        fields: dict[str, object] = {
            "root": self.root,
            "expected": self.expected,
            "head": self.head,
            "clean": self.clean,
            "ok": self.ok,
            "reason": self.reason,
        }
        return json.dumps(fields, sort_keys=True) + "\n"


def clean_env(base: Mapping[str, str]) -> dict[str, str]:
    """Copy an environment without the three variables that point git at another repository.

    Returns:
        the environment minus `GIT_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE`.

    """
    return {k: v for k, v in base.items() if k not in GIT_ENV}


def run_git(argv: Sequence[str], root: Path) -> tuple[int, str]:
    """Run git in `root` with the repository-pointing variables removed.

    Returns:
        its exit status and its output (standard error when it failed); (127, why) with no git.

    """
    git = shutil.which("git")
    if git is None:
        return NOT_FOUND, "git is not installed"
    try:
        done = subprocess.run(
            [git, "-C", str(root), *argv],
            capture_output=True,
            text=True,
            check=False,
            env=clean_env(os.environ),
        )
    except OSError as exc:
        return NOT_FOUND, f"{type(exc).__name__}: {exc}"
    return done.returncode, (done.stdout if done.returncode == 0 else done.stderr).strip()


def _malformed(root: Path, expected: str) -> str | None:
    """Name what is wrong with the question itself, before git is asked.

    Returns:
        the reason, or None when the root is absolute and the sha has the right shape.

    """
    if not root.is_absolute():
        return "the root must be absolute: a relative one resolves against the wrong directory"
    if not SHA.fullmatch(expected):
        return "the recorded sha must be 7 to 40 lowercase hex digits"
    return None


def check(root: Path, expected: str, runner: Runner = run_git) -> Verdict:
    """Ask the sibling whether it is at `expected` and clean.

    Returns:
        the verdict; `ok` only when HEAD begins with the expected sha and the tree has no changes.

    """
    name = str(root)
    malformed = _malformed(root, expected)
    if malformed is not None:
        return Verdict(name, expected, "", clean=False, ok=False, reason=malformed)
    status, head = runner(["rev-parse", "HEAD"], root)
    if status != 0:
        return Verdict(name, expected, "", clean=False, ok=False, reason=f"not a checkout: {head}")
    if not head.startswith(expected):
        reason = "HEAD is not the recorded sha"
        return Verdict(name, expected, head, clean=False, ok=False, reason=reason)
    status, changes = runner(["status", "--porcelain"], root)
    if status != 0:
        reason = f"git status failed: {changes}"
        return Verdict(name, expected, head, clean=False, ok=False, reason=reason)
    if changes:
        return Verdict(name, expected, head, clean=False, ok=False, reason="uncommitted changes")
    return Verdict(name, expected, head, clean=True, ok=True, reason="")


def main(argv: Sequence[str] | None = None) -> int:
    """Run `ROOT SHA`: print the verdict as a JSON line.

    Returns:
        0 when the sibling is at the sha and clean, 1 when it is not, 2 for a usage error.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != ARGC:
        sys.stderr.write("usage: mikemol-sibling-pin ROOT SHA\n")
        return USAGE
    verdict = check(Path(args[0]), args[1])
    sys.stdout.write(verdict.line())
    return 0 if verdict.ok else 1

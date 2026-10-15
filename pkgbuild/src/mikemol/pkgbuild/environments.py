# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Create the two GitHub environments the publish workflow names, in one command (W1217).

    mikemol-wheel environments OWNER/REPO [--write]

Trusted publishing is registered against an environment name, and the real upload should wait for
the operator, so the repository needs a `testpypi` environment (no rules) and a `pypi` environment
that REQUIRES THE OPERATOR'S APPROVAL. GitHub makes both with one idempotent PUT each
(`PUT /repos/{owner}/{repo}/environments/{name}`), and `gh` is already signed in as the operator,
so this is one command instead of a settings page.

⚑ A DRY RUN BY DEFAULT: without `--write` it prints the two requests it would make and changes
nothing. With `--write` it asks `gh api user` who is signed in, makes both PUTs, and prints each
answer. Running it again changes nothing (a PUT of an existing environment sets the same rules).

⚑ `gh` IS A SEAM: the runner is a parameter, so the tests never reach GitHub.

CONSUMED BY: `mikemol-wheel environments`, the operator's first step (W1153).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

WRITE_FLAG = "--write"
USAGE = 2
NOT_FOUND = 127


def gh(argv: Sequence[str]) -> tuple[int, str]:
    """Run `gh` with `argv` and read its answer.

    Returns:
        its exit status and its standard output and error together; (127, why) with no `gh`.

    """
    tool = shutil.which("gh")
    if tool is None:
        return NOT_FOUND, "gh is not installed"
    done = subprocess.run([tool, *argv], capture_output=True, text=True, check=False)
    return done.returncode, (done.stdout + done.stderr).strip()


def requests_of(repo: str, reviewer: str) -> list[tuple[str, dict[str, object]]]:
    """Name the two environment requests: their API path and their JSON body.

    Returns:
        `(path, body)` for `testpypi` (no rules) and `pypi` (the reviewer must approve).

    """
    base = f"repos/{repo}/environments"
    who: object = int(reviewer) if reviewer.isdecimal() else reviewer
    needs: dict[str, object] = {"reviewers": [{"type": "User", "id": who}]}
    return [(f"{base}/testpypi", {}), (f"{base}/pypi", needs)]


def run(args: Sequence[str], runner: Callable[[Sequence[str]], tuple[int, str]] = gh) -> int:
    """Run `OWNER/REPO [--write]`.

    Returns:
        0 when every request was made (or, dry, listed), 1 when one failed, 2 for a usage error.

    """
    words = [a for a in args if a != WRITE_FLAG]
    if len(words) != 1 or words[0].count("/") != 1:
        sys.stderr.write("usage: mikemol-wheel environments OWNER/REPO [--write]\n")
        return USAGE
    write = WRITE_FLAG in args
    reviewer = "<the signed-in gh user's id>"
    if write:
        status, who = runner(["api", "user", "--jq", ".id"])
        if status != 0 or not who.isdecimal():
            sys.stderr.write(f"environments: cannot tell who is signed in to gh: {who}\n")
            return 1
        reviewer = who
    failed = 0
    with tempfile.TemporaryDirectory() as scratch:
        for place, (path, body) in enumerate(requests_of(words[0], reviewer)):
            line = f"PUT {path} {json.dumps(body)}"
            if not write:
                sys.stdout.write(f"would {line}\n")
                continue
            source = Path(scratch) / f"request-{place}.json"
            source.write_text(json.dumps(body), encoding="utf-8")
            status, answer = runner(["api", "-X", "PUT", path, "--input", str(source)])
            sys.stdout.write(f"{'ok' if status == 0 else 'FAILED'} {line}: {answer[:120]}\n")
            failed += int(status != 0)
    return 1 if failed else 0

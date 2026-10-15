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

from mikemol.pkgbuild import repos

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

WRITE_FLAG = "--write"
REPOS_FLAG = "--repos"
USAGE = 2
NOT_FOUND = 127
SYNOPSIS = "usage: mikemol-wheel environments OWNER/REPO|ROOT [--repos FILE] [--write]\n"


def slugs_of(target: str, layout_file: Path | None) -> list[str] | str:
    """Name the repositories to make environments in.

    ⚑ A DIRECTORY MEANS EVERY REPOSITORY ITS DISTS PUBLISH FROM (W1222): each dist folder under it
    is placed by the layout file (the current layout when none is given), and each distinct
    repository is listed once. Anything else is one OWNER/REPO.

    Returns:
        the OWNER/REPO slugs, or the reason none can be named.

    """
    folder = Path(target)
    if not folder.is_dir():
        if target.count("/") == 1:
            return [target]
        return f"{target} is neither OWNER/REPO nor a directory"
    layout = repos.load(layout_file)
    if isinstance(layout, str):
        return layout
    found = folder.glob("*/pyproject.toml")
    dists = sorted(p.parent.name for p in found if not p.parent.is_symlink())
    if not dists:
        return f"no dist found under {target}"
    return [place.slug() for place in layout.places(dists)]


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
    layout_file = None
    if REPOS_FLAG in words:
        place = words.index(REPOS_FLAG)
        if place + 1 >= len(words):
            sys.stderr.write(SYNOPSIS)
            return USAGE
        layout_file = Path(words[place + 1])
        del words[place : place + 2]
    if len(words) != 1:
        sys.stderr.write(SYNOPSIS)
        return USAGE
    slugs = slugs_of(words[0], layout_file)
    if isinstance(slugs, str):
        sys.stderr.write(f"environments: {slugs}\n")
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
        requests = [r for slug in slugs for r in requests_of(slug, reviewer)]
        for number, (path, body) in enumerate(requests):
            line = f"PUT {path} {json.dumps(body)}"
            if not write:
                sys.stdout.write(f"would {line}\n")
                continue
            source = Path(scratch) / f"request-{number}.json"
            source.write_text(json.dumps(body), encoding="utf-8")
            status, answer = runner(["api", "-X", "PUT", path, "--input", str(source)])
            sys.stdout.write(f"{'ok' if status == 0 else 'FAILED'} {line}: {answer[:120]}\n")
            failed += int(status != 0)
    return 1 if failed else 0

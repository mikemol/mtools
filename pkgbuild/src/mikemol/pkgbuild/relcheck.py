# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build every dist's sdist and wheel from a PINNED SHA in a clean tree, and check each (W1188).

    mikemol-wheel release-check ROOT SHA OUT

The publish preflight (W1151) needs a fact, not a belief: the artifacts that WOULD be uploaded,
built from exactly the commit that would be tagged, pass the metadata check.

⚑ NOTHING COMES FROM THE WORKING TREE. The sha is `git archive`d into a temp directory and every
dist is built there, so an uncommitted edit, an ignored file or a stale `build/` cannot make an
artifact look better (or worse) than the commit. Each dist is a top-level directory holding a
`pyproject.toml`, built through its own DECLARED PEP 517 backend (`build_sdist` then `build_wheel`),
with no network and nothing installed.

⚑ A DIST THAT FAILS TO BUILD IS A ROW, NOT A CRASH: its `ok` is false and its `build` field says
why, so one broken dist is reported beside the others instead of hiding them.

⚑ THREE CHECKS, ALL REQUIRED FOR `ok`: the metadata check (`metacheck`, standard library), the
README rendering (`twinecheck`, W1189: `twine check --strict`) and the shipped-file privacy judge
(`privacycheck`, W1199: no deny and no unaccepted withheld finding in any file the artifacts carry).
Each of the last two reports `ok`, `failed` or `unavailable`, and `unavailable` is a failure.

CONSUMED BY: `mikemol-wheel release-check` and the publish preflight (W1151).
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import metacheck, privacycheck, twinecheck

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

DEFAULT_BACKEND = "setuptools.build_meta"
ARGC = 3
BUILD_ERRORS = (OSError, ValueError, RuntimeError, ImportError, KeyError, TypeError, SystemExit)
Row = dict[str, object]
to_stderr = contextlib.redirect_stdout
run_twine = twinecheck.check
run_privacy = privacycheck.check


def checkout(root: Path, sha: str, dest: Path) -> None:
    """Write the tree of `sha` under `dest`, from git's own object, not the working tree.

    Raises:
        OSError: when git is not installed.

    """
    git = shutil.which("git")
    if git is None:
        msg = "git is not installed"
        raise OSError(msg)
    done = subprocess.run(
        [git, "-C", str(root), "archive", "--format=tar", sha], capture_output=True, check=True
    )
    with tarfile.open(fileobj=io.BytesIO(done.stdout)) as archive:
        archive.extractall(dest, filter="data")


def dists_in(tree: Path) -> list[Path]:
    """Find the dists of a tree: the top-level directories that hold a `pyproject.toml`.

    Returns:
        their directories, in name order.

    """
    return sorted(p.parent for p in tree.glob("*/pyproject.toml"))


def backend_of(dist: Path) -> str:
    """Read the dist's declared PEP 517 backend.

    Returns:
        `build-system.build-backend`, or setuptools' when none is declared.

    """
    text = (dist / "pyproject.toml").read_text(encoding="utf-8")
    table = cast("dict[str, object]", tomllib.loads(text))
    system = table.get("build-system")
    declared = (
        cast("dict[str, object]", system).get("build-backend") if isinstance(system, dict) else None
    )
    return declared if isinstance(declared, str) else DEFAULT_BACKEND


def build_dist(dist: Path, out: Path) -> tuple[Path, Path]:
    """Build the sdist and then the wheel of one dist into `out`.

    Returns:
        the sdist's path and the wheel's path.

    """
    module = importlib.import_module(backend_of(dist))
    build_sdist = cast("Callable[[str], str]", module.build_sdist)
    build_wheel = cast("Callable[[str], str]", module.build_wheel)
    out.mkdir(parents=True, exist_ok=True)
    cwd = Path.cwd()
    try:
        os.chdir(dist)  # PEP 517 builds the project rooted at the CWD
        # ⚑ A BACKEND PRINTS ITS PROGRESS TO STANDARD OUTPUT, which is this command's machine
        # channel (one JSON line per dist): the noise goes to standard error, or the first real
        # run of this over 34 dists buried 34 result lines in 280 KB of `copying ...`.
        with to_stderr(sys.stderr):
            sdist = out / build_sdist(str(out))
            wheel = out / build_wheel(str(out))
    finally:
        os.chdir(cwd)
        shutil.rmtree(dist / "build", ignore_errors=True)
    return sdist, wheel


def row_of(dist: Path, out: Path, sha: str) -> Row:
    """Build one dist and check both artifacts.

    Returns:
        the dist's row: `dist`, `sha`, `ok`, `build` ("ok" or the reason), the `twine` and `privacy`
        states and the two metadata verdicts.

    """
    try:
        sdist, wheel = build_dist(dist, out / dist.name)
    except BUILD_ERRORS as exc:
        reason = f"{type(exc).__name__}: {exc}"
        return {
            "dist": dist.name,
            "sha": sha,
            "ok": False,
            "build": reason,
            "twine": "not run",
            "privacy": "not run",
            "artifacts": [],
        }
    verdicts = [metacheck.verdict(sdist), metacheck.verdict(wheel)]
    twine, detail = run_twine([sdist, wheel])
    privacy, scan = run_privacy([sdist, wheel])
    row: Row = {
        "dist": dist.name,
        "sha": sha,
        "ok": all(v["ok"] for v in verdicts) and twine == "ok" and privacy == "ok",
        "build": "ok",
        "twine": twine,
        "privacy": privacy,
        "artifacts": verdicts,
    }
    if twine != "ok":
        row["twine_detail"] = detail
    if privacy != "ok":
        row["privacy_detail"] = scan
    return row


def release_check(root: Path, sha: str, out: Path) -> list[Row]:
    """Build and check every dist of `sha`.

    Returns:
        one row per dist, in name order.

    """
    with tempfile.TemporaryDirectory() as scratch:
        tree = Path(scratch)
        checkout(root, sha, tree)
        return [row_of(dist, out, sha) for dist in dists_in(tree)]


def run(args: Sequence[str]) -> int:
    """Run `release-check ROOT SHA OUT`: one JSON line per dist, exit 1 if any is not ok.

    Returns:
        0 when every dist built and passed, else 1; 2 for the wrong number of arguments.

    """
    if len(args) != ARGC:
        sys.stderr.write("usage: mikemol-wheel release-check ROOT SHA OUT\n")
        return 2
    rows = release_check(Path(args[0]), args[1], Path(args[2]))
    sys.stdout.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    return 0 if rows and all(r["ok"] for r in rows) else 1

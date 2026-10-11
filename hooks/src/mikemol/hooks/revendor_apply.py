# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build the mtools wheels at one commit, check the writer, and swap the pins (mtools:W990).

⚑ EVERY PROCESS IS A SEAM, NO PROCESS IS IMPORTED. git and uv run through a `Runner`
`(argv, cwd) -> (exit, stdout)`, so the tests drive the whole sequence with a fake that does what
git and uv do to the disk and never start either. The pure half (names, pin rewrite, plan) is
`revendor`; this is the half that reads and writes files and calls out.

⚑ THE SAFETY CHECK IS BUILT IN, NOT REMEMBERED. Before the live venv is touched the new wheels are
installed in a THROWAWAY venv, and the new writer's `--hash` over a COPY of the queue must equal the
live writer's: a writer that reads the queue differently stops the swap with the two hashes named
(luthen-observability:W811 did this by hand for W807 and then built it in).

⚑ NEVER COMMITS, AND REFUSES A DIRTY TREE. The result is a reviewable diff for the repo's own
session; while `pyproject.toml`, `uv.lock` or `vendor/wheels` have uncommitted changes nothing is
built. Everything is built and checked in a scratch directory first, and the repo is written only
after both the build and the hash check passed.
"""

from __future__ import annotations

import hashlib
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import revendor

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type Runner = Callable[[Sequence[str], Path], tuple[int, str]]

WHEELS = Path("vendor") / "wheels"
STATE = Path(".claude") / "paths-forward.json"
_TAIL = 200
_WRITES = ("pyproject.toml", "uv.lock", str(WHEELS))


@dataclass(frozen=True)
class Target:
    """What to re-vendor: the vendoring repo, the mtools checkout, the commit, the live writer."""

    repo: Path
    mtools: Path
    sha: str
    writer: Path


def _failed(what: str, code: int, out: str) -> str:
    return f"{what} failed (exit {code}): {out.strip()[-_TAIL:]}"


def dirty(run: Runner, repo: Path) -> bool:
    """Say whether the files a re-vendor writes have uncommitted changes.

    Returns:
        True when git reports any change, or cannot be asked.

    """
    code, out = run(["git", "status", "--porcelain", "--", *_WRITES], repo)
    return code != 0 or bool(out.strip())


def build(run: Runner, target: Target, work: Path) -> str | None:
    """Archive both dists at the commit and build their wheels into `work/dist`.

    The local version `+g<short>` is set in the ARCHIVED pyproject only, never in the checkout.

    Returns:
        why it failed, or None when both wheels were built.

    """
    short = revendor.short_of(target.sha)
    tar = work / "mtools.tar"
    argv = ["git", "-C", str(target.mtools), "archive", "--format=tar", f"--output={tar}"]
    code, out = run([*argv, target.sha, *revendor.DISTS], work)
    if code != 0:
        return _failed("git archive", code, out)
    with tarfile.open(tar) as archive:
        archive.extractall(work / "src", filter="data")
    for dist in revendor.DISTS:
        project = work / "src" / dist / "pyproject.toml"
        edited = revendor.with_local_version(project.read_text(encoding="utf-8"), short)
        if edited is None:
            return f"{dist}/pyproject.toml has no version {revendor.VERSION} to extend"
        project.write_text(edited, encoding="utf-8")
        argv = ["uv", "build", "--wheel", "--quiet", "--out-dir", str(work / "dist")]
        code, out = run(argv, work / "src" / dist)
        if code != 0:
            return _failed(f"uv build {dist}", code, out)
    return None


def _hash_of(run: Runner, writer: Path, state: Path, work: Path) -> str:
    return run([str(writer), "--state", str(state), "--hash"], work)[1].strip()


def same_reading(run: Runner, target: Target, work: Path) -> str | None:
    """Install the new wheels in a throwaway venv and compare the writers' reading of the queue.

    Returns:
        why the swap must stop, or None when the new writer's `--hash` equals the live one's over
        a copy of the queue.

    """
    short = revendor.short_of(target.sha)
    venv = work / "venv"
    code, out = run(["uv", "venv", "--quiet", str(venv)], work)
    if code != 0:
        return _failed("uv venv", code, out)
    wheels = [str(work / "dist" / revendor.wheel_name(d, short)) for d in revendor.DISTS]
    python = str(venv / "bin" / "python")
    code, out = run(["uv", "pip", "install", "--quiet", "--python", python, *wheels], work)
    if code != 0:
        return _failed("throwaway install", code, out)
    copy = work / "state-copy.json"
    shutil.copyfile(target.repo / STATE, copy)
    live = _hash_of(run, target.writer, copy, work)
    fresh = _hash_of(run, venv / "bin" / "mikemol-paths-forward", copy, work)
    if not live or live != fresh:
        return f"the new writer reads the queue differently: live {live!r} new {fresh!r}"
    return None


def swap(run: Runner, target: Target, work: Path, old: set[str]) -> str | None:
    """Copy the new wheels in, remove the old, move the pins, then lock and sync.

    Returns:
        why it failed, or None when the repo is on the new commit.

    """
    short = revendor.short_of(target.sha)
    for dist in revendor.DISTS:
        name = revendor.wheel_name(dist, short)
        shutil.copyfile(work / "dist" / name, target.repo / WHEELS / name)
    for stale in sorted(old - {short}):
        for dist in revendor.DISTS:
            gone = str(WHEELS / revendor.wheel_name(dist, stale))
            run(["git", "rm", "--quiet", "--force", gone], target.repo)
    project = target.repo / "pyproject.toml"
    moved = revendor.move_sources(project.read_text(encoding="utf-8"), short)
    project.write_text(moved, encoding="utf-8")
    for step in (["uv", "lock"], ["uv", "sync", "--frozen"]):
        code, out = run(step, target.repo)
        if code != 0:
            return _failed(" ".join(step), code, out)
    return None


def apply(run: Runner, target: Target) -> str | None:
    """Re-vendor both dists at the commit: refuse a dirty tree, build and check, then swap.

    Returns:
        why it was refused or failed, or None when the repo now vendors the commit.

    """
    if dirty(run, target.repo):
        return "pyproject.toml, uv.lock or vendor/wheels have uncommitted changes"
    old = revendor.pinned_shorts((target.repo / "pyproject.toml").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failure = build(run, target, work) or same_reading(run, target, work)
        return failure or swap(run, target, work, old)


def checksums(target: Target) -> dict[str, str]:
    """Hash the vendored wheels for the hand-written vendor/wheels/README.md record.

    Returns:
        the sha256 hex of each dist's wheel at the commit.

    """
    short = revendor.short_of(target.sha)
    wheels = {
        dist: target.repo / WHEELS / revendor.wheel_name(dist, short) for dist in revendor.DISTS
    }
    return {dist: hashlib.sha256(path.read_bytes()).hexdigest() for dist, path in wheels.items()}

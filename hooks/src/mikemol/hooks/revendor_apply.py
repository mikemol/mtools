# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build the mtools wheels at one commit, check the writer, and swap the pins (mtools:W990).

⚑ EVERY PROCESS IS A SEAM, NO PROCESS IS IMPORTED. git and uv run through a `Runner`
`(argv, cwd) -> (exit, stdout)`, so the tests drive the whole sequence with a fake that does what
git and uv do to the disk and never start either. The pure half (names, pin rewrite, plan) is
`revendor`; the wheel build itself is `wheel` (mtools:W992, `mikemol-wheel`), shared with every
caller that needs a wheel at a commit; this is the half that reads and writes the repo.

⚑ THE SAFETY CHECK IS BUILT IN, NOT REMEMBERED. Before the live venv is touched the new wheels are
installed in a THROWAWAY venv, and the new writer's `--hash` over a COPY of the queue must equal the
live writer's: a writer that reads the queue differently stops the swap with the two hashes named
(luthen-observability:W811 did this by hand for W807 and then built it in).

⚑ NEVER COMMITS, AND REFUSES A DIRTY TREE. The result is a reviewable diff for the repo's own
session; while `pyproject.toml`, `MODULE.bazel`, `uv.lock` or `vendor/wheels` have uncommitted
changes nothing is built. Everything is built and checked in a scratch directory first, and the
repo is written only after both the build and the hash check passed.

⚑ NEMIK'S LAYOUT TOO (W1449): the wheel paths are moved in `MODULE.bazel` as well as in
`pyproject.toml`, `vendor/wheels/SHA256SUMS` is rewritten for the new wheels when the repo keeps
one, and the new wheels (and that file) are `git add -f`ed because such a repo's
`vendor/wheels/.gitignore` is `*`. Staging is as far as it goes; it still never commits.
"""

import hashlib
import shutil
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks import revendor, wheel

Runner = Callable[[Sequence[str], Path], tuple[int, str]]

WHEELS = Path("vendor") / "wheels"
STATE = Path(".claude") / "paths-forward.json"
SUMS = "SHA256SUMS"
BAZEL = "MODULE.bazel"
_TAIL = 200
_WRITES = ("pyproject.toml", BAZEL, "uv.lock", str(WHEELS))


@dataclass(frozen=True)
class Target:
    """What to re-vendor: the vendoring repo, the mtools checkout, the commit, the live writer.

    `dists` are the wheels the repo vendors (`revendor.vendored`): all moved to the one commit
    together. `tag` is the repo's own local-version prefix (`g`, or empty for nemik).
    """

    repo: Path
    mtools: Path
    sha: str
    writer: Path
    dists: tuple[str, ...] = revendor.DISTS
    sync: bool = True
    """False runs `uv lock` only: `uv sync --frozen` removes packages the lock does not name."""
    tag: str = revendor.TAG


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
    """Build every dist's wheel at the commit into `work/dist`, through `wheel.build_into`.

    Returns:
        why it failed, or None when every wheel was built.

    """
    source = wheel.Source(target.sha, target.mtools, tag=target.tag)
    return wheel.build_into(run, source, target.dists, work, work / "dist")


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
    names = [revendor.wheel_name(d, short, target.tag) for d in target.dists]
    wheels = [str(work / "dist" / name) for name in names]
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


def _move_file(path: Path, short: str, old: set[str]) -> None:
    # Move the wheel paths (and the prose naming the old commit) in one text file, if it exists.
    if not path.is_file():
        return
    text = revendor.move_sources(path.read_text(encoding="utf-8"), short)
    for stale in sorted(old - {short}):
        text = revendor.move_mentions(text, stale, short)
    path.write_text(text, encoding="utf-8")


def write_sums(target: Target) -> None:
    """Rewrite `vendor/wheels/SHA256SUMS` for the new wheels, when the repo keeps one.

    ⚑ THE `sha256sum ./*.whl` FORMAT (nemik:W417): `<hash>  ./<name>`, names in sorted order, so
    `sha256sum -c` checks it. A repo with no such file gets none.
    """
    sums = target.repo / WHEELS / SUMS
    if not sums.is_file():
        return
    short = revendor.short_of(target.sha)
    names = sorted(revendor.wheel_name(d, short, target.tag) for d in target.dists)
    lines = [
        f"{hashlib.sha256((target.repo / WHEELS / n).read_bytes()).hexdigest()}  ./{n}\n"
        for n in names
    ]
    sums.write_text("".join(lines), encoding="utf-8")


def swap(run: Runner, target: Target, work: Path, old: set[str]) -> str | None:
    """Copy the new wheels in, remove the old, move the pins, then lock and sync.

    Returns:
        why it failed, or None when the repo is on the new commit.

    """
    short = revendor.short_of(target.sha)
    new_names = [revendor.wheel_name(d, short, target.tag) for d in target.dists]
    for name in new_names:
        shutil.copyfile(work / "dist" / name, target.repo / WHEELS / name)
    for stale in sorted(old - {short}):
        for dist in target.dists:
            gone = str(WHEELS / revendor.wheel_name(dist, stale, target.tag))
            run(["git", "rm", "--quiet", "--force", gone], target.repo)
    for name in ("pyproject.toml", BAZEL):
        _move_file(target.repo / name, short, old)
    write_sums(target)
    added = [str(WHEELS / name) for name in new_names]
    if (target.repo / WHEELS / SUMS).is_file():
        added.append(str(WHEELS / SUMS))
    run(["git", "add", "-f", "--", *added], target.repo)
    steps = [["uv", "lock"], ["uv", "sync", "--frozen"]] if target.sync else [["uv", "lock"]]
    for step in steps:
        code, out = run(step, target.repo)
        if code != 0:
            return _failed(" ".join(step), code, out)
    return None


def apply(run: Runner, target: Target) -> str | None:
    """Re-vendor the dists at the commit: refuse a dirty tree, build and check, then swap.

    Returns:
        why it was refused or failed, or None when the repo now vendors the commit.

    """
    if dirty(run, target.repo):
        return "pyproject.toml, MODULE.bazel, uv.lock or vendor/wheels have uncommitted changes"
    old = revendor.pinned_shorts((target.repo / "pyproject.toml").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failure = build(run, target, work) or same_reading(run, target, work)
        return failure or swap(run, target, work, old)


def checksums(target: Target) -> dict[str, str]:
    """Hash the vendored wheels for the vendor/wheels/README.md record.

    Returns:
        the sha256 hex of each dist's wheel at the commit.

    """
    short = revendor.short_of(target.sha)
    wheels = {
        dist: target.repo / WHEELS / revendor.wheel_name(dist, short, target.tag)
        for dist in target.dists
    }
    return {dist: hashlib.sha256(path.read_bytes()).hexdigest() for dist, path in wheels.items()}

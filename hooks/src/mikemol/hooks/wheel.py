# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-wheel`: build mtools dists' wheels at ONE commit, one JSON line each (mtools:W992).

    mikemol-wheel DIST... --sha SHA40 --out DIR (--mtools REPO | --src TREE)

⚑ NO WHEELS ARE PUBLISHED ANYWHERE (no release, tag, index or workflow), so a peer that needs a dist
as a content-addressed input builds it from the commit. This is that build as one tool, lifted out
of `revendor_apply` where luthen-observability's re-vendor recipe lives: `git archive` the dists,
set the local version `+g<short>` in the ARCHIVED pyproject only, `uv build --wheel`. `--mtools`
is a git checkout to archive from; `--src` is a tree that already holds the dist directories (an
unpacked archive, for a caller with no git history).

⚑ ALL THE DISTS AT ONE SHA IN ONE RUN, because two specs at different commits can resolve to two
copies of the shared `mikemol` namespace (docs/repinning.md).

⚑ DETERMINISTIC PER SHA, MEASURED: every file of the extracted tree is stamped with one fixed epoch
and the build runs with `SOURCE_DATE_EPOCH` at that epoch. The stamp alone was not enough (measured
2026-10-11: two builds of one commit differed, because setuptools dates the wheel's own `dist-info`
entries by the build clock), so the bytes now depend on neither when nor from what archive.

⚑ ONE JSON OBJECT PER WHEEL ON STDOUT, `{"dist","wheel","sha256"}`, in the order the dists were
named; a failure is one line on stderr and exit 1, and exit 2 is a usage refusal.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import revendor
from mikemol.hooks.repin_cli import run_process

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type Runner = Callable[[Sequence[str], Path], tuple[int, str]]

EXIT_FAILED = 1
EXIT_USAGE = 2
EPOCH = 315_532_800
_USAGE = "usage: mikemol-wheel DIST... --sha SHA40 --out DIR (--mtools REPO | --src TREE)\n"
_VALUED = frozenset({"--sha", "--out", "--mtools", "--src"})
_TAIL = 200


@dataclass(frozen=True)
class Source:
    """Where the dists come from: a git checkout to archive, or a tree that already holds them."""

    sha: str
    mtools: Path | None = None
    tree: Path | None = None


def _failed(what: str, code: int, out: str) -> str:
    return f"{what} failed (exit {code}): {out.strip()[-_TAIL:]}"


def stamp(root: Path) -> None:
    """Give every file and directory under a tree the one fixed epoch, links left alone."""
    for path in [root, *root.rglob("*")]:
        os.utime(path, (EPOCH, EPOCH), follow_symlinks=False)


def extract(run: Runner, source: Source, dists: Sequence[str], work: Path) -> str | None:
    """Put the dists' trees under `work/src`.

    Returns:
        why it failed, or None when each dist directory is there.

    """
    if source.tree is not None:
        for dist in dists:
            if not (source.tree / dist / "pyproject.toml").is_file():
                return f"{dist}/pyproject.toml is not in {source.tree}"
            shutil.copytree(source.tree / dist, work / "src" / dist, symlinks=True)
        return None
    tar = work / "mtools.tar"
    argv = ["git", "-C", str(source.mtools), "archive", "--format=tar", f"--output={tar}"]
    code, out = run([*argv, source.sha, *dists], work)
    if code != 0:
        return _failed("git archive", code, out)
    with tarfile.open(tar) as archive:
        archive.extractall(work / "src", filter="data")
    return None


def build_into(
    run: Runner, source: Source, dists: Sequence[str], work: Path, out: Path
) -> str | None:
    """Build each dist's wheel at the commit into `out`.

    The local version `+g<short>` is set in the EXTRACTED pyproject only, never in a checkout.

    Returns:
        why it failed, or None when every wheel was built.

    """
    short = revendor.short_of(source.sha)
    failure = extract(run, source, dists, work)
    if failure is not None:
        return failure
    for dist in dists:
        project = work / "src" / dist / "pyproject.toml"
        edited = revendor.with_local_version(project.read_text(encoding="utf-8"), short)
        if edited is None:
            return f"{dist}/pyproject.toml has no version {revendor.VERSION} to extend"
        project.write_text(edited, encoding="utf-8")
        stamp(work / "src" / dist)
        argv = ["env", f"SOURCE_DATE_EPOCH={EPOCH}", "uv", "build", "--wheel", "--quiet"]
        argv += ["--out-dir", str(out)]
        code, text = run(argv, work / "src" / dist)
        if code != 0:
            return _failed(f"uv build {dist}", code, text)
    return None


def describe(out: Path, dists: Sequence[str], short: str) -> list[dict[str, str]]:
    """Name and hash the wheels `build_into` left in `out`.

    Returns:
        one record per dist, in the order named; a dist whose wheel is absent is an empty record.

    """
    records: list[dict[str, str]] = []
    for dist in dists:
        name = revendor.wheel_name(dist, short)
        path = out / name
        if not path.is_file():
            records.append({})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append({"dist": dist, "wheel": name, "sha256": digest})
    return records


def _parse(args: Sequence[str]) -> tuple[list[str], dict[str, str]] | None:
    dists: list[str] = []
    valued: dict[str, str] = {}
    rest = list(args)
    while rest:
        name = rest.pop(0)
        if name in _VALUED and rest:
            valued[name] = rest.pop(0)
        elif name.startswith("-"):
            return None
        else:
            dists.append(name)
    return dists, valued


def _source_of(valued: dict[str, str]) -> Source | None:
    sha = valued.get("--sha", "")
    if not revendor.is_full_sha(sha) or ("--mtools" in valued) == ("--src" in valued):
        return None
    if "--src" in valued:
        return Source(sha, None, Path(valued["--src"]))
    return Source(sha, Path(valued["--mtools"]))


def main(argv: Sequence[str] | None = None, runner: Runner = run_process) -> int:
    """Build the named dists' wheels at one commit and print a JSON line for each.

    Returns:
        0 when every wheel was built, 1 on a build failure, 2 for a usage refusal.

    """
    parsed = _parse(sys.argv[1:] if argv is None else argv)
    source = _source_of(parsed[1]) if parsed is not None else None
    if parsed is None or not parsed[0] or "--out" not in parsed[1] or source is None:
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    dists, valued = parsed
    out = Path(valued["--out"])
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        failure = build_into(runner, source, dists, Path(tmp), out)
    records = describe(out, dists, revendor.short_of(source.sha))
    if failure is None and not all(records):
        failure = "a built wheel is missing from the output directory"
    if failure is not None:
        sys.stderr.write(f"mikemol-wheel: {failure}\n")
        return EXIT_FAILED
    sys.stdout.write("".join(json.dumps(record) + "\n" for record in records))
    return 0

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-repin`: survey every repo's mtools pins against a commit, then move them (mtools:W958).

    mikemol-repin [--root DIR] [--sha SHA] [--dist D ...] [--write] [--no-sync]

⚑ A DRY RUN UNLESS `--write`. The survey prints one line per pin, `repo dist form pinned STATUS`,
with STATUS `SAME`, `DIFFERS` or `VENDORED` (a vendored wheel is named, never rewritten: see
`repin`). `--write` needs `--sha`, a full 40-hex commit.

⚑ A REPO WITH UNSAVED WORK IS NEVER TOUCHED. If its `pyproject.toml` or `uv.lock` has uncommitted
changes the repo is skipped, so a rewrite can never be tangled into someone's half-made edit. This
shell never commits: the result is a clean, reviewable diff in each repo for its own session.

⚑ ONE LINE PER REPO AT THE END: `RESULT repo written|synced|sync-failed|skipped-dirty|current`.
The exit is 1 when any sync failed, else 0; 2 for a usage refusal.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import musthave, repin
from mikemol.hooks.musthave_cli import run as run_must_have
from mikemol.hooks.repin_metrics import publish, render
from mikemol.hooks.revendor_cli import run_revendor
from mikemol.hooks.runproc import run_process

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type Runner = Callable[[Sequence[str], Path], tuple[int, str]]

EXIT_FAILED = 1
EXIT_USAGE = 2
SELF = "mtools"
PAR_ENV = "MIKEMOL_REPIN_PAR"
_ENV = os.environ
_NOW = time.time
_PUBLISH = publish
_RENDER = render
_REVENDOR = run_revendor
_MUST_HAVE = run_must_have
_FIXES_AT = musthave.at_commit
_MISSING = musthave.missing_for
_USAGE = (
    "usage: mikemol-repin [--root DIR] [--sha SHA] [--dist D ...] [--metrics FILE] [--write]"
    " [--no-sync]\n"
    "       mikemol-repin --revendor --sha SHA40 [--root REPO] [--mtools DIR] [--write]\n"
    "       mikemol-repin --must-have SHA40 --dists D --reason R [--requires SHA40] [--write]\n"
    "       mikemol-repin --check-must-have [--mtools DIR]\n"
)
_VALUED = frozenset(
    {
        "--root",
        "--sha",
        "--dist",
        "--metrics",
        "--mtools",
        "--must-have",
        "--dists",
        "--reason",
        "--requires",
    }
)
_FLAGS = frozenset({"--write", "--no-sync", "--revendor", "--check-must-have"})


@dataclass(frozen=True)
class Row:
    """One pin in one repo and how it stands against the target.

    `missing` is the must-have fixes a vendored pin lacks by commit ancestry (W1138): None when it
    was not measured (no par, or the pin is not a commit in the mtools history), an empty tuple
    when it has them all.
    """

    repo: str
    dist: str
    form: str
    pinned: str
    status: str
    missing: tuple[str, ...] | None = None

    def line(self) -> str:
        """Render the row as one tab-separated line.

        Returns:
            the line, without a newline.

        """
        return f"{self.repo}\t{self.dist}\t{self.form}\t{self.pinned}\t{self.status}"


def _scannable(directory: Path) -> bool:
    """Say whether a child of the root is a repo to read.

    ⚑ NOT THROUGH A LINK, AND NOT bazel-*: `bazel-<repo>`, `bazel-bin` and the other convenience
    links point at an execroot that holds a stale copy of the repo's own files (substrate measured
    nine false rows from one), and no link is read as data here (operator 2026-10-02).

    Returns:
        True for a real, visible directory that is neither mtools nor a bazel output.

    """
    name = directory.name
    hidden = name.startswith((".", "bazel-"))
    return not hidden and name != SELF and not directory.is_symlink()


def repos(root: Path) -> list[Path]:
    """List the repos to read: `root` itself when it holds a pyproject, else its children that do.

    ⚑ POINTING `--root` AT A REPO READS THAT REPO. It used to read the repo's subdirectories and so
    reported no row for the repo's own root file, which is where most pins live.

    Returns:
        the repo directories, sorted.

    """
    if (root / "pyproject.toml").is_file():
        return [root]
    return [p.parent for p in sorted(root.glob("*/pyproject.toml")) if _scannable(p.parent)]


def _status(pin: repin.Pin, target: str | None) -> str:
    if pin.form == repin.WHEEL:
        return "VENDORED"
    if target is None:
        return "-"
    return "SAME" if repin.same(pin.sha, target) else "DIFFERS"


def survey(
    root: Path,
    target: str | None,
    dists: frozenset[str] | None,
    measure: Callable[[repin.Pin], tuple[str, ...] | None] | None = None,
) -> list[Row]:
    """Read every repo's pins.

    ⚑ `measure` JUDGES A VENDORED WHEEL BY ANCESTRY (W1138): a wheel's sha is not a git pin to
    compare with the par sha, but it is a commit, so it is measured against the must-have fixes.
    Git pins keep their SAME or DIFFERS status and carry no measurement.

    Returns:
        one Row per pin of a selected dist, repos in name order and pins in file order.

    """
    rows: list[Row] = []
    for repo in repos(root):
        text = (repo / "pyproject.toml").read_text(encoding="utf-8")
        rows.extend(
            Row(
                repo.name,
                pin.dist,
                pin.form,
                pin.sha,
                _status(pin, target),
                measure(pin) if measure is not None and pin.form == repin.WHEEL else None,
            )
            for pin in repin.find(text)
            if dists is None or pin.dist in dists
        )
    return rows


def _repin_one(repo: Path, target: str, dists: frozenset[str] | None, runner: Runner) -> str:
    """Rewrite one repo's pyproject unless it has unsaved work.

    Returns:
        `current`, `skipped-dirty` or `written`.

    """
    path = repo / "pyproject.toml"
    new, changed = repin.rewrite(path.read_text(encoding="utf-8"), target, dists)
    if not changed:
        return "current"
    code, out = runner(["git", "status", "--porcelain", "--", "pyproject.toml", "uv.lock"], repo)
    if code != 0 or out.strip():
        return "skipped-dirty"
    path.write_text(new, encoding="utf-8")
    return "written"


def apply(
    root: Path,
    target: str,
    dists: frozenset[str] | None,
    runner: Runner,
    *,
    sync: bool,
) -> list[tuple[str, str]]:
    """Move every repo's selected pins to `target`, syncing each one that changed.

    Returns:
        (repo, result) per repo that has a selected git pin; result is one of `current`,
        `skipped-dirty`, `written` (sync not asked for), `synced` or `sync-failed`.

    """
    selected = {row.repo for row in survey(root, None, dists) if row.form != repin.WHEEL}
    results: list[tuple[str, str]] = []
    for repo in (r for r in repos(root) if r.name in selected):
        result = _repin_one(repo, target, dists, runner)
        if result == "written" and sync:
            result = "synced" if runner(["uv", "sync"], repo)[0] == 0 else "sync-failed"
        results.append((repo.name, result))
    return results


def _parse(args: Sequence[str]) -> tuple[dict[str, list[str]], set[str]] | None:
    """Split the arguments into valued options and flags.

    Returns:
        (valued options, flags), or None on anything unknown or a missing value.

    """
    valued: dict[str, list[str]] = {}
    flags: set[str] = set()
    rest = list(args)
    while rest:
        name = rest.pop(0)
        if name in _FLAGS:
            flags.add(name)
        elif name in _VALUED and rest:
            valued.setdefault(name, []).append(rest.pop(0))
        else:
            return None
    return valued, flags


def _refusal(target: str | None, *, write: bool) -> str | None:
    """Say why the target and the write flag cannot be used together, if they cannot.

    Returns:
        the reason, or None when the arguments are usable.

    """
    if target is None:
        return "--write needs --sha, the full commit to move every pin to" if write else None
    try:
        repin.check_sha(target)
    except ValueError as fault:
        return str(fault)
    return None


def _measure(
    par: str | None, mtools: Path, runner: Runner
) -> Callable[[repin.Pin], tuple[str, ...] | None] | None:
    """Build the ancestry measurement of a vendored pin against the par commit's must-have list.

    ⚑ NO PAR, NO MEASUREMENT: the list is read at a commit, so without one nothing is claimed. A
    list that cannot be read is said on standard error and the census goes on unmeasured.

    Returns:
        a function from a pin to the fixes it lacks (None when the pin is not a commit in the
        history), or None when there is nothing to measure against.

    """
    if par is None:
        return None
    fixes = _FIXES_AT(par, mtools, runner)
    if isinstance(fixes, str):
        sys.stderr.write(f"mikemol-repin: {fixes}\n")
        return None

    def measure(pin: repin.Pin) -> tuple[str, ...] | None:
        return _MISSING(pin.sha, pin.dist, fixes, mtools, runner)

    return measure


def main(argv: Sequence[str] | None = None, runner: Runner = run_process) -> int:
    """Survey, or with `--write` repin, every repo under the root.

    Returns:
        0 normally, 1 when any sync failed, 2 for a usage refusal.

    """
    parsed = _parse(sys.argv[1:] if argv is None else argv)
    if parsed is None:
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    valued, flags = parsed
    if "--must-have" in valued or "--check-must-have" in flags:
        mtools = Path(valued.get("--mtools", [str(Path.home() / "github" / "mtools")])[-1])
        return _MUST_HAVE(mtools, valued, frozenset(flags), runner)
    if "--revendor" in flags:
        repo = Path(valued.get("--root", [str(Path.cwd())])[-1])
        mtools = Path(valued.get("--mtools", [str(Path.home() / "github" / "mtools")])[-1])
        sha = valued.get("--sha", [""])[-1]
        return _REVENDOR(repo, sha, mtools, runner, frozenset(flags))
    root = Path(valued.get("--root", [str(Path.home() / "github")])[-1])
    target = valued.get("--sha", [None])[-1]
    dists = frozenset(valued["--dist"]) if "--dist" in valued else None
    metrics = valued.get("--metrics", [None])[-1]
    par = target if target is not None or metrics is None else (_ENV.get(PAR_ENV) or None)
    refusal = _refusal(target, write="--write" in flags) or _refusal(par, write=False)
    if refusal is not None:
        sys.stderr.write(f"mikemol-repin: {refusal}\n")
        return EXIT_USAGE
    mtools_dir = Path(valued.get("--mtools", [str(Path.home() / "github" / "mtools")])[-1])
    rows = survey(root, par, dists, _measure(par, mtools_dir, runner))
    sys.stdout.write("".join(f"{row.line()}\n" for row in rows))
    if metrics is not None:
        _PUBLISH(Path(metrics), _RENDER(rows, str(root), par, int(_NOW())))
    if "--write" not in flags or target is None:
        return 0
    results = apply(root, target, dists, runner, sync="--no-sync" not in flags)
    sys.stdout.write("".join(f"RESULT {repo} {result}\n" for repo, result in results))
    return EXIT_FAILED if any(result == "sync-failed" for _repo, result in results) else 0

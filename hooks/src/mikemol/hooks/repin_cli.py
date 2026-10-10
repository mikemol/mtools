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

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import repin

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type Runner = Callable[[Sequence[str], Path], tuple[int, str]]

EXIT_FAILED = 1
EXIT_USAGE = 2
SELF = "mtools"
_USAGE = "usage: mikemol-repin [--root DIR] [--sha SHA] [--dist D ...] [--write] [--no-sync]\n"
_VALUED = frozenset({"--root", "--sha", "--dist"})
_FLAGS = frozenset({"--write", "--no-sync"})


@dataclass(frozen=True)
class Row:
    """One pin in one repo and how it stands against the target."""

    repo: str
    dist: str
    form: str
    pinned: str
    status: str

    def line(self) -> str:
        """Render the row as one tab-separated line.

        Returns:
            the line, without a newline.

        """
        return f"{self.repo}\t{self.dist}\t{self.form}\t{self.pinned}\t{self.status}"


def run_process(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
    """Run a command in a directory.

    Returns:
        its exit code and standard output; 127 and empty when the program is missing.

    """
    try:
        done = subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 127, ""
    return done.returncode, done.stdout


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


def survey(root: Path, target: str | None, dists: frozenset[str] | None) -> list[Row]:
    """Read every repo's pins.

    Returns:
        one Row per pin of a selected dist, repos in name order and pins in file order.

    """
    rows: list[Row] = []
    for repo in repos(root):
        text = (repo / "pyproject.toml").read_text(encoding="utf-8")
        rows.extend(
            Row(repo.name, pin.dist, pin.form, pin.sha, _status(pin, target))
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
    root = Path(valued.get("--root", [str(Path.home() / "github")])[-1])
    target = valued.get("--sha", [None])[-1]
    dists = frozenset(valued["--dist"]) if "--dist" in valued else None
    refusal = _refusal(target, write="--write" in flags)
    if refusal is not None:
        sys.stderr.write(f"mikemol-repin: {refusal}\n")
        return EXIT_USAGE
    sys.stdout.write("".join(f"{row.line()}\n" for row in survey(root, target, dists)))
    if "--write" not in flags or target is None:
        return 0
    results = apply(root, target, dists, runner, sync="--no-sync" not in flags)
    sys.stdout.write("".join(f"RESULT {repo} {result}\n" for repo, result in results))
    return EXIT_FAILED if any(result == "sync-failed" for _repo, result in results) else 0

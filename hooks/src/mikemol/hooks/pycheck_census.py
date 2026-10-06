# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W794: findings per file under the edit gate's OWN verdict, the ledger debtplan mints from.

The host's debt ledgers were measured by mypy alone, so a card's finding count was not what
actually refuses an edit: the gate also judges ruff, ruff-format and suppressions, per the file's
own project bar. This reads the SAME per-file verdict (`pycheck.analyze`, through
`mikemol-pycheck --census`) and counts what its report names, so ONE measurement is the gate's.

⚑ A COUNT IS READ FROM THE REPORT'S OWN MARKERS, never guessed: a ruff block states `Found N
error`, a ruff-format block carries one `@@` hunk per place it would change, a mypy block one
`: error:` line per finding, a syntax block one `[syntax]` line. A refused file whose report
yields no marker still counts 1, so a file that refuses is never debt-free.

⚑ A FILE NO CHECKER COULD JUDGE IS NOT CLEAN AND IS NOT IN THE LEDGER: it is returned apart as
`unchecked`, because a ledger that read blindness as zero debt once retired 178 real cards.

⚑ THE FILES ARE NAMED FROM GIT'S INDEX, never globbed or walked (operator: inputs are named).

⚑ A LEDGER IS REPLACED WHOLE OR NOT AT ALL (W821): `write_ledger` stages beside the target and
renames over it, so a census that failed leaves the previous ledger standing. A shell redirect
would have truncated it first, which is why the refresh is a mode of the tool, not `> file`.

CONSUMED BY: `pycheck_cli` (`mikemol-pycheck --census`, `--refresh-ledger`).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from mikemol.hooks.verdict import Verdict

_RUFF = re.compile(r"^\s*Found (\d+) errors?\b", re.MULTILINE)
_HUNK = re.compile(r"^@@ ", re.MULTILINE)
# A syntax finding is spelled like a mypy one (`path: error: ...  [syntax]`): it is counted once,
# as syntax, so the mypy marker refuses a line that ends in that tag.
_MYPY = re.compile(r": error:(?!.*\[syntax\])")
_SYNTAX = re.compile(r"\[syntax\]")
_MINIMUM = 1
_PY_SUFFIX = ".py"
_GIT_TIMEOUT_S = 60
# A porcelain v1 entry is `XY path`: two status letters, a space, the path.
_STATUS_WIDTH = 2
_STATUS_PREFIX = 3
_ORIGIN_FOLLOWS = frozenset("RC")


def _occurrences(pattern: re.Pattern[str], report: str) -> int:
    """Count the non-overlapping matches of `pattern` in `report`.

    Returns:
        the number of matches.

    """
    return sum(1 for _found in pattern.finditer(report))


def _ruff_total(report: str) -> int:
    """Sum the counts ruff states in `Found N error(s)` lines.

    Returns:
        the total, 0 when ruff stated none.

    """
    total = 0
    for found in _RUFF.finditer(report):
        words = found.string[found.start() : found.end()].split()
        total += int(words[1])
    return total


def findings(report: str) -> int:
    """Count the findings a refusal report names, at least one for any refusal.

    Returns:
        the sum of the ruff, ruff-format hunk, mypy and syntax markers, or 1 when none match.

    """
    hunks = _occurrences(_HUNK, report)
    typed = _occurrences(_MYPY, report)
    broken = _occurrences(_SYNTAX, report)
    return max(_ruff_total(report) + hunks + typed + broken, _MINIMUM)


def tracked_python(root: Path) -> list[str] | None:
    """Name the Python files git tracks under `root`, from its index.

    Returns:
        the tracked `.py` paths relative to `root`, or None when git is absent or refused.

    """
    git = shutil.which("git")
    if git is None:
        return None
    try:
        done = subprocess.run(
            [git, "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return sorted(name for name in done.stdout.split("\0") if name.endswith(_PY_SUFFIX))


def _status_paths(porcelain: str) -> list[str]:
    """Read the live paths out of `git status --porcelain=v1 -z`.

    ⚑ A RENAME OR COPY ENTRY IS TWO NAMES (the new path, then the origin): the origin no longer
    exists, so it is skipped. A deletion on either side is not a file to judge.

    Returns:
        the paths of added, modified, renamed and untracked files, in git's order.

    """
    tokens = porcelain.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        entry = tokens[index]
        index += 1
        if len(entry) < _STATUS_PREFIX:
            continue
        status, path = entry[:_STATUS_WIDTH], entry[_STATUS_PREFIX:]
        if status[0] in _ORIGIN_FOLLOWS or status[1] in _ORIGIN_FOLLOWS:
            index += 1
        if "D" not in status:
            paths.append(path)
    return paths


def changed_python(root: Path) -> list[str] | None:
    """Name the Python files that are modified, added or untracked under `root`, from git.

    ⚑ ROOT IS THE REPOSITORY'S TOP: porcelain paths are relative to it, whatever the cwd.

    Returns:
        the changed `.py` paths, sorted, or None when git is absent or refused.

    """
    git = shutil.which("git")
    if git is None:
        return None
    try:
        done = subprocess.run(
            [git, "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return sorted(name for name in _status_paths(done.stdout) if name.endswith(_PY_SUFFIX))


def census(
    root: Path,
    files: Iterable[str],
    analyze: Callable[[str, str], Verdict],
) -> tuple[dict[str, int], list[str]]:
    """Judge each file under `root` and count the findings of those the gate would refuse.

    Returns:
        the findings per refused file (relative to `root`), and the files no checker judged.

    """
    debt: dict[str, int] = {}
    unchecked: list[str] = []
    for rel in files:
        try:
            content = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            unchecked.append(rel)
            continue
        ok, report = analyze(content, str(root / rel))
        if ok is None:
            unchecked.append(rel)
        elif not ok:
            debt[rel] = findings(report)
    return dict(sorted(debt.items())), sorted(unchecked)


def write_ledger(target: Path, debt: Mapping[str, int]) -> None:
    """Replace the ledger at `target` whole, or leave the old one standing.

    Raises:
        OSError: when the ledger could not be staged or renamed (the old file is untouched).

    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, staged_name = tempfile.mkstemp(dir=target.parent, prefix=".debt-ledger-", suffix=".tmp")
    staged = Path(staged_name)
    plain: dict[str, int] = {**debt}
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(plain, indent=2) + "\n")
        staged.replace(target)
    except OSError:
        staged.unlink(missing_ok=True)
        raise

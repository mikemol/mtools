# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Discover which files ARE selftest suites: a dispatch that answers `--selftest`.

Moved from substrate's `substrate/suite_discovery.py` (N-a row 2); its suite is ported to
`tests/test_suite_discovery.py`.

⚑⚑ A SUITE IS WHAT `python <path> --selftest` PRODUCES A RESULT FROM. That is not statically
decidable, so this is its closest static proxy: an ENTRY POINT plus evidence it does selftest
work, where the evidence is the UNION of naming the flag or defining `_selftest`. Measured in
substrate, requiring either alone erased real suites, and the under-admitting direction is the
costly one: a missing suite vanishes into a smaller green total that nobody has a prior for.

⚑⚑ GIT'S IGNORE IS THE ONE OWNER OF WHICH TOP-LEVEL TREES ARE WALKED. A name-keyed roster was
removed by operator ruling in substrate: it answers *which directories did someone think of*,
never *which files are suites*. Only nested noise a top-level walk cannot see stays in
`SKIP_DIRS`.

⚑ The tree is always the caller's argument; there is no default root.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

# Vendored and venv noise, and editor snapshot copies: a backup of a suite is not a second one.
SKIP_DIRS = frozenset({".venv", "__pycache__", ".edit-snapshots", "node_modules", ".git"})

# ⚑ TWO ENTRY-POINT SPELLINGS, BOTH LIVE AND BOTH MEASURED: anchoring on the `__main__` idiom
# alone dropped a passing 12/12 suite that dispatches on a bare module-level flag test.
HAS_ENTRY = re.compile(
    r"^if\s+__name__\s*==\s*[\"']__main__[\"']\s*:"
    r"|^if\s+[\"']--selftest[\"']\s+in\s+sys\.argv\s*:",
    re.MULTILINE,
)

# ⚑ The flag must be handled somewhere: an entry point alone is every CLI in the tree.
HANDLES_SELFTEST = re.compile(r"--selftest")

# ⚑ NOT required alongside the dispatch: a split module keeps the body in a sibling.
HAS_SELFTEST = re.compile(r"^def _selftest\s*\(", re.MULTILINE)

# How long git may take to answer before the walk proceeds without it.
_GIT_TIMEOUT_S = 30


def _ignored(root: Path, names: list[str]) -> frozenset[str]:
    """Ask git which of `names` it ignores in `root`, rather than restating .gitignore.

    ⚑ A GIT THAT CANNOT ANSWER IGNORES NOTHING: outside a repo, or with git absent, the dotfile
    rule still applies. That is substrate's recorded degradation, so a fixture in a temp
    directory still runs.

    Returns:
        the ignored names; empty when git cannot answer.

    """
    git = shutil.which("git")
    if not names or git is None:
        return frozenset()
    try:
        done = subprocess.run(
            [git, "-C", str(root), "check-ignore", "--stdin"],
            input="\n".join(names),
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    return frozenset(line.strip() for line in done.stdout.splitlines() if line.strip())


def roots(root: Path) -> tuple[str, ...]:
    """Discover the top-level directories of `root` that may hold suites.

    Returns:
        the sorted non-hidden directory names git does not ignore.

    """
    named = [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]
    return tuple(sorted(set(named) - _ignored(root, named)))


def is_suite(src: str) -> bool:
    """Report whether a file's source makes it a suite.

    Returns:
        True for an entry point AND (the flag named OR `_selftest` defined).

    """
    return bool(
        HAS_ENTRY.search(src) and (HANDLES_SELFTEST.search(src) or HAS_SELFTEST.search(src))
    )


def discover(root: Path) -> list[tuple[str, str]]:
    """List every file under `root` that IS a suite.

    Returns:
        `(root-relative label, absolute path)` pairs, in walk order.

    """
    out: list[tuple[str, str]] = []
    for tree in roots(root):
        for dirpath, dirnames, filenames in os.walk(root / tree):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                path = Path(dirpath) / name
                try:
                    src = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if is_suite(src):
                    out.append((str(path.relative_to(root)), str(path)))
    return out

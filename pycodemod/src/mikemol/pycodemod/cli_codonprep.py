# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`codon-prep-tree`: hoist the TYPE_CHECKING blocks, drop the future import, prove the project.

⚑⚑ THE TWO VERBS ARE ONE ROLLOUT, SO ONE MODE (mtools:W1359, W1363). `type-checking-imports` alone
leaves a hoisted import that ruff's TC rules call typing-only under the deferred annotations the
future import buys, and the bar refuses it; `future-import` alone quotes every TYPE_CHECKING-only
name, which the hoist would have made unnecessary. Run in that order, per project, the pair leaves
nothing to quote and nothing for TC003 to flag (measured on cvdcore, mtools 22607ae).

⚑ A PROJECT IS WRITTEN WHOLE OR NOT AT ALL. After both verbs the changed files are held to the
repository's bar (`mikemol-pycheck --check-file`, the same gate a commit meets) and the project's
own tests run once; a failure in either restores every file the mode wrote and is exit 2. A dry run
writes nothing and runs neither: it reports each verb's candidates, and the future-import count in
a dry run is of the files as they stand, before the hoist has removed what would need quoting.

    mikemol-pycodemod codon-prep-tree [--write] PROJECT...
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_futureimport import print_future_import
from mikemol.pycodemod.cli_typedargs import TypedArgsFlags, run_tool
from mikemol.pycodemod.cli_typingblocks import (
    print_typing_blocks,
    restore,
    source_files,
    tested,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.cli_typedargs import Runner

LABEL = "codon-prep"
_FAILED = 2
_TAIL = 3


def _changed(snapshot: dict[str, str]) -> list[str]:
    return [name for name, text in snapshot.items() if Path(name).read_text("utf-8") != text]


def _barred(root: Path, names: Sequence[str], run: Runner) -> str | None:
    """Hold each changed file to the repository bar.

    Returns:
        None when every file is admitted, else a line naming the first that is not.

    """
    pycheck = root.parent / "hooks" / ".venv" / "bin" / "mikemol-pycheck"
    for name in names:
        code, out, err = run([str(pycheck), "--check-file", name], root)
        if code != 0:
            tail = " | ".join((out + err).strip().splitlines()[:_TAIL])
            return f"{name} fails the bar (exit {code}): {tail}"
    return None


def _both(files: list[str], flags: TypedArgsFlags, run: Runner) -> int:
    # The hoist first, then the future import: the order the pair is measured in.
    return max(print_typing_blocks(files, flags, run), print_future_import(files, flags, run))


def _prepared(root: Path, files: list[str], snapshot: dict[str, str], run: Runner) -> int:
    # Write both verbs over one project, then the bar, then its tests once; restore on a failure.
    code = _both(files, TypedArgsFlags(root=str(root), write=True), run)
    if code >= _FAILED:
        restore(snapshot)
        return code
    broken = _barred(root, _changed(snapshot), run)
    if broken is not None:
        restore(snapshot)
        sys.stdout.write(f"{LABEL} {broken}; every file restored\n")
        return _FAILED
    python = root / ".venv" / "bin" / "python"
    return max(code, tested(root, python, snapshot, run))


def print_codon_prep_tree(roots: Sequence[str], *, write: bool, run: Runner = run_tool) -> int:
    """Run both verbs over each project's `src`, proving each project before it is kept.

    Returns:
        the largest exit code any project produced (0 done, 1 worklist, 2 a tool, the bar or the
        tests failed).

    """
    worst = 0
    for root in map(Path, roots):
        python = root / ".venv" / "bin" / "python"
        if not (root / "src").is_dir() or not python.exists():
            sys.stdout.write(f"{LABEL} skipped {root}: no src tree or no .venv/bin/python\n")
            continue
        files = source_files(root)
        snapshot = {name: Path(name).read_text(encoding="utf-8") for name in files}
        if write:
            code = _prepared(root, files, snapshot, run)
        else:
            code = _both(files, TypedArgsFlags(root=str(root), write=False), run)
        sys.stdout.write(f"{LABEL} project {root} exit {code}\n")
        worst = max(worst, code)
    return worst

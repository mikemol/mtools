# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`codon-prep-tree`: type statements to aliases, hoist TYPE_CHECKING, drop the future import.

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

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.pycodemod import mutantslines, ruffignore
from mikemol.pycodemod.cli_exceptsplit import print_except_split
from mikemol.pycodemod.cli_futureimport import print_future_import
from mikemol.pycodemod.cli_kwonly import print_kwonly
from mikemol.pycodemod.cli_typealias import print_type_alias
from mikemol.pycodemod.cli_typedargs import Runner, TypedArgsFlags, run_tool
from mikemol.pycodemod.cli_typingblocks import (
    print_typing_blocks,
    restore,
    source_files,
    tested,
)

LABEL = "codon-prep"
_FAILED = 2
_TAIL = 3
_FINDING = re.compile(r"^([a-z][a-z0-9-]*): ", re.MULTILINE)
SELF_FIXABLE = frozenset(
    {
        "boolean-type-hint-positional-argument",
        "boolean-default-value-positional-argument",
        "typing-only-first-party-import",
        "typing-only-third-party-import",
        "typing-only-standard-library-import",
    }
)
"""The rules a rewrite makes contradict Codon; each is switched off, per dist, in pyproject."""
_WHY = (
    "CODON REJECTS A BARE `*,` AND A TYPE_CHECKING GUARD (mtools:W1319, W1340, W1343): the rules\n"
    "that demand them are off for this dist."
)


@dataclass(frozen=True, slots=True)
class Refusal:
    """The bar's refusal of one file: which file, its exit, what it said, which rules."""

    name: str
    code: int
    output: str

    @property
    def rules(self) -> frozenset[str]:
        """Name the rule ids of the findings in the output."""
        return frozenset(cast("list[str]", _FINDING.findall(self.output)))

    @property
    def self_fixable(self) -> bool:
        """Say whether every finding is a rule the rewrite itself makes contradict the target."""
        return bool(self.rules) and self.rules <= SELF_FIXABLE

    def line(self) -> str:
        """Render the refusal as one line.

        Returns:
            the file, the exit and the first lines of the output.

        """
        tail = " | ".join(self.output.strip().splitlines()[:_TAIL])
        return f"{self.name} fails the bar (exit {self.code}): {tail}"


def _changed(snapshot: dict[str, str]) -> list[str]:
    return [name for name, text in snapshot.items() if Path(name).read_text("utf-8") != text]


def _barred(root: Path, names: Sequence[str], run: Runner) -> Refusal | None:
    """Hold each changed file to the repository bar.

    Returns:
        None when every file is admitted, else the refusal of the first that is not.

    """
    pycheck = root.parent / "hooks" / ".venv" / "bin" / "mikemol-pycheck"
    for name in names:
        code, out, err = run([str(pycheck), "--check-file", name], root)
        if code != 0:
            return Refusal(name, code, out + err)
    return None


def _ignore_the_contradiction(root: Path, refusal: Refusal) -> str | None:
    """Switch off, in the dist's pyproject, the rules the rewrite made contradict the target.

    Returns:
        the pyproject's text before the edit (so a failure can put it back), or None when there was
        no `ignore` list to extend.

    """
    path = root / "pyproject.toml"
    before = path.read_text(encoding="utf-8")
    after = ruffignore.add(before, sorted(refusal.rules), _WHY)
    if after is None or after == before:
        return None
    path.write_text(after, encoding="utf-8")
    return before


def _both(files: list[str], flags: TypedArgsFlags, run: Runner) -> int:
    # Aliases first (so a block of imports and aliases can be hoisted), then the hoist, then the
    # future import: the order the three are measured in.
    return max(
        print_type_alias(files, flags, run),
        print_typing_blocks(files, flags, run),
        print_future_import(files, flags, run),
        print_except_split(files, flags, run),
        print_kwonly(files, flags, run),
    )


def _prepared(root: Path, files: list[str], snapshot: dict[str, str], run: Runner) -> int:
    # Write both verbs over one project, then the bar, then its tests once; restore on a failure.
    code = _both(files, TypedArgsFlags(root=str(root), write=True), run)
    if code >= _FAILED:
        restore(snapshot)
        return code
    original: str | None = None
    broken = _barred(root, _changed(snapshot), run)
    while broken is not None and broken.self_fixable:
        before = _ignore_the_contradiction(root, broken)
        if before is None:
            break
        original = original or before
        sys.stdout.write(f"{LABEL} {root.name}: ruff rules switched off: {sorted(broken.rules)}\n")
        broken = _barred(root, _changed(snapshot), run)
    if broken is not None:
        restore(snapshot)
        _put_back(root, original)
        sys.stdout.write(f"{LABEL} {broken.line()}; every file restored\n")
        return _FAILED
    stale = _stale_mutants(root, snapshot)
    if stale:
        restore(snapshot)
        _put_back(root, original)
        sys.stdout.write(f"{LABEL} {root.name}: declared mutants left matching nothing: {stale}\n")
        return _FAILED
    python = root / ".venv" / "bin" / "python"
    result = tested(root, python, snapshot, run)
    if result >= _FAILED:
        _put_back(root, original)
    return max(code, result)


def _stale_mutants(root: Path, snapshot: dict[str, str]) -> list[str]:
    """List the declared mutants this run left matching nothing (and that matched before).

    ⚑ BLAME ONLY WHAT THE RUN DID: a declaration already stale before the rewrite is the dist's
    own debt and is not charged to it, so the check compares the unapplied set after against before.

    Returns:
        the `<file>::<name>` of each newly stale declaration; empty when the dist has no
        `mutants.regex`.

    """
    declared = root / "mutants.regex"
    if not declared.is_file():
        return []
    lines = declared.read_text(encoding="utf-8")

    def now(file: str) -> str | None:
        path = root / file
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def before(file: str) -> str | None:
        return snapshot.get(str(root / file), now(file))

    return sorted(
        set(mutantslines.unapplied(lines, now)) - set(mutantslines.unapplied(lines, before))
    )


def _put_back(root: Path, original: str | None) -> None:
    # Restore the dist's pyproject when this run had edited it.
    if original is not None:
        (root / "pyproject.toml").write_text(original, encoding="utf-8")


def print_codon_prep_tree(roots: Sequence[str], *, write: bool, run: Runner = run_tool) -> int:
    """Run both verbs over each project's `src`, proving each project before it is kept.

    Returns:
        the largest exit code any project produced (0 done, 1 worklist, 2 a tool, the bar or the
        tests failed).

    """
    worst = 0
    # ⚑ ABSOLUTE ROOTS: the bar's path is built from the root's parent and run with the root as cwd,
    # so a relative root named a `hooks/.venv` that only exists beside the checkout.
    for root in (Path(name).resolve() for name in roots):
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

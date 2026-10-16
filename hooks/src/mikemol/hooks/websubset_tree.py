# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count the refused idioms of a whole tree, by rule, for one transpile target (mtools:W1338).

⚑ THE COMPILER SEES ONE ERROR PER FILE; THE ALLOWLIST SEES THEM ALL. Codon stops at the first
rejection of a module, so a compile census hides everything behind it. This reads every `src` module
under the roots with the same detectors the `--target` gate uses and counts each rule: how many
modules it blocks, and at how many sites. That is the debt by idiom, fleet-wide, with no compile and
no wall-clock, so it runs over the full tree and in order of modules unblocked (the order the
rewrites should land in).

⚑ WHAT IT CANNOT SEE: a construct that has no detector yet (a rule Codon rejects and this module
does not name). The compile census (`mikemol.corpus.codoncensus`) is the check on that: a module
this report calls clean that Codon still rejects names a missing rule.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks import websubset

_SKIP = frozenset({".git", ".venv", "node_modules", "build", "__pycache__", "tests", "stubs"})


@dataclass(frozen=True)
class RuleCount:
    """One rule's reach: the modules it appears in and the sites in all of them."""

    rule: str
    modules: int
    sites: int


@dataclass(frozen=True)
class TreeCensus:
    """The whole tree under one target: per-rule counts and how many modules are clean."""

    target: str
    total: int
    clean: int
    unreadable: int
    rules: tuple[RuleCount, ...]


def source_files(roots: Sequence[Path]) -> list[Path]:
    """List the `src` modules under the roots, sorted, without tests, stubs or `__init__`.

    Returns:
        the paths, each once.

    """
    return sorted(
        {
            path
            for root in roots
            for path in root.rglob("*.py")
            if "src" in path.parts and not _SKIP & set(path.parts) and path.name != "__init__.py"
        }
    )


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as caught:
        if not isinstance(caught, (OSError, UnicodeDecodeError)):
            raise
        return None


def _by_reach(count: RuleCount) -> tuple[int, int, str]:
    return -count.modules, -count.sites, count.rule


def census(roots: Sequence[Path], target: str) -> TreeCensus:
    """Check every module and count each rule by the modules it blocks.

    Returns:
        the census; rules are ordered by modules blocked, most first.

    """
    modules: dict[str, int] = {}
    sites: dict[str, int] = {}
    clean = unreadable = total = 0
    for path in source_files(roots):
        total += 1
        source = _read(path)
        if source is None:
            unreadable += 1
            continue
        found = websubset.check(source, target)
        clean += not found
        for rule in {finding.rule for finding in found}:
            modules[rule] = modules.get(rule, 0) + 1
        for finding in found:
            sites[finding.rule] = sites.get(finding.rule, 0) + 1
    counts = [RuleCount(rule, modules[rule], sites[rule]) for rule in modules]
    return TreeCensus(target, total, clean, unreadable, tuple(sorted(counts, key=_by_reach)))


def render(found: TreeCensus) -> str:
    """Format the census, one rule per line.

    Returns:
        the report text, the totals line first.

    """
    head = (
        f"idioms under target {found.target}: {found.total} module(s), {found.clean} clean, "
        f"{found.unreadable} unreadable\n"
    )
    rows = [f"{c.rule}: {c.modules} module(s), {c.sites} site(s)\n" for c in found.rules]
    return head + "".join(rows)

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check every `ruff: ignore[...]` directive in one distribution is honoured by the gate's ruff.

W385, ported from hooks/tests/test_bar_fires.py's suppression arm. That arm read only
`hooks/tests`, so directives in ratchet, fence and mdstruct, and every one under a `src/` tree,
were never checked (measured 2026-10-02: 7 files in 4 distributions carry one). Here a
distribution checks its own sources, all of them.

A directive the checker does not honour fails silently: the finding it suppressed reappears,
with nothing saying the directive died. So this checks the EFFECT, not the spelling (the spelling
has its own rule, enforced by the distribution's ruff target): ruff, run with the gate's flags
over the files carrying directives, must report no finding for a rule any directive claims to
suppress. A finding for any other rule is the ruff target's business, not this check's, so a red
here is always about suppression.

    suppression_check.py RUFF DIST_DIR

Exit 0 when every directive holds, or the distribution carries none; 1 with each resurfaced
finding; 2 on usage.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

_USAGE = "usage: suppression_check.py RUFF DIST_DIR"
_ARGS = 2
_DIRECTIVE = re.compile(r"#\s*ruff:\s*ignore\[([^\]]+)\]")
_TIMEOUT_S = 120
# ruff's own report that a directive names nothing it can honour: this check's subject, stated by
# the tool, so it is claimed whether or not any directive names it.
_ALWAYS = frozenset({"RUF102", "invalid-rule-code"})

type Runner = Callable[[list[str], Path], str]


def claimed(texts: list[str]) -> frozenset[str]:
    """Collect the rules the directives name, plus ruff's invalid-directive rule.

    Derived from the sources, never typed: a literal list would go stale at the next directive
    and quietly narrow what is checked.

    Returns:
        every rule some directive claims to suppress.

    """
    names: set[str] = set()
    for text in texts:
        # ⚑ DECLARED AT THE EDGE: findall is typed list[Any], which disallow_any_expr refuses.
        groups: list[str] = _DIRECTIVE.findall(text)
        names.update(rule.strip() for group in groups for rule in group.split(","))
    return frozenset(names) | _ALWAYS


def resurfaced(output: str, rules: frozenset[str]) -> list[str]:
    """Pick the ruff findings for a rule a directive claims to suppress.

    Returns:
        each such line of ruff's concise output.

    """
    return [
        line
        for line in output.splitlines()
        if any(f" {rule}" in line or f"{rule}:" in line for rule in rules)
    ]


def ruff_runner(ruff: str) -> Runner:
    """Run the pinned ruff with the gate's flags: no cache, the distribution's config.

    Returns:
        a runner giving ruff's concise output for the named files, run from `dist`.

    """

    def run(files: list[str], dist: Path) -> str:
        proc = subprocess.run(
            [ruff, "check", "--no-cache", "--config", "pyproject.toml"]
            + ["--output-format", "concise", *files],
            capture_output=True,
            text=True,
            check=False,
            cwd=dist,
            timeout=_TIMEOUT_S,
        )
        return proc.stdout

    return run


def _normalise_modes(sources: list[Path]) -> None:
    """Strip invented execute bits from shebang-less sources, as ruff_check.sh does.

    A remote executor stages sources +x, which makes EXE002 fire on a filesystem the CAS invented.
    The gate normalises its population; this check runs its own ruff and so must do the same.
    """
    for src in sources:
        mode = src.stat().st_mode
        if mode & 0o111 and not src.read_bytes().startswith(b"#!"):
            src.chmod(mode & ~0o111)


def check(dist: Path, run: Runner) -> list[str]:
    """Check every directive under `dist` (tests and src alike) is honoured.

    Returns:
        each resurfaced finding; empty when every directive holds or there are none.

    """
    sources = sorted(
        p for p in dist.rglob("*.py") if "ruff: ignore" in p.read_text(encoding="utf-8")
    )
    if not sources:
        return []
    texts = [p.read_text(encoding="utf-8") for p in sources]
    rules = claimed(texts)
    _normalise_modes(sources)
    output = run([str(p.relative_to(dist)) for p in sources], dist)
    return resurfaced(output, rules)


def main(argv: list[str]) -> int:
    """Check the distribution named on the command line.

    Returns:
        0 when every directive holds, 1 on a resurfaced finding, 2 on a usage error.

    """
    if len(argv) != _ARGS:
        sys.stderr.write(_USAGE + "\n")
        return 2
    dist = Path(argv[1])
    if not (dist / "pyproject.toml").is_file():
        sys.stderr.write(f"suppression_check: {dist}/pyproject.toml was not staged; refusing\n")
        return 1
    findings = check(dist, ruff_runner(argv[0]))
    for finding in findings:
        sys.stderr.write(f"a directive claims to suppress this, and ruff reports it: {finding}\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

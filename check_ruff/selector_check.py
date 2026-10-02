# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check a pyproject.toml's ruff selectors agree with the comments that explain them.

W384, ported from hooks/tests/test_bar_fires.py's selector arm, which walked every distribution
from the repo root. Here it runs over one distribution's config, so each repo after the split
(W317) carries it.

The operator adopted `rule-codes-in-selectors` (2026-09-07), which rewrites a selector's rule CODE
to its NAME. The autofix rewrites the value and leaves the prose above it, so a comment can still
cite `S603` over a selector that now says `subprocess-without-shell-equals-true`, and a reader
greps for a code the config no longer carries. Only that contradiction is a finding: a comment
naming a DIFFERENT rule, to explain why the entry exists, is normal and correct.

    selector_check.py RUFF PYPROJECT

Exit 0 when every selector agrees with its comment; 1 with one line per finding; 2 on usage.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

_USAGE = "usage: selector_check.py RUFF PYPROJECT"
_ARGS = 2
_CODE = re.compile(r"\b([A-Z]{1,4}\d{3,4})\b")
_TIMEOUT_S = 60

type RuleName = Callable[[str], str | None]


def ruff_rule_name(ruff: str) -> RuleName:
    """Ask the pinned ruff what a code is called.

    The map is asked of the checker, never written here: a table would go stale the first time
    ruff renamed a rule, which is the event this check exists for.

    Returns:
        a lookup giving the rule's name, or None when ruff does not know the code.

    """

    def name(code: str) -> str | None:
        proc = subprocess.run(
            [ruff, "rule", code, "--output-format", "json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_TIMEOUT_S,
        )
        if proc.returncode != 0:
            return None
        # ⚑ NARROWED AT THE EDGE: json.loads is typed Any, which disallow_any_expr refuses.
        parsed = cast("object", json.loads(proc.stdout))
        if not isinstance(parsed, dict):
            return None
        found = cast("dict[str, object]", parsed).get("name")
        return found if isinstance(found, str) else None

    return name


def check(text: str, rule_name: RuleName, label: str = "pyproject.toml") -> list[str]:
    """Find each selector whose comment cites a code the selector names by its rule name.

    The prose is the comment block immediately above the entry, walked back to the first line
    that is not a comment, so a neighbouring entry's comment is never read as this one's.
    Entries carrying no code are checked too: after the rename they are exactly the population
    this exists for.

    Returns:
        one finding per contradicting entry; empty when every entry agrees with its prose.

    """
    lines = text.splitlines()
    findings = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        value = line.split("=", 1)[1]
        prose: list[str] = []
        for back in range(i - 1, -1, -1):
            if not lines[back].lstrip().startswith("#"):
                break
            prose.append(lines[back])
        found: list[str] = _CODE.findall("\n".join(prose))
        contradicted = sorted(
            {code for code in found if (name := rule_name(code)) is not None and name in value}
        )
        if contradicted:
            findings.append(
                f"{label}:{i + 1}: the selector names this rule by NAME while the comment above "
                f"still cites {contradicted}; a reader greps for a code the selector no longer "
                "carries"
            )
    return findings


def main(argv: list[str]) -> int:
    """Check the pyproject.toml named on the command line.

    Returns:
        0 when every selector agrees, 1 on findings, 2 on a usage error.

    """
    if len(argv) != _ARGS:
        sys.stderr.write(_USAGE + "\n")
        return 2
    config = Path(argv[1])
    if not config.is_file():
        sys.stderr.write(f"selector_check: {config} was not staged; refusing\n")
        return 1
    findings = check(config.read_text(encoding="utf-8"), ruff_rule_name(argv[0]), str(config))
    for finding in findings:
        sys.stderr.write(finding + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

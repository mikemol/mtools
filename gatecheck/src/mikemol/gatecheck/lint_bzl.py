# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The STATIC witness of the verdict/idempotency invariant for .bzl shell strings.

Ported from paperkit's `tools/lint_bzl.py` (paperkit:W142), behaviour unchanged.

A .bzl `run_shell` command must INVOKE tools, never embed program logic or construct/parse data in
a shell string. Fails the build if any .bzl (passed as args) contains a forbidden pattern:

  bare-python3 : `python3 <script>.py|.sh` or `python3 -c` NOT resolved via `command -v`: the
                 ambient-interpreter dependence that left sys.executable='' and made every
                 subprocess-spawning check spuriously flip.
  printf-json  : building a JSON record with printf: the data-construction-in-shell whose spacing
                 drifted from its grep consumer and silently passed a FAILING gate
                 (tools/verdict.py is the one owner of the {verb,verdict} format).
  grep-json    : reading a JSON field with grep (`grep ... "field":`): fragile to spacing; PARSE it.

The build-time pair of the runtime empty-baseline witness (tools/sens.py): together they make "a
verdict is entailed by its inputs and witnesses its own validity" correct-by-construction.
Legit inline shell stays: env exports, /sys reads, `[ -f ]`, and running an ARBITRARY command
(pk_cmd's `sh -c`). `command -v python3 ...` is the sanctioned resolution and is NOT flagged.

Usage:  mikemol-lint-bzl FILE.bzl [FILE.bzl ...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# `python3` immediately followed by whitespace + (-c | a script path) is a BARE invocation. The
# sanctioned `"$(command -v python3)" script.py` has `python3` followed by `)`, so it never matches.
CHECKS = (
    ("bare-python3", re.compile(r"python3\s+(-c\b|[^\s'\"]+\.(py|sh)\b)")),
    ("printf-json", re.compile(r"printf\s+['\"]\\?\{")),
    ("grep-json", re.compile(r"grep\b[^\n|;]*\\\":")),
)


def findings(paths: Sequence[str]) -> list[tuple[str, int, str, str]]:
    """Scan each file line by line for the forbidden patterns.

    Returns:
        `(path, line number, pattern name, stripped line)` for every match, in file order.

    """
    bad: list[tuple[str, int, str, str]] = []
    for path in paths:
        with Path(path).open(encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                bad.extend((path, n, name, line.strip()) for name, rx in CHECKS if rx.search(line))
    return bad


def main(argv: Sequence[str] | None = None) -> int:
    """Lint the .bzl files named in `argv` and report each forbidden pattern on stderr.

    Returns:
        0 when every file is clean, 1 when any pattern matched.

    """
    bad = findings(sys.argv[1:] if argv is None else argv)
    for path, n, name, text in bad:
        sys.stderr.write(f"{path}:{n}: Ξ·lint [{name}] {text}\n")
    if bad:
        sys.stderr.write(
            f"\nΞ·lint: {len(bad)} forbidden pattern(s) — lift logic/JSON into a tool "
            "(tools/verdict.py owns the verdict record), resolve python via "
            "`command -v`.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

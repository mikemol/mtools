# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Turn a checker's findings into ratchet keys, and run the gate over them.

⚑⚑⚑ THE KEY IS `file:rule`, NOT `file:line:rule`. A line number changes when anything above
it moves, so a line-keyed baseline reports the whole file as new debt after an unrelated
edit — every key refused, none of it real. The origin of that mistake is easy to make and
its symptom is a gate that cries wolf until someone disables it.

⚑⚑ AND IT IS NOT `rule` ALONE, EITHER. Collapsing to the rule loses WHERE the debt is, so
paying one file down while another regresses reads as unchanged — the same substitution
blindness the set exists to defeat, one axis over.

⚑ THE COUNT PER (file, rule) IS DELIBERATELY NOT IN THE KEY. Two instances of one rule in
one file is the same debt as three; encoding the count would make an unrelated refactor
that merges two lines look like paydown. The set answers "does this file still owe this
rule", which is the question paydown-only can actually enforce.
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

# ⚑⚑ ruff's concise line is `path:line:col: <rule> message`, and `<rule>` is a RULE NAME
# (`docstring-missing-returns`) rather than a code (`DOC201`) under this configuration. A first
# cut of this pattern matched `[A-Z]+[0-9]+` and produced ZERO keys against a tree with 192
# findings — an empty census that reads exactly like a clean one, which is the fail-open shape
# this module's own docstring warns about. It was caught by running the parser rather than by
# reading it. The path may contain colons (`./src/x.py`), so the split is on the LAST three
# colon-separated fields rather than the first, and the rule is followed by a COLON.
_CONCISE = re.compile(
    r"^(?P<path>.+?):\d+:\d+:\s+(?P<code>[A-Za-z][A-Za-z0-9-]*):")


def parse_concise(lines: Iterable[str]) -> frozenset[str]:
    """Return `{file:rule}` keys from a checker's concise output.

    ⚑ A LINE THAT DOES NOT MATCH IS DROPPED SILENTLY, and that is safe ONLY because the
    caller checks the process's exit code separately: a checker that crashed emits no
    matching lines, which would otherwise read as a clean census and pay the whole baseline
    down in one run. `run_ruff` refuses on an unexpected exit rather than trusting the parse.
    """
    out: set[str] = set()
    for line in lines:
        found = _CONCISE.match(line.strip())
        if found:
            out.add(f"{found['path']}:{found['code']}")
    return frozenset(out)


def run_ruff(dist: Path, *, preview: bool) -> frozenset[str]:
    """Run ruff over one distribution and return its census.

    ⚑⚑ EXIT 0 AND EXIT 1 ARE BOTH SUCCESS HERE — 0 is a clean tree, 1 is findings. Anything
    ELSE (2 is a usage or internal error) means the checker did not run, and a census read
    from a checker that did not run is an empty set that looks exactly like a clean tree.
    That is the fail-open shape this ecosystem keeps paying for, so it raises instead.
    """
    argv = [str(dist / ".venv" / "bin" / "ruff"), "check", "--no-cache",
            "--output-format", "concise", "."]
    if preview:
        argv.insert(3, "--preview")
    proc = subprocess.run(argv, capture_output=True, text=True, check=False, cwd=dist)
    if proc.returncode not in (0, 1):
        msg = (f"ruff exited {proc.returncode} in {dist} — the census is not trustworthy; "
               f"refusing rather than reporting an empty one\n{proc.stderr}")
        raise RuntimeError(msg)
    return parse_concise(proc.stdout.splitlines())

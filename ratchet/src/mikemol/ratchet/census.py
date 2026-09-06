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

import os
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


# ⚑⚑⚑ FILES A BUILD SYSTEM SYNTHESIZES ARE NOT PART OF THE DISTRIBUTION'S CENSUS. rules_python
# creates `__init__.py` at every level of a runfiles tree so it is importable; none of them exist
# in the source tree, and `src/mikemol/__init__.py` is the file PEP 420 forbids here outright,
# because it would make the first-installed distribution the exclusive owner of the `mikemol`
# prefix. MEASURED: the first honest run of the bazel ratchet gate refused 8 keys, all from these.
#
# ⚑⚑ THE CENSUS WAS CORRECT ABOUT WHAT IT SAW; WHAT IT SAW WAS NOT THE DISTRIBUTION. An action
# whose domain is a SUPERSET of the real one fails loudly rather than serving a stale green, which
# is the better of the two ways to be mis-typed — but it is still mis-typed, and the repair is to
# state the domain rather than to widen the baseline to swallow the noise.
# ⚑ A FIRST CUT EXCLUDED EVERY `__init__.py` AND OVER-EXCLUDED. `mdstruct/src/mikemol/mdstruct/
# __init__.py` EXISTS in source and legitimately carried a key; dropping it paid down real debt by
# accident, which is the mirror of the defect being fixed — a domain too NARROW rather than too
# wide, and that one serves a stale green. The synthesized files are exactly the empty ones, so
# the discriminator is emptiness rather than the name.
_SYNTHESIZED = "__init__.py"


def _is_synthesized(path: str, root: Path) -> bool:
    """Report whether `path` names a build-system-synthesized package marker.

    ⚑ rules_python writes an EMPTY `__init__.py` at every level of a runfiles tree so it is
    importable. A hand-written one has content. Checking the bytes rather than the name keeps a
    real file's debt in the census while dropping an artifact the baseline never saw.

    Returns:
        whether `path` names a build-system-synthesized package marker.

    """
    if not path.endswith(_SYNTHESIZED):
        return False
    candidate = root.joinpath(path)
    return candidate.is_file() and not candidate.read_text(encoding="utf-8").strip()


def parse_concise(lines: Iterable[str], root: Path | None = None) -> frozenset[str]:
    """Return `{file:rule}` keys from a checker's concise output.

    ⚑ A LINE THAT DOES NOT MATCH IS DROPPED SILENTLY, and that is safe ONLY because the
    caller checks the process's exit code separately: a checker that crashed emits no
    matching lines, which would otherwise read as a clean census and pay the whole baseline
    down in one run. `run_ruff` refuses on an unexpected exit rather than trusting the parse.

    Returns:
        `{file:rule}` keys from a checker's concise output.

    """
    out: set[str] = set()
    for line in lines:
        found = _CONCISE.match(line.strip())
        if not found:
            continue
        # ⚑ THE `str()` IS THE NARROWING, NOT A FORMALITY — a regex group is typed `str | Any`, and
        # an `Any` reaching the returned mapping is an unchecked shape crossing this boundary.
        path = str(found["path"])
        if root is None or not _is_synthesized(path, root):
            out.add(f"{path}:{found['code']}")
    return frozenset(out)


def run_ruff(dist: Path, *, preview: bool) -> frozenset[str]:
    """Run ruff over one distribution and return its census.

    ⚑⚑ EXIT 0 AND EXIT 1 ARE BOTH SUCCESS HERE — 0 is a clean tree, 1 is findings. Anything
    ELSE (2 is a usage or internal error) means the checker did not run, and a census read
    from a checker that did not run is an empty set that looks exactly like a clean tree.
    That is the fail-open shape this ecosystem keeps paying for, so it raises instead.

    Returns:
        the ruff over one distribution and return its census.

    """
    # ⚑⚑ THE DECLARED BINARY WINS OVER A VENV PATH. This read `.venv/bin/ruff` unconditionally,
    # which is a developer venv no clone contains — the same escape the hooks suite already
    # closed. Under bazel `RUFF_BIN` names a hash-pinned staged input; unset, the venv answers as
    # before. An action reaching for an undeclared binary is invisible to its own key.
    binary = os.environ.get("RUFF_BIN") or str(dist / ".venv" / "bin" / "ruff")
    argv = [binary, "check", "--no-cache",
            "--output-format", "concise", "."]
    if preview:
        argv.insert(3, "--preview")
    proc = subprocess.run(argv, capture_output=True, text=True, check=False, cwd=dist)
    if proc.returncode not in (0, 1):
        msg = (f"ruff exited {proc.returncode} in {dist} — the census is not trustworthy; "
               f"refusing rather than reporting an empty one\n{proc.stderr}")
        raise RuntimeError(msg)
    return parse_concise(proc.stdout.splitlines(), dist)

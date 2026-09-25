# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witness a mode that DISPATCHES while appearing in no self-description.

Moved from substrate (N-a row 6).

⚑⚑⚑ THE VERDICT USED TO BE A DISJUNCTION. The original read "<tool> <mode> is documented (or no
longer dispatched)" — one green over two OPPOSITE states, because a divergence census lists only
tools that HAVE a divergence, so absence from it means either documented or gone.

⚑⚑ THE SPLIT USES A SECOND, DECORRELATED LENS. The DIVERGENCE lens answers "does this mode
diverge"; the FIND lens answers "is this mode DECLARED anywhere, and by which tool". Absent from
divergence and present in find is DOCUMENTED; absent from both is DELETED.

⚑⚑⚑ A DELETED MODE IS **OPEN**, NEVER CLOSED: a finding is not closed by the deletion of its
subject — the cheapest possible false green. So CLOSED is returned on EXACTLY ONE path, the
documented one, which is what lets `finding_polarity` probe this kind as a guard.

⚑⚑ THE LENSES AND THE RUNNER ARE THE CALLER'S — THE LETTER'S §3.2. Substrate's copy hard-wired
`("python3", "scratch/toolmodes.py", "--divergence" | "--find")`: a substrate scratch tool under a
bare interpreter, run from substrate's root. Both argvs and the runner are REQUIRED here; a caller
wanting the ledger's own runner passes `finding_kinds.runner_in(its_repo)`. The contract with the
lenses is their ROW FORMAT, read by `diverges` and `declared_by`.

⚑ PARSE THE ROWS, NEVER PATTERN-MATCH THE RENDERING: the original substringed a column-aligned
block and returned a FALSE ZERO on all three findings it was written to hold.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.ledger.finding_kinds import CLOSED, OPEN, UNRUNNABLE

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.ledger.finding_kinds import Runner, Verdict

# The row marker a divergence listing uses to open a per-tool block.
TOOL_MARK = "── "

# The field a divergence row leads with when the mode dispatches undeclared.
UNDOCUMENTED = "UNDOCUMENTED"

# A divergence row is `<verdict> <mode> …` — the two fields that reader needs present.
DIVERGENCE_ARITY = 2

# A declaration row is `<mode> on <path> [source] …` — three fields before the optional source.
DECLARATION_ARITY = 3

# What a declaration row means when it names no source for the declaration.
UNSTATED = "(source unstated)"


def diverges(out: str, stem: str, mode: str) -> bool:
    """Report whether a divergence listing carries an UNDOCUMENTED row for this tool and mode.

    ⚑ THE BLOCK STRUCTURE IS LOAD-BEARING: rows are grouped under a `── <path>` header, so a row
    under a DIFFERENT tool says nothing about this one, and a shared flag spelling cannot answer
    for every tool that declares it.

    Returns:
        True when this tool's block has the row.

    """
    in_tool = False
    for line in out.splitlines():
        if line.startswith(TOOL_MARK):
            in_tool = line[len(TOOL_MARK) :].strip().endswith(stem)
            continue
        if not in_tool:
            continue
        parts = line.split()
        if len(parts) >= DIVERGENCE_ARITY and parts[0] == UNDOCUMENTED and parts[1] == mode:
            return True
    return False


def declares(parts: list[str], stem: str, mode: str) -> bool:
    """Report whether one find row is THIS tool declaring THIS mode.

    ⚑ EVERY FIELD IS CHECKED, INCLUDING THE PATH: a find listing carries a `⚑ NOT on:` line naming
    every OTHER tool, so a name-only test credits the tool explicitly said not to have it.

    Returns:
        True for this tool's declaration.

    """
    if len(parts) < DECLARATION_ARITY or parts[0] != mode or parts[1] != "on":
        return False
    return Path(parts[2]).name == stem


def declared_by(out: str, stem: str, mode: str) -> str | None:
    """Return the source a find listing credits for this tool's declaration, or None if absent.

    Returns:
        the declaring source, `UNSTATED` when the row names none, or None.

    """
    for line in out.splitlines():
        parts = line.split()
        if declares(parts, stem, mode):
            return parts[DECLARATION_ARITY] if len(parts) > DECLARATION_ARITY else UNSTATED
    return None


def mode_undocumented(
    tool: str,
    mode: str,
    *,
    divergence: Sequence[str],
    find: Sequence[str],
    runner: Runner,
) -> Verdict:
    """Report OPEN while `mode` dispatches in `tool` but appears in no self-description.

    - **OPEN** — the mode still dispatches undocumented, OR the mode is GONE.
    - **CLOSED** — the mode is DECLARED by this tool. The only green path.
    - **UNRUNNABLE** — a lens did not run, so DOCUMENTED cannot be told from DELETED; withheld
      rather than guessed.

    `divergence` is the argv of the divergence lens; `find` is the find lens's, to which the mode
    is appended.

    Returns:
        the verdict and its note.

    """
    rc, out = runner(divergence)
    if rc is None:
        return UNRUNNABLE, f"the divergence lens did not run: {out[:120]}"
    stem = Path(tool).name

    if diverges(out, stem, mode):
        return OPEN, f"{stem} {mode} still dispatches with no self-description"

    # ⚑ REACHING HERE MEANS ONLY "no divergence row", the AMBIGUOUS half; the second lens decides.
    rc2, found = runner((*find, mode))
    if rc2 is None:
        return UNRUNNABLE, (
            f"{stem} {mode} has no divergence row, but the find lens did not run, so DOCUMENTED "
            f"cannot be distinguished from DELETED: {found[:100]}"
        )

    source = declared_by(found, stem, mode)
    if source is not None:
        return CLOSED, f"{stem} {mode} is DOCUMENTED — declared {source}"

    # ⚑ NOT CLOSED. A finding is not closed by the deletion of its subject.
    return OPEN, (
        f"{stem} {mode} is GONE — no divergence row AND no declaration in the find lens. The "
        "finding recorded an UNDOCUMENTED CAPABILITY; if the mode was removed, the repair it names "
        "did not land, the subject did. Re-key or retire this finding deliberately — do not read "
        "this as documented."
    )

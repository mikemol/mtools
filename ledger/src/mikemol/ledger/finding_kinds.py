# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The KIND MACHINERY of a findings ledger — what makes a witness falsifiable.

Moved from substrate (N-a row 6, `inbox/2026-09-24-substrate-findings-letter.md`).

⚑⚑⚑ THE LOAD-BEARING PROPERTY ACROSS EVERY KIND: **A COMMAND THAT CANNOT RUN IS UNRUNNABLE,
NEVER CLOSED AND NEVER OPEN.** An absent instrument is not evidence. It binds hardest on `refuses`,
where a DELETED command exits non-zero for the wrong reason and would otherwise read as a passing
refusal.

⚑⚑ THE VERDICT IS DECIDED BY THE EXIT CODE BEFORE ANY TEXT IS READ. `evidence` and `failing_case`
choose which line to QUOTE and never what the verdict IS, so a miss in either reader degrades the
citation and can never move the finding.

⚑⚑ NO `ROOT`: EVERY COMMAND RUNS WHERE ITS CALLER SAYS. Substrate's copy pinned `cwd` to a path
derived from `__file__`, correct in a checkout and wrong once installed: every witness would run
from `site-packages`, and a ledger's relative commands would fail there as UNRUNNABLE — the quieter
failure, because it reads as a missing instrument rather than as a wrong directory. So `cwd` is a
REQUIRED argument, and only the ledger's CLI — which knows its repository — resolves it.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# How long one witness command may take before it is reported as not having run.
TIMEOUT = 300

Verdict = tuple[int, str]

# ⚑⚑ THE THREE OUTCOMES ARE A VOCABULARY, NOT MAGIC NUMBERS, and naming them lets a reader assert
#   on the DISTINCTION. UNRUNNABLE is not a degree of OPEN: it is the third outcome, and can never
#   collapse into CLOSED or OPEN.
CLOSED = 0
OPEN = 1
UNRUNNABLE = 2

# ⚑ WORDS A REFUSAL ANNOUNCES ITSELF WITH. Not a verdict input — see the module docstring.
_REFUSAL_WORDS: tuple[str, ...] = (
    "refus",
    "error",
    "abort",
    "denied",
    "must ",
    "requires",
    "not permitted",
    "unstated",
    "no such",
)


def run(*argv: str, cwd: Path) -> tuple[int | None, str]:
    """Return `(rc, stdout+stderr)` for one command run in `cwd`. Never raises.

    ⚑ `rc is None` MEANS THE PROCESS NEVER STARTED, which is distinct from any exit code it could
    have produced. Collapsing it into a number is how an absent instrument starts reading as a
    measurement.

    Returns:
        the exit code (None if it never started) and the combined output.

    """
    try:
        done = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def failing_case(out: str) -> str:
    """Return the line most likely to BE the failure, for a suite reporting `n/m` LAST.

    ⚑⚑ `tail[-1]` IS RELIABLY WRONG HERE: a house suite prints `FAIL <name>: <why>` lines and
    THEN its `<suite>: n/m` score, so the last line is always arithmetic. ⚑ The score is reported
    ALONGSIDE, never instead: it is the only line saying HOW MANY failed.

    Returns:
        the citation.

    """
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not lines:
        return "(no output — the exit code is the whole evidence)"
    fails = [ln for ln in lines if ln.startswith("FAIL ")]
    score = next(
        (ln for ln in reversed(lines) if "/" in ln and ln.rstrip().rsplit("/", 1)[-1].isdigit()),
        None,
    )
    if fails:
        more = "" if len(fails) == 1 else f" (+{len(fails) - 1} more failing case(s))"
        tail = "" if not score else f" [{score[:40]}]"
        return f"{fails[0][:140]}{more}{tail}"
    if score:
        return (
            f"{score[:80]} — ⚑ the suite reported a score but NO `FAIL <case>` line, so "
            "which case failed is not in this output"
        )
    return f"(no FAIL line and no score; last output: {lines[-1][:110]})"


def evidence(out: str) -> str:
    """Return the line most likely to BE the refusal, not merely the last line printed.

    ⚑⚑ `tail[-1]` WAS MEASURED WRONG on real witnesses: a refusal ending in a help hint, and one
    ending in a SQL error caret — right verdicts, useless citations. ⚑ A miss is FLAGGED rather
    than hidden behind an incidental last line.

    Returns:
        the citation.

    """
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not lines:
        return "(no output — the exit code is the whole evidence)"
    for line in lines:
        low = line.lower()
        if any(word in low for word in _REFUSAL_WORDS):
            return line[:160]
    return f"(no refusal line found; last output: {lines[-1][:110]})"


def selftest(cmd: list[str], note: str, *, cwd: Path) -> Verdict:
    """Report CLOSED while `cmd` exits 0 — the witness that a mechanism WORKS.

    Returns:
        the verdict and its note.

    """
    code, out = run(*cmd, cwd=cwd)
    spelled = " ".join(cmd)
    if code is None:
        return UNRUNNABLE, f"{spelled} did not run: {out[:120]}"
    if code == 0:
        return CLOSED, f"{spelled} PASSES — {note}"
    return OPEN, f"{spelled} exits {code} — {failing_case(out)}"


def refuses(cmd: list[str], note: str, *, cwd: Path) -> Verdict:
    """Report CLOSED while `cmd` exits NON-ZERO — the witness for an installed REFUSAL.

    ⚑⚑⚑ EXIT 0 IS THE OPEN VERDICT HERE, AND THE INVERSION IS THE POINT: if the command SUCCEEDS
    the refusal is GONE — reverted, weakened, or routed around — and the finding is open.

    Returns:
        the verdict and its note.

    """
    code, out = run(*cmd, cwd=cwd)
    spelled = " ".join(cmd)
    if code is None:
        return UNRUNNABLE, f"{spelled} did not run: {out[:120]}"
    if code != 0:
        return CLOSED, f"REFUSES (exit {code}) — {note} — {evidence(out)}"
    return OPEN, (
        f"{spelled} EXITS 0 — the refusal this finding records is GONE (reverted, "
        f"weakened or routed around): {note}"
    )


def standing(note: str) -> Verdict:
    """Report a measured FACT, which holds until a measurement overturns it.

    ⚑ VACUOUS BY CONSTRUCTION: legitimate ONLY for a measured fact, never for a claim that a
    repair landed, which it cannot see reverted.

    Returns:
        CLOSED and its note.

    """
    return CLOSED, f"STANDING — {note}"


def unwitnessed(note: str) -> Verdict:
    """Report an honest gap: no command distinguishes true from false. ALWAYS UNRUNNABLE.

    Returns:
        UNRUNNABLE and its note.

    """
    return UNRUNNABLE, f"UNWITNESSED — {note}"

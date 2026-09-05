# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the checkers and the flags each one is pointed at the edited file with.

⚑⚑ THE FLAGS APPLIED TO THE CHECKED FILE ARE THE WHOLE RESPONSIBILITY. This hook lints an
IN-FLIGHT edit by staging post-edit content to a TEMPFILE, so without saying otherwise a checker
resolves its path-keyed configuration against `tmpab12cd.py` — matching no `per-file-ignores`
pattern, no `exclude`, no `extend-per-file-ignores`. **A path-keyed exemption cannot reach a temp
copy.** The consequence is broader than any one rule: the gate and a direct `ruff check` disagree
about the same file, ALWAYS, and the disagreement is silent in the direction that manufactures
findings the author cannot act on.

⚑ AND THAT MATTERS MORE AS A PACKAGE THAN IT DID AS A SCRIPT. An adopting repo writes its own
`per-file-ignores`; if the temp copy escaped them, every adopter would see findings against
exemptions they had correctly declared, with nothing to point at.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def checker_argv(tmp: Path, path: str, venv_py: Path,
                 pyproject: Path) -> tuple[tuple[str, list[str], bool], ...]:
    """Return `(name, argv, reads_stdin)` for each checker, naming `path` as the subject.

    ⚑ TWO MECHANISMS, BECAUSE THE TWO CHECKERS SPELL THIS DIFFERENTLY, and the third tuple
    element is what keeps the caller from having to know which is which.
    """
    real = path or str(tmp)
    return (
        # ⚑⚑ `--stdin-filename` IS WHAT MAKES CONFIGURATION REACH AN IN-FLIGHT EDIT. ruff
        # evaluates stdin content AS IF it were the named path, so every path-keyed setting in
        # `pyproject.toml` resolves against the author's real file. Without it this package's own
        # `S603` exemption is inert (measured: the entry landed, and the tempfile still matched no
        # pattern), and so is every `per-file-ignores` entry an ADOPTING repo writes.
        #
        # ⚑ IT ALSO RETIRES THE PATH REWRITE FOR THE RUFF HALF. ruff renders the author's path in
        # its own findings rather than a `tmpab12cd.py` the reader cannot map to anything; the
        # analyze module still rewrites for mypy.
        ("ruff", [str(venv_py), "-m", "ruff", "check",
                  "--config", str(pyproject), "--no-cache",
                  "--stdin-filename", real, "-"], True),
        # ⚑⚑ `--pretty` RENDERS THE SOURCE LINE AND A CARET, AND ITS ABSENCE COST AN AFTERNOON.
        # Without it mypy emits a bare line number naming a line in a tempfile that is deleted
        # microseconds later and never existed on disk — a citation with NO READABLE REFERENT.
        # Acting on it means guessing which construct is there; that was guessed six times on one
        # file, wrong every time, and the line number MOVED as the file grew, which read as
        # evidence of closing in. It was not: the line moved because the FILE moved.
        #
        # ⚑ ruff ALREADY DOES THIS BY DEFAULT, which is why no ruff finding ever cost a wrong
        # guess. So the asymmetry was never between the TOOLS — it was between two INVOCATIONS,
        # and this token is the whole difference.
        #
        # ⚑⚑ mypy NEEDS NO COUNTERPART HERE, AND SAYING IT DID WAS WRONG TWICE. MEASURED, with a
        # positive control because a clean result is ambiguous between CHECKED-clean and
        # NOT-ADMITTED: a file containing `X: int = "not an int"` placed OUTSIDE the repo entirely
        # is still reported `[assignment]`, and a file outside `files` is checked at full
        # strictness with imports followed. **`files` names the DEFAULT TARGET when mypy is given
        # no path; it does not filter what a named path is checked as.** So the tempfile gets
        # exactly the treatment the real file would, and there is no identity defect on this side.
        #
        # ⚑ THE ASYMMETRY IS A PROPERTY OF THE POLICY, NOT A PENDING FIX. ruff HAS a per-file
        # exemption mechanism, so a temp copy escapes it — the defect above. A config carrying NO
        # `[[tool.mypy.overrides]]` section (relief lives on the ENUMERABLE side, never on the
        # unenumerable one) cannot have the exemption-escape defect at all. *By construction*, not
        # yet-to-do.
        #
        # ⚑⚑ RECORDED BECAUSE THE WRONG VERSION PROPAGATED. This comment previously called
        # `--shadow-file` the pending counterpart; that reached two peers as a shared to-do and
        # became a line in one's ledger within the hour, because it sat beside a claim that WAS
        # measured. **An accurate report is the most efficient vector for an inaccurate adjacent
        # claim** — and the replacement offered when retracting it ("`files` decides admission")
        # was ALSO unmeasured, the same shape inside a correction. The positive control caught it;
        # re-reading would not have.
        ("mypy", [str(venv_py), "-m", "mypy", "--config-file", str(pyproject),
                  "--no-error-summary", "--no-color-output", "--pretty", str(tmp)],
         False),
    )

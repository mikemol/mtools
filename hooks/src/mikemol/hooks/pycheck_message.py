# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Render a pycheck refusal: bound it, count it, and route the reader by the SHAPE of the debt.

⚑⚑ A REFUSAL IS A MESSAGE WITH A SIZE, AND IT IS FED STRAIGHT BACK INTO THE SESSION THAT
TRIGGERED IT. Nothing here decides a verdict; it decides what a reader is told and what being
told costs them. Ported from substrate's `scripts/pycheck_message.py` (letter 2026-09-22), minus
that tree's own config citations (`stubs/`, "no `[[tool.mypy.overrides]]`"): an adopting tree's
bar is its own pyproject, and a message quoting another tree's policy is a dangling pointer.

⚑⚑ THE GRAIN IS ONE WRITE, AND THE MESSAGE NOW SAYS SO WHEN THAT IS THE CAUSE. An import and its
first use written in two edits are refused twice — F401 for the import alone, F821 for the use
alone. The refusal is CORRECT (each intermediate file is dirty); the round trip is avoidable, so
an F401/F821-shaped report names the grain instead of leaving the author to rediscover it.

CONSUMED BY: `mikemol.hooks.pycheck`, `mikemol.hooks.pycheck_cli`.
"""

from __future__ import annotations

import re

# The deny message's line budget: its reader did not ask for it and cannot decline it.
MAX_LINES = 25

# The maintainer mode's budget: asked for deliberately, so it can afford more.
CHECK_FILE_LINES = 60

# Above this many findings, listing them is the wrong advice: the file needs splitting.
PAYABLE_IN_ONE_EDIT = 30

# ⚑ THE SPLIT-EDIT SIGNATURE: ruff's unused-import and undefined-name rules, and mypy's
# undefined-name code. Matched at a finding's head, never anywhere in the text, so a message
# QUOTING the code does not trip it.
# ⚑⚑ BOTH SPELLINGS, MEASURED 2026-09-22 on ruff 0.16.6: a config with `preview = true` (this
# repo's) heads each finding with the rule NAME (`unused-import:`), one without it with the CODE
# (`F401 [*]`). A code-only pattern is silent on exactly the tree that ships this hook.
_GRAIN = re.compile(
    r"^\s*(?:F401|F821|unused-import:|undefined-name:)|\[name-defined\]\s*$", re.MULTILINE
)


def clip(report: str, limit: int) -> str:
    """Return at most `limit` non-blank lines of `report`, saying how many were withheld.

    Returns:
        the bounded report, with a withheld-count line when anything was cut.

    """
    lines = [ln for ln in report.splitlines() if ln.strip()]
    if len(lines) <= limit:
        return "\n".join(lines)
    shown = lines[:limit]
    shown.append(
        f"  … {len(lines) - limit} more line(s) withheld — a refusal is BOUNDED; run "
        "`mikemol-pycheck --check-file PATH` for more."
    )
    return "\n".join(shown)


def finding_count(report: str) -> int:
    """Count findings by their head lines, not by rendered lines.

    Returns:
        ruff's `-->` location lines plus mypy's `: error:` lines.

    """
    lines = report.splitlines()
    return sum(1 for ln in lines if ln.lstrip().startswith("--> ")) + sum(
        1 for ln in lines if ": error:" in ln
    )


def grain_note(report: str) -> str:
    """Return the one-write advice when the report is F401/F821-shaped, else "".

    Returns:
        the advice naming the per-write grain, or the empty string.

    """
    if not _GRAIN.search(report):
        return ""
    return (
        "\n  ⚑ THE GRAIN IS ONE WRITE. An unused import (F401) or an undefined name (F821,\n"
        "    [name-defined]) is often an import and its first use split across two edits —\n"
        "    each half is refused on its own. Land the import AND its use in ONE Edit\n"
        "    (widen `old_string` to span both) or one Write."
    )


def debt_note(report: str) -> str:
    """Return the routing advice, which changes once the debt exceeds one edit.

    Returns:
        the split-the-file routing above the threshold, the short reminder below it.

    """
    n = finding_count(report)
    if n <= PAYABLE_IN_ONE_EDIT:
        return (
            "\n  ⚑ A file too large to leave clean in one edit is not a linting problem —\n"
            "    it is the per-file gate saying the file does too much."
        )
    return (
        f"\n  ⚑⚑ {n} FINDINGS — this file cannot be made clean in one edit, and an edit that\n"
        "    leaves it dirty is refused too. Extract the concern you need into a NEW module\n"
        "    written clean in one pass; keep cutting until the dispatch moves out, then\n"
        "    retire this file."
    )


def render(report: str, path: str) -> str:
    """Build the deny message: what was refused, where, and where relief lives.

    Returns:
        the refusal text.

    """
    body = "\n".join("  " + ln for ln in clip(report, MAX_LINES).splitlines())
    named = path or "this file"
    return (
        f"pycheck: this edit leaves {named} with findings — refusing.\n{body}\n"
        "  ⚑ ZERO TOLERANCE: no line-scoped suppression. Relief lives on the ENUMERABLE side\n"
        "    only — a stub for an untyped dependency, or a per-RESPONSIBILITY entry in the\n"
        "    governing pyproject.toml's per-file-ignores — each a reviewed change to that file."
        f"{grain_note(report)}{debt_note(report)}"
    )

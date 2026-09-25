# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Find the line-scoped suppression directives an edit ADDS to a Python file.

⚑⚑⚑ THE BAR SAID "NO LINE-SCOPED SUPPRESSION" AND DID NOT ENFORCE IT. Every refusal pycheck prints
ends "ZERO TOLERANCE: no line-scoped suppression" — yet an edit CARRYING one passed, because ruff
honours `# noqa` and mypy honours `# type: ignore`, so the finding the directive silences never
reached the gate. Measured: substrate landed two `# noqa: PLR2004` edits this way (letter
2026-09-25), and this repo's own session had a `# noqa` and a `# type: ignore` admitted too. A
rule that holds only when the author already knows it is not a gate.

⚑⚑ ADDED, NOT PRESENT: the gate compares the file before and after the edit, and refuses only
directives the edit introduces. Existing debt must not block an unrelated edit to its file —
refusing every edit to a file that carries one would make paying the debt down unlandable.

⚑ COMMENTS ONLY, FOUND BY THE TOKENIZER: the word `noqa` inside a string is not a directive, and a
regex over raw text cannot tell the two apart.

⚑ A MULTISET, SO MOVING A DIRECTIVE IS NOT ADDING ONE: counts are compared per directive text, and
only a count that grows is reported.
"""

from __future__ import annotations

import io
import re
import tokenize
from collections import Counter

# A comment that suppresses a checker's finding on its line (or, for `ruff: noqa`, its file).
_DIRECTIVE = re.compile(
    r"#\s*(noqa\b.*|type:\s*ignore\b.*|ruff:\s*(?:noqa|ignore)\b.*|pyright:\s*ignore\b.*)",
    re.IGNORECASE,
)

RELIEF = (
    "  Relief lives on the ENUMERABLE side: a per-file entry in the governing pyproject.toml's\n"
    "  [tool.ruff.lint.per-file-ignores] (with the reason as a comment beside it), a stub for an\n"
    "  untyped dependency, or a change to the code so the finding does not arise — a named\n"
    "  constant for PLR2004, a Protocol cast for a deliberately wrong call."
)


def _directive_text(comment: str) -> str | None:
    """Return a comment's suppression directive, whitespace-collapsed, or None when it has none.

    ⚑ THE GROUP IS NARROWED AT THE SEAM: `Match.group` is typed `str | Any`.

    Returns:
        the directive text, or None.

    """
    match = _DIRECTIVE.search(comment)
    if match is None:
        return None
    got = match.group(1)
    return " ".join(got.split()) if isinstance(got, str) else None


def directives(source: str) -> Counter[str]:
    """Count the suppression directives in `source`'s comments, keyed by their normalised text.

    ⚑ SOURCE THAT DOES NOT TOKENIZE COUNTS NOTHING: this reads what a checker would honour, and
    the syntax stage already refuses a post-edit file that does not parse.

    Returns:
        each directive's text with how often it occurs.

    """
    found: Counter[str] = Counter()
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type != tokenize.COMMENT:
                continue
            text = _directive_text(token.string)
            if text is not None:
                found[text] += 1
    except (tokenize.TokenError, SyntaxError):
        return Counter()
    return found


def added(before: str, after: str) -> list[str]:
    """Return the directives `after` carries more of than `before`, one entry per extra occurrence.

    Returns:
        the added directives, sorted.

    """
    grown = directives(after) - directives(before)
    return sorted(grown.elements())


def report(path: str, new: list[str]) -> str:
    """Render the refusal for directives an edit adds.

    Returns:
        the report block, naming each directive and the enumerable relief.

    """
    listed = "".join(f"\n  {path}: adds `# {d}`" for d in new)
    return (
        f"--- suppression ---{listed}\n"
        "  ⚑ THIS EDIT ADDS A LINE-SCOPED SUPPRESSION, which silences the finding rather than\n"
        "  answering it — and a directive travels with the code into trees that may not share\n"
        "  this config.\n" + RELIEF
    )

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Split YAML frontmatter from a markdown body — frontmatter is DATA, not prose.

⚑⚑⚑ PANDOC ATE THE FRONTMATTER AND BOTH GATES PASSED THE WRITE. Converting a document dropped
`name:`, `type:`, `originSessionId:`, `modified:` — its IDENTITY and provenance — while a
round-trip check reported success and called the drift *"expected, not a failure"*. Pandoc parses
frontmatter as metadata and only re-emits it when asked with `--standalone`, and its YAML
round-trip is its own normalization anyway.

⚑⚑ THE FIX IS TO NOT HAND IT OVER. Frontmatter is a different language sharing a file with
markdown, and the prose writer has no business reformatting it. Splitting at the ONE conversion
point every caller routes through means every mode gains preservation at once, rather than each
one remembering to re-attach.

⚑ THIS IS THE BOTTOM OF THE STACK: no dependencies, so every other module can reach it.

⚑ A `+++` (TOML) DOCUMENT NEVER SPLITS, AND THAT ASYMMETRY IS RECORDED RATHER THAN FIXED. The
fence recognised is `---` only, so a TOML-fenced document is passed through whole — which is why
the same mode succeeded on it while failing on YAML-fenced files, an inconsistency a downstream
consumer surfaced while diagnosing the re-attach defect.
"""

from __future__ import annotations

# The fence a YAML frontmatter block opens with. ⚑ THE OPENING FORM CARRIES ITS NEWLINE so a
# document beginning with a horizontal rule is not mistaken for frontmatter.
OPEN_FENCE = "---\n"

# The closing fence, searched for after the opening one.
CLOSE_FENCE = "\n---\n"


def split(src: str) -> tuple[str, str]:
    """Return `(frontmatter_or_empty, body)`.

    ⚑ AN UNTERMINATED FENCE IS NOT FRONTMATTER. A document that opens `---` and never closes it
    is markdown whose first line is a rule; treating the whole file as metadata would hand the
    body to no writer at all.

    Returns:
        `(frontmatter_or_empty, body)`.

    """
    if not src.startswith(OPEN_FENCE):
        return "", src
    end = src.find(CLOSE_FENCE, len(OPEN_FENCE) - 1)
    if end == -1:
        return "", src
    cut = end + len(CLOSE_FENCE)
    return src[:cut], src[cut:]

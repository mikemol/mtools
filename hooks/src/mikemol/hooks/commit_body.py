# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A commit body is plain text: the trailers are the tool's, never the caller's (mtools:W1273).

⚑ `mikemol-commit` WRITES TWO TRAILERS ITSELF, the `Waypoint:` line and the co-author line
(`commit_kata.message_of`). A caller that also puts either in `--body` (or in a stack file's body)
gets it TWICE: measured on 2026-10-15, every commit made by one session carried its `Co-Authored-By`
line in the body and again as the tool's own trailer. The rule used to live in a tick prompt, where
nothing enforced it; this is the check, run where the body enters, so the prompt can drop the rule.

⚑ A REFUSAL, NOT A QUIET REPAIR: stripping the line would hide that the caller misunderstood the
tool, and the next caller would repeat it. The message names the two trailers the tool adds.
"""

from __future__ import annotations

_OWNED = ("waypoint:", "co-authored-by:")


def refusal(body: str) -> str | None:
    """Say why a commit body may not be used, if it may not.

    Returns:
        the reason when any line of the body starts with a trailer the tool adds itself
        (`Waypoint:` or `Co-Authored-By:`, any case, after leading space), else None.

    """
    for number, line in enumerate(body.splitlines(), start=1):
        if line.strip().lower().startswith(_OWNED):
            word = line.strip().split(":", 1)[0]
            return (
                f"the body's line {number} is a {word} trailer: mikemol-commit adds the Waypoint "
                "and Co-Authored-By trailers itself, so a body carrying either has it twice"
            )
    return None

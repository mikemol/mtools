# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Say why a stack is refused for sharing files with a stack ahead, and how to build it right.

W2078, the wording half: `stackahead.unbuilt_on` names the files a stack shares with a live stack
ahead but does not carry the same bytes of. This turns those paths into the refusal a submit
prints, and nothing else: no filesystem, no git, no queue. It is a pure function so the submit
hook that calls it (`commit_kata.submit_problem`, a live hook at its complexity limits) gains one
call and no logic.

⚑ A REFUSAL NAMES THE PATHS AND THE WAY OUT. The paths are sorted and capped (a registry-heavy
stack can share dozens; the first few are enough to find the cause and the count says how many are
hidden). The way out is the remedy W2103 built: rebuild the stack in a scratch worktree on the
stack ahead's frozen files and submit it with `--freeze-from DIR`, so its bytes ARE the stack
ahead's plus its own change.

⚑ NO PATHS IS NO REFUSAL: an empty list returns None, never an empty message, so a caller cannot
refuse on a falsy-but-present string.

CONSUMED BY: `commit_kata.submit_problem` (not yet wired).
"""

from collections.abc import Sequence

SHOWN = 5
ESCAPE = (
    "rebuild it in a scratch worktree on the stack ahead's frozen files and submit it with "
    "--freeze-from DIR (mikemol-scratch open, then mikemol-commit REPO --stack FILE "
    "--freeze-from DIR)"
)


def refusal(unbuilt: Sequence[str]) -> str | None:
    """Turn the unbuilt shared paths into a submit refusal.

    Returns:
        the refusal naming up to SHOWN paths, how many more there are and the way out; None when
        no path is unbuilt.

    """
    if not unbuilt:
        return None
    shown = sorted(unbuilt)[:SHOWN]
    hidden = len(unbuilt) - len(shown)
    more = f" and {hidden} more" if hidden else ""
    return (
        f"this stack shares {len(unbuilt)} file(s) with a stack ahead without being built on its "
        f"bytes: {', '.join(shown)}{more}; {ESCAPE}"
    )

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit REPO --stack FILE --freeze-from DIR`: freeze a stack from a scratch tree (W2103).

⚑ THE FILES A STACK FREEZES AT SUBMIT COME FROM THE MAIN TREE, so a stack built on a queued stack's
files had to be built there, beside the carrier's uncommitted bytes (luthen-observability:W1831, the
incident github:W90: a host-read file carried in the main tree through a check-then-use race).
`--freeze-from DIR` takes the bytes from DIR, a scratch worktree of the same repository, while the
queue, the lease and the ledger stay the main repository's. A submission is still a (base, tree)
pair: the tree is whatever DIR holds at submit, the base is the repository's HEAD.

⚑ DIR MUST BE THE SAME REPOSITORY, judged by git's common directory (a linked worktree shares its
main's). Any other directory would put files from an unrelated tree into this repository's object
store and land them: `refusal` is the check, and it takes the two common directories as values so
the judgement is pure.

⚑ THE PARSE IS ONLY THE FORM `REPO --stack FILE --freeze-from DIR`; any other arrangement of the
flag is not recognised as this form and is left to the commit's own usage error.

CONSUMED BY: nothing yet (`commit_kata`, in the stack after this module is in the venv).
"""

from collections.abc import Sequence
from pathlib import Path

FLAG = "--freeze-from"
_FORM_PLAIN = 3
_FORM_FROM = 5


def parse(args: Sequence[str]) -> Path | None:
    """Read the directory of `REPO --stack FILE --freeze-from DIR`.

    Returns:
        DIR, or None when the arguments are not exactly that five-word form.

    """
    if len(args) == _FORM_FROM and args[1] == "--stack" and args[3] == FLAG:
        return Path(args[4])
    return None


def form_is_stack(args: Sequence[str]) -> bool:
    """Say whether the arguments are `REPO --stack FILE`, with or without `--freeze-from DIR`.

    Returns:
        True for either stack form.

    """
    if len(args) == _FORM_PLAIN:
        return args[1] == "--stack"
    return parse(args) is not None


def refusal(repo_common: Path | None, dir_common: Path | None, given: Path) -> str | None:
    """Judge a `--freeze-from` directory by the git common directory it shares with the repository.

    Returns:
        the refusal text naming the directory, or None when both common directories are known and
        are the same.

    """
    if repo_common is None or dir_common is None:
        return f"NOT COMMITTED: --freeze-from {given} is not a directory git can read (W2103)"
    if repo_common.resolve() != dir_common.resolve():
        return (
            f"NOT COMMITTED: --freeze-from {given} belongs to another repository "
            f"({dir_common}), not this one ({repo_common}) (W2103)"
        )
    return None

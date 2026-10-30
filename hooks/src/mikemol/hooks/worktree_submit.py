# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An undeclared linked-worktree submit is refused, and every one leaves a durable mark (W2103).

⚑ THE MEASURED HAZARD (github-8f, 2026-10-28, a toy repository): `mikemol-commit <linked worktree>
--stack B.json` was NOT refused. `commit_kata.ledger_of` names `<git dir>/mtools`, and the git dir
of a linked worktree is `<main>/.git/worktrees/<name>`, so the submit took the WORKTREE's own lease
and queue: a second queue, a second lease, two gates side by side, landing on the worktree's HEAD,
while the main ledger showed only the first. Loop prompt line 40 reads as if a worktree submit were
queued behind main's; it is not.

⚑ ONLY THE IMPLICIT CASE IS REFUSED (the operator's constraint, relayed by github-8f): a session
that submits from a linked worktree WITHOUT SAYING SO, believing it queued behind main. A later
DECLARED queue mode (a per-branch queue that merges upward) is an added flag, not a redesign:
`refusal` takes the declared modes as a closed list, and today it holds none.

⚑ THE MARK IS WRITTEN TO THE MAIN REPOSITORY, NOT THE WORKTREE: `git worktree remove` deletes
`<git dir>/worktrees/<name>`, so a mark kept there is gone when the worktree is, and a host could
not read a split queue after the fact. Every worktree submit, refused or declared, appends one line
to `<main git dir>/mtools/worktree-submits.log`.

⚑ PURE ON PATHS: whether a git dir belongs to a linked worktree is read from its SHAPE
(`.../worktrees/<name>`), never from a file; only `append` touches the disk.

CONSUMED BY: nothing yet (`commit_kata`'s submit, in the stack after this module is in the venv).
"""

from pathlib import Path

DECLARED_MODES: tuple[str, ...] = ()
LOG_NAME = "worktree-submits.log"
REFUSED = "refused"


def main_git_dir(git_dir: Path) -> Path | None:
    """Find the main repository's git directory from a worktree's.

    Returns:
        `<main>/.git` when `git_dir` is `<main>/.git/worktrees/<name>`; None for any other shape
        (a main checkout, a bare repository).

    """
    return git_dir.parent.parent if git_dir.parent.name == "worktrees" else None


def refusal(name: str, git_dir: Path, mode: str = "") -> str | None:
    """Judge a submit by the git directory it would take its queue and lease from.

    Returns:
        the refusal text naming the main repository and W2103; None for a main checkout or a
        worktree that declares one of `DECLARED_MODES`.

    """
    main = main_git_dir(git_dir)
    if main is None or (mode and mode in DECLARED_MODES):
        return None
    return (
        f"NOT COMMITTED: {name} is a linked worktree of {main.parent}, and an undeclared worktree "
        "submit would take its own queue and lease beside main's (mtools:W2103). Submit from "
        f"{main.parent}, or build the stack there; no per-worktree queue mode is declared yet"
    )


def record(stamp: str, name: str, git_dir: Path, verdict: str) -> tuple[Path, str] | None:
    """Make the durable line for a worktree submit and the main-repository file it goes to.

    Returns:
        the log path and the line (`<stamp> <verdict> <name> <git dir>`), or None when the git
        directory is not a linked worktree's.

    """
    main = main_git_dir(git_dir)
    if main is None:
        return None
    return main / "mtools" / LOG_NAME, f"{stamp} {verdict} {name} {git_dir}\n"


def append(path: Path, line: str) -> None:
    """Append one line to the log, making its directory when it is not there yet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log:
        log.write(line)

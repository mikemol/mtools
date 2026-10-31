# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W2104 (github-8f, W2174): map each dirty path of a repository to what carries it.

    PATH carrier=stack:KEY | scratch:NAME | excepted:queue | excepted:inbox | NONE
    # N dirty, C carried, E excepted, O only in main

⚑ THE MAIN TREE IS NOT A STORE OF PENDING WORK: each card's work lives in its OWN scratch tree and
main converges to HEAD plus what queued stacks carry (github-8f, 2026-10-28, who read 103 dirty
paths of which 55 were carried by nothing). A dirty path with no carrier exists ONLY in main, and
a crash or a clean-up loses it. This module makes "only in main" a number with a trend, so the
host can read it every tick for every repository.

⚑ CARRIED MEANS THE SAME PATH IS HELD ELSEWHERE, not that the bytes match: a live stack's frozen
paths and a scratch tree's dirty paths are the two carriers. A stack is named before a scratch
tree when both hold the path, because a submitted stack is the one that lands.

⚑ TWO KINDS ARE EXCEPTED BY NAME, never counted as only-in-main: the queue files (read from main at
land time, so main is their home) and the archived peer letters under `inbox/`.

This is the pure half. Reading the dirty paths (`git status`), the live stacks' frozen paths and the
scratch trees' dirty paths is a thin reader that calls `carrier_lines` with three plain values.
"""

from collections.abc import Collection, Mapping, Sequence

QUEUE_FILES = frozenset(
    {
        ".claude/paths-forward.json",
        ".claude/paths-forward.ledger",
        ".claude/paths-forward.md",
        ".claude/paths-forward.export.json",
    }
)
INBOX = "inbox/"
_RENAME = " -> "
_STATUS_WIDTH = 3


def dirty_paths(porcelain: str) -> list[str]:
    """Read the paths out of `git status --porcelain=v1` text.

    Returns:
        each changed path, in the order git printed them; a rename names its new path.

    """
    paths: list[str] = []
    for line in porcelain.splitlines():
        if len(line) <= _STATUS_WIDTH:
            continue
        body = line[_STATUS_WIDTH:]
        paths.append(body.split(_RENAME)[-1])
    return paths


def carrier_of(
    path: str,
    stacks: Mapping[str, Collection[str]],
    scratch: Mapping[str, Collection[str]],
) -> str:
    """Name what carries one dirty path.

    Returns:
        `stack:KEY`, else `scratch:NAME`, else `excepted:queue` or `excepted:inbox`, else `NONE`.

    """
    for key in sorted(stacks):
        if path in stacks[key]:
            return f"stack:{key}"
    for name in sorted(scratch):
        if path in scratch[name]:
            return f"scratch:{name}"
    if path in QUEUE_FILES:
        return "excepted:queue"
    return "excepted:inbox" if path.startswith(INBOX) else "NONE"


def carrier_lines(
    dirty: Sequence[str],
    stacks: Mapping[str, Collection[str]],
    scratch: Mapping[str, Collection[str]],
) -> list[str]:
    """Render each dirty path with its carrier, then the count line.

    Returns:
        `PATH carrier=...` per dirty path, then `# N dirty, C carried, E excepted, O only in main`.

    """
    carriers = [carrier_of(path, stacks, scratch) for path in dirty]
    rows = [f"{path} carrier={carrier}" for path, carrier in zip(dirty, carriers, strict=True)]
    carried = sum(1 for c in carriers if c.startswith(("stack:", "scratch:")))
    excepted = sum(1 for c in carriers if c.startswith("excepted:"))
    only = sum(1 for c in carriers if c == "NONE")
    count = f"# {len(dirty)} dirty, {carried} carried, {excepted} excepted, {only} only in main"
    return [*rows, count]

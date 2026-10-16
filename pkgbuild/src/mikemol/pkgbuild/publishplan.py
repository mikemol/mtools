# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Print the release steps for one publish card, each as the exact command to run (W1238, W803).

    mikemol-wheel publish-plan STATE SHA INDEX [--card WN]

The operator's ruling (2026-10-09): a release mints a fresh `publish` waypoint, the build's version
is `0.0.<that card's number>`, the card is done when the upload succeeds, and the commit is tagged
`v0.0.N` as the record. This prints those steps with the number filled in, so none is typed.

⚑ NOTHING IS RUN OR WRITTEN: minting the card, the dispatch and the tag are the operator's (or a
later, authorised verb's) acts. Without `--card` the number shown is the next the queue's counter
would issue and the plan says to mint first, because a card minted in between would move it; with
`--card W<n>` the number is that card's, and it must be a number the queue has already issued.

CONSUMED BY: `mikemol-wheel publish-plan`, the operator's release step (W1153, W1152).
"""

import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

USAGE = 2
ARGC = 3
INDEXES = ("testpypi", "pypi")
SHA = re.compile(r"[0-9a-f]{7,40}")
CARD = re.compile(r"W(\d+)")
PF = "mikemol-paths-forward --state .claude/paths-forward.json"
SYNOPSIS = "usage: mikemol-wheel publish-plan STATE SHA testpypi|pypi [--card WN]\n"


def counter_of(state: Path) -> int | None:
    """Read the queue's counter: the number of the last waypoint issued.

    Returns:
        the counter, or None when the file is unreadable or has no integer counter.

    """
    try:
        table = cast("dict[str, object]", json.loads(state.read_text(encoding="utf-8")))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    value = table.get("counter")
    return value if isinstance(value, int) else None


def steps(sha: str, index: str, number: int, minted: bool) -> list[str]:
    """Write the plan for one release.

    Returns:
        the lines: the card, the build check, the dispatch and the tag, each as a command.

    """
    version = f"0.0.{number}"
    if minted:
        mint = f"1. publish card W{number} exists; its number is the version."
    else:
        first = f"1. MINT FIRST (W{number} only if nothing else is minted):"
        mint = f'{first} {PF} --add "publish {version}"'
    check = f"python -m mikemol.pkgbuild.wheel release-check . {sha} out --version {version}"
    tag = f"git tag v{version} {sha} && git push origin v{version}"
    return [
        f"release {version} at {sha} to {index}",
        mint,
        f"2. check: {check}",
        f"3. dispatch: gh workflow run publish.yml -f index={index} -f version={version}",
        f"4. on success mark W{number} done, then: {tag}",
        "   a failed upload leaves the card open as evidence; a retry mints a higher number.",
    ]


def run(args: Sequence[str]) -> int:
    """Run `STATE SHA INDEX [--card WN]`: print the plan.

    Returns:
        0, or 2 for a usage error, an unreadable queue, a card the queue has not issued, or a
        sha or index that is not one.

    """
    words = list(args)
    card = None
    if "--card" in words:
        place = words.index("--card")
        card = CARD.fullmatch(words[place + 1]) if place + 1 < len(words) else None
        if card is None:
            sys.stderr.write(SYNOPSIS)
            return USAGE
        del words[place : place + 2]
    if len(words) != ARGC or words[2] not in INDEXES or not SHA.fullmatch(words[1]):
        sys.stderr.write(SYNOPSIS)
        return USAGE
    counter = counter_of(Path(words[0]))
    if counter is None:
        sys.stderr.write(f"publish-plan: no queue counter in {words[0]}\n")
        return USAGE
    number = int(card.group(1)) if card else counter + 1
    if card is not None and number > counter:
        sys.stderr.write(f"publish-plan: W{number} is not issued (the counter is {counter})\n")
        return USAGE
    plan = steps(words[1], words[2], number, minted=card is not None)
    sys.stdout.writelines(line + "\n" for line in plan)
    return 0

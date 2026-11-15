# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The dry run comparing stored RRULEs with a reference parser across the fleet's queues (W1259).

`recurrence.check` reads a rule by its own grammar and standard library only. This reads every
workstream's queue under a root, READ-ONLY, hands each stored rule to `recurrence.disagreements`
with a reference parser the CALLER supplies (python-dateutil's `rrulestr` as a dev-only oracle,
never imported here), and says one line per rule the two read differently.

⚑ READ-ONLY, AND UNREADABLE IS NOT A FINDING: a queue that is missing, unreadable or not an object
contributes no rules and no line, so a broken neighbour cannot make the audit report a difference
that is only a missing file. Nothing is written anywhere.

CONSUMED BY: nothing yet; the dry-run mode of the CLI calls it once the oracle is wired (W1259).
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

from mikemol.pathsforward import recurrence

QUEUE = Path(".claude") / "paths-forward.json"


def _queue(repo: Path) -> object:
    """Read one workstream's queue document.

    Returns:
        the decoded document; None when it is missing or unreadable.

    """
    try:
        return cast("object", json.loads((repo / QUEUE).read_text(encoding="utf-8")))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None


def audit(root: Path, reference: Callable[[str], bool]) -> list[str]:
    """Compare every stored RRULE under `root` with a reference parser's reading.

    Args:
        root: the directory holding the workstreams, one subdirectory each.
        reference: whether a real parser accepts a rule.

    Returns:
        `<repo>:<symbol> <rule>: <who accepts>` for each disagreement, repos in name order and
        rules in queue order; empty when the readers agree on every rule.

    """
    found: list[str] = []
    for repo in sorted(path for path in root.iterdir() if path.is_dir()):
        found.extend(
            f"{repo.name}:{symbol} {line}"
            for symbol, rule in recurrence.rules_of(_queue(repo))
            for line in recurrence.disagreements([rule], reference)
        )
    return found

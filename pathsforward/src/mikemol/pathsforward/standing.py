# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The standing rules, read back: `--standing` and `--tick-open` print them (W1470).

The list had a writer (`--standing-set`, W862) and no reader but the payload, so a session that
wanted this repo's rules grepped the JSON for them, the mode the fleet's no-grep rule forbids. The
loop prompt says repo-specific rules live in the queue, and a tick that opens without reading them
reads them from recall.

⚑ ONE LINE PER RULE, NUMBERED, SO A CALLER CAN CITE `standing 4`: the number is a position in the
list as it stands and moves when a rule is retired, the way the payload's own order does.
"""

from mikemol.pathsforward.model import Json, strlist

KEY = "standing"
NONE_LINE = "standing: none stored (set them with --standing-set FILE)"


def rules(doc: Json) -> list[str]:
    """Read the stored standing rules.

    Returns:
        the rules in stored order; [] when the list is absent.

    """
    return strlist(doc, KEY)


def lines(doc: Json) -> list[str]:
    """Render the standing rules, one numbered line each.

    Returns:
        `standing N: <rule>` per rule, or the one line saying none are stored.

    """
    stored = rules(doc)
    if not stored:
        return [NONE_LINE]
    return [f"standing {number}: {rule}" for number, rule in enumerate(stored, start=1)]

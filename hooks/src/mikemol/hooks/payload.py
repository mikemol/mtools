# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the harness's untyped payload, and report whether the hook is armed.

⚑ A HOOK THAT MIS-READS ITS OWN INPUT RENDERS A VERDICT ABOUT SOMETHING OTHER THAN WHAT RAN,
which is why this is its own responsibility: it changes when the HARNESS's contract changes, not
when a checker, a message or a verdict does.

⚑ NO SHEBANG — THIS IS AN IMPORTED MODULE, NOT A SCRIPT. The origin tree kept these as files in a
`scripts/` directory, so every one carried a shebang and an exe bit; as package modules they are
imported, and the linter says so.
"""

from __future__ import annotations

import os

# ⚑ THE HOOK'S OWN SWITCH, CHECKED FIRST. A shared switch alone cannot arm one hook without
# arming its siblings, and a repo adopting this may want exactly one of them refusing.
OWN_SWITCH = "PYCHECK_HOOK_BLOCK"

# The switch every hook in this package honours when its own is unset.
SHARED_SWITCH = "STRUCT_HOOK_BLOCK"


def as_record(value: object) -> dict[str, object]:
    """Return `value` as a string-keyed record, or an empty one if not a mapping.

    ⚑⚑ `object` IS THE HONEST TYPE OF AN UNTRUSTED VALUE; `Any` IS THE DISHONEST ONE. The payload
    arrives as untyped JSON; rebuilding the mapping with a declared return type forces its values
    to `object`, and every read is then narrowed with a real runtime `isinstance` at the use
    site — a CHECK, not an assertion. `isinstance(x, dict)` alone narrows to `dict[Any, Any]`, so
    every read through it inherits the `Any` a strict bar exists to refuse.
    """
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in value.items()}


def text_of(value: object) -> str:
    """Return `value` when it is a string, else an empty string."""
    return value if isinstance(value, str) else ""


def armed() -> bool:
    """Report whether this hook is set to DENY — own switch first, then the shared one.

    ⚑⚑ ARMED ON THE COMMAND LINE, NOT BY AN ENVIRONMENT BLOCK ALONE. A session already running
    when its settings change never re-reads them, so a hook armed only in a settings env block
    keeps exiting 0 — detecting every violation and reporting none, **reading as armed in review
    and off in fact**. Set the switch inline in the command string. Two independent adopters
    volunteered this trap.
    """
    own = os.environ.get(OWN_SWITCH)
    if own is not None:
        return own == "1"
    return os.environ.get(SHARED_SWITCH) == "1"

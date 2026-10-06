# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""PostToolUse(Edit|Write): say which imports of the edited `.py` file are not clean (W818).

⚑ AFTER THE EDIT, NOT INSIDE THE GATE. The edit gate (`pycheck`) judges one file and its contract
is unchanged; it admitted this edit or it would not have landed. This hook runs once the write is
on disk and adds context only, so it can never refuse, never delays the decision, and a gap in it
(no ledger, no planner, an unreadable plan) is silence. The advice itself is `pycheck_closure`.

⚑ THERE IS NO ARMING SWITCH BECAUSE THERE IS NOTHING TO ARM: it blocks nothing. A payload that is
not a Python edit, or that names no file, says nothing at all.

CONSUMED BY: the `mikemol-hook-pycheck-advise` console script.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import project_root, pycheck_closure
from mikemol.hooks.payload import as_record, text_of

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import TextIO

EDIT_TOOLS = frozenset(("Write", "Edit"))
PY_SUFFIX = ".py"


def run(
    record: Mapping[str, object],
    env: Mapping[str, str],
    plan: Callable[[Sequence[str]], str | None],
    out: TextIO,
) -> int:
    """Print the closure advisory for an edited Python file, if there is one.

    Returns:
        0 always: a context hook never decides.

    """
    if text_of(record.get("tool_name")) not in EDIT_TOOLS:
        return 0
    path = text_of(as_record(record.get("tool_input")).get("file_path"))
    if not path.endswith(PY_SUFFIX) or not Path(path).is_file():
        return 0
    root = project_root.project_for(path)
    if root is None:
        return 0
    text = pycheck_closure.context_for(path, root, env, plan)
    if text is None:
        return 0
    decision = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}
    out.write(json.dumps(decision))
    return 0


def main() -> int:
    """Read the PostToolUse payload on stdin and add the closure advisory.

    An unreadable payload says nothing: a context hook has nothing to refuse.

    Returns:
        the exit code from `run`, or 0.

    """
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        return 0
    return run(as_record(raw), dict(os.environ), pycheck_closure.run_planner, sys.stdout)

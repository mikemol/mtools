# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`annotate`: the `annotating` planner under the shared judge (see `cli_typedargs`).

⚑ DRY RUN FIRST, AND NO JUDGE OF ITS OWN (W1516): the candidate is measured with the project's own
mypy before and after, formatted, written and reported by `cli_typedargs.print_judged`, so a file
is written only with `--write` and only where its findings fall; a file whose count holds or rises
is printed with the reason and never touched. This module reads the observations and hands
`annotating.plan` over, one planner per file.

⚑ THE OBSERVATIONS ARE A FILE: `--seen` is a JSON object of `"<file>::<qualified name>"` to
`{"params": {name: [type, ...]}, "returns": [type, ...]}`, what `observed.Observer` collected, so
a run's tracing and this judging are two steps and neither starts a process of the other's.

    mikemol-pycodemod annotate --root PROJECT --seen seen.json [--write] FILE...
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.pycodemod import annotating
from mikemol.pycodemod.cli_typedargs import (
    Plan,
    Planner,
    Runner,
    TypedArgsFlags,
    print_judged,
    run_tool,
)
from mikemol.pycodemod.observed import Signature

LABEL = "annotate"
SEPARATOR = "::"
READ_FAILED = 2


@dataclass(frozen=True, slots=True)
class AnnotateFlags:
    """What `annotate` was asked: the project to judge in, write or not, the observations file."""

    root: str
    write: bool
    seen: str


def signatures_for(seen: Mapping[str, object], name: str) -> dict[str, Signature]:
    """Pick one file's observations out of the whole document.

    Returns:
        the signatures by qualified name for entries whose file is `name`.

    """
    out: dict[str, Signature] = {}
    for key, body in seen.items():
        file, _, qual = key.partition(SEPARATOR)
        if file != name or not isinstance(body, dict):
            continue
        record = cast("dict[str, object]", body)
        params = cast("dict[str, list[str]]", record.get("params", {}))
        returns = cast("list[str]", record.get("returns", []))
        out[qual] = Signature({p: set(types) for p, types in params.items()}, set(returns))
    return out


def _planner(known: dict[str, Signature]) -> Planner:
    def planner(text: str) -> Plan:
        planned = annotating.plan(text, known)
        return Plan(planned.text, planned.sites, tuple((0, w, why) for w, why in planned.worklist))

    return planner


def print_annotate(paths: Sequence[str], flags: AnnotateFlags, run: Runner = run_tool) -> int:
    """Run `annotate` over files under the shared judge.

    Returns:
        the exit code `print_judged` computed, or 2 when the observations cannot be read.

    """
    try:
        loaded = cast("object", json.loads(Path(flags.seen).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return READ_FAILED
    if not isinstance(loaded, dict):
        return READ_FAILED
    seen = cast("dict[str, object]", loaded)
    shared = TypedArgsFlags(root=flags.root, write=flags.write)
    code = 0
    for name in paths:
        plan = (LABEL, _planner(signatures_for(seen, name)))
        code = max(code, print_judged([name], shared, plan, run))
    return code

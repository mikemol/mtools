# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a mypy baseline kept as one file per module and merge it into the one object (W2190).

⚑ WHY (github:R212, nemik:W1280, mtools:W2186): every mypy stack rewrites the ONE
`mypy-baseline.json`, which freezes whole, so no mypy stack can queue behind another. A baseline
kept as a directory of per-module files, `mypy-baseline.d/<module>.json`, makes module slices touch
disjoint files. The shape does not change: keys are already per file, each part is the same
`{file: {rule: count}}` object, and the merge is their union, so the ratchet's VALUE stays the one
sum nemik's arithmetic needs (rule 1 of its ruling).

⚑ A FILE KEY IN TWO PARTS IS REFUSED, NOT MERGED: the same source file counted by two modules'
baselines would be a count nobody can lower honestly. An unreadable part, a part that is not a
JSON object, and a directory with no part at all each read as NO baseline (the caller says
`none judged`), never as an empty one: a missing baseline is not a clean one.

CONSUMED BY: nothing yet (`pycheck_ratchet_run.disk` for the path `mypy-baseline.json`, when
`mypy-baseline.d` exists beside it, in the stack after this module is in the venv: `mikemol-pycheck`
is the edit gate, so an import of a module the venv lacks would refuse every edit). The writer for
this layout is W2191.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

DIR = "mypy-baseline.d"


def merge(parts: Sequence[tuple[str, str]]) -> str | None:
    """Union per-module baseline parts, each a `(name, JSON text)` pair, into one baseline text.

    Returns:
        the merged `{file: {rule: count}}` as sorted JSON, or None when there is no part, a part
        is not a JSON object, or a file key appears in two parts.

    """
    merged: dict[str, object] = {}
    for _name, text in parts:
        try:
            part: object = json.loads(text)
        except ValueError:
            return None
        if not isinstance(part, dict):
            return None
        for key, counts in cast("dict[str, object]", part).items():
            if key in merged:
                return None
            merged[key] = counts
    return json.dumps(merged, sort_keys=True) if parts else None


def parts(directory: Path) -> list[tuple[str, str]] | None:
    """Read every `*.json` of a baseline directory in name order.

    Returns:
        the `(name, text)` pairs, or None when a part cannot be read.

    """
    try:
        return [
            (path.name, path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("*.json"))
        ]
    except OSError:
        return None


def read(directory: Path) -> str | None:
    """Read every `*.json` of a baseline directory in name order and merge them.

    Returns:
        the merged text (`merge`), or None when a part cannot be read.

    """
    found = parts(directory)
    return None if found is None else merge(found)


def lowered[V](found: Sequence[tuple[str, str]], now: Mapping[str, V]) -> dict[str, dict[str, V]]:
    """Name the parts whose counts changed, each with its new contents (W2191).

    ⚑ ONLY A PART THAT CHANGED IS REWRITTEN: a part keeps exactly the file keys it holds, each
    taken from today's counts, and a key whose file no longer has a finding drops out. A key
    today's counts hold that no part holds is a RISE and the caller has refused it already, so
    it is never added here. A part that did not change is left out, so two stacks lowering
    different modules write disjoint files.

    Returns:
        part name to its new `{file: counts}` object, for the changed parts only; a part
        that does not parse is left alone.

    """
    changed: dict[str, dict[str, V]] = {}
    for name, text in found:
        try:
            old: object = json.loads(text)
        except ValueError:
            continue
        if not isinstance(old, dict):
            continue
        keep = {key: now[key] for key in cast("dict[str, object]", old) if key in now}
        if keep != old:
            changed[name] = keep
    return changed

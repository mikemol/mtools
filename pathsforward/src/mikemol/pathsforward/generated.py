# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A repo's generated files, which no card holds a lease on (W1468, el-openglo via github-8f).

⚑ A GENERATED FILE IS NOT AN EXCLUSIVE WRITE. el-openglo's port cards each declare `closures.bzl`
for write and the file is regenerated at the tip of every stack, so one working card holding its
lease refused W587 to W590 ("W586 holds it") although no two of them write different bytes into it.
The repo lists such files in `.claude/generated.json`, the file nemik's stack planner reads for the
same reason (`{"generated": [{"path": "<repo-relative path>"}]}`), and a `file:` tag naming one is
left out of the lease.

⚑ AN ABSENT OR MALFORMED LIST MEANS NONE: the lease is only ever relaxed by a list that parses, so a
broken file can never silently exempt anything.
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from mikemol.pathsforward.tags import parse_tag

FILE = ".claude/generated.json"


def paths(root: Path) -> frozenset[str]:
    """Read the exact repo-relative paths a repo lists as generated.

    Returns:
        the paths, or none when the file is absent, unreadable or not in the expected shape.

    """
    try:
        doc: object = json.loads((root / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    rows = cast("dict[str, object]", doc).get("generated") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        return frozenset()
    named = [cast("dict[str, object]", row).get("path") for row in rows if isinstance(row, dict)]
    return frozenset(p for p in named if isinstance(p, str))


def leased(tags: Sequence[str], generated: frozenset[str]) -> list[str]:
    """Drop the tags that name a generated file, leaving those a lease may hold.

    Returns:
        the tags in order, without any `file:` tag whose path is generated.

    """
    kept: list[str] = []
    for raw in tags:
        tag = parse_tag(raw)
        if tag.grain == "file" and tag.name in generated:
            continue
        kept.append(raw)
    return kept

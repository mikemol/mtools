# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The PURE predicate: which paths make worktree != index.

Ported from paperkit's `tools/indexdiverge.py` (paperkit:W142), behaviour unchanged. It is the
part of `hook_index` with no I/O and no environment: given a `git status --porcelain=v1 -z`
transcript, decide which paths diverge.

⚑ THE SEPARATION IS REAL, NOT A LINT DODGE. `divergent` is a total function from a string to a
sorted list; everything around it in `hook_index` spawns git, reads the environment and prints
refusals, so a suite can exercise this half over porcelain FIXTURES alone.
"""

from __future__ import annotations

# Each entry is a path PREFIX, and each earns its place by OWNERSHIP: bazel-invisible (zero
# references in any BUILD/bib/bzl) AND index-gated by its own check (cotype-monotone).
ALLOW = ("cotype/",)

_MIN_ENTRY = 4  # "XY path" — two status columns, a space, at least one path character
_ORIGIN_COLUMNS = "RC"  # a rename or copy entry is followed by its origin path field


def divergent(porcelain: str, allow: tuple[str, ...] = ALLOW) -> list[str]:
    """Return the paths where worktree != index (unstaged edits, `??` untracked), outside `allow`.

    Parsed from `git status --porcelain=v1 -z` output: NUL-separated, and a rename entry carries
    a SECOND NUL-terminated origin path which is consumed and ignored: the NEW path is what a
    commit lands, so it is the one that can diverge.

    Returns:
        the divergent paths, sorted.

    """
    out: list[str] = []
    fields = porcelain.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < _MIN_ENTRY:
            continue
        xy, path = entry[:2], entry[3:]
        if xy[0] in _ORIGIN_COLUMNS:
            i += 1  # the rename/copy origin path field
        dirty = xy == "??" or xy[1] != " "  # untracked, or the worktree column is live
        if dirty and not any(path.startswith(a) for a in allow):
            out.append(path)
    return sorted(out)

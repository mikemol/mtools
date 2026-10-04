# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The vfs seam by its old name: one read/write surface over the working tree and git history.

paperkit's `tools/vfs.py` was one module; here it is split by responsibility (`presence`,
`result`, `sources`, `read`, `write`, `listing`, `census`), and this module re-exports the public
names so a caller repoints one import line and nothing else:

    from mikemol.treeio import vfs
    result = vfs.read("agda/Foundation.agda", vfs.Rev("HEAD"))
    if result.presence is vfs.Presence.PRESENT:  use result.data   # bytes, maybe empty
    elif result.presence is vfs.Presence.ABSENT: ...                # legitimately not there
    else:                                        raise result.error # BROKEN: never a miss

One name is deliberately NOT re-exported. `DRY_RUN` is read by `write` at call time from its own
module, so a caller that assigned it here would silently change nothing. Assign
`mikemol.treeio.write.DRY_RUN` instead.
"""

from __future__ import annotations

from mikemol.treeio.census import census, compare
from mikemol.treeio.listing import (
    LISTDIR_ORDER,
    AmbiguousPattern,
    AmbiguousPatternError,
    ambiguous_across_sources,
    listdir,
    suffixed,
)
from mikemol.treeio.presence import Presence
from mikemol.treeio.read import read, read_text
from mikemol.treeio.result import Result
from mikemol.treeio.sources import Rev, WorkingTree
from mikemol.treeio.write import write

__all__ = [
    "LISTDIR_ORDER",
    "AmbiguousPattern",
    "AmbiguousPatternError",
    "Presence",
    "Result",
    "Rev",
    "WorkingTree",
    "ambiguous_across_sources",
    "census",
    "compare",
    "listdir",
    "read",
    "read_text",
    "suffixed",
    "write",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the workstreams under the host root: the directories that carry a paths-forward queue.

Ported from the host katas.py `repos()` (mtools:W796, W872), unchanged in what it answers: a
directory is a workstream when it holds `.claude/paths-forward.json`, and a dot-named directory
(a scratch checkout, a hidden tool tree) is never one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

QUEUE = ".claude/paths-forward.json"
"""Where a workstream's queue lives, relative to its directory."""


def repos(root: Path) -> list[str]:
    """List every workstream directory under `root` that has a queue, sorted.

    Returns:
        the directory names; dot-named directories are left out.

    """
    names = [queue.parent.parent.name for queue in root.glob(f"*/{QUEUE}")]
    return sorted(name for name in names if not name.startswith("."))

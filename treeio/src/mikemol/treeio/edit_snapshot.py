# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The edit-snapshot surface by its old name: guard, snapshot, restore and the contract.

paperkit's `tools/edit_snapshot.py` was one module; here it is split by responsibility (`errors`,
`ambient`, `context`, `layout`, `proc`, `gitrun`, `snapshot`, `restore`, `contract`,
`snapshot_cli`), and this module re-exports the public names so a caller repoints one import line:

    from mikemol.treeio import edit_snapshot as _es
    _es.guard(label, [path], intent="apply")

What it does not carry is the root: paperkit's functions snapshotted the checkout the module sat in,
and these take an optional `root` (the current directory when omitted) where a signature has room
for one. The entry-point form `require_at_entry` always uses the current directory.
"""

from __future__ import annotations

from mikemol.treeio.ambient import (
    SANCTIONED_OVERRIDES,
    Ambient,
    AmbientConflict,
    AmbientConflictError,
)
from mikemol.treeio.context import (
    INTENT,
    SNAPSHOT_STATE,
    TENANT,
    IntentConflict,
    naming_tenant,
    resolve_intent,
    sanctioned_setters,
)
from mikemol.treeio.contract import (
    NEAR_MISS_SPELLINGS,
    cli_main,
    guard,
    require_at_entry,
    require_explicit_mutation,
    snapshot_once,
)
from mikemol.treeio.errors import AmbientVocabError, MutationContractError
from mikemol.treeio.restore import contents, restore
from mikemol.treeio.snapshot import announce, snapshot

__all__ = [
    "INTENT",
    "NEAR_MISS_SPELLINGS",
    "SANCTIONED_OVERRIDES",
    "SNAPSHOT_STATE",
    "TENANT",
    "Ambient",
    "AmbientConflict",
    "AmbientConflictError",
    "AmbientVocabError",
    "IntentConflict",
    "MutationContractError",
    "announce",
    "cli_main",
    "contents",
    "guard",
    "naming_tenant",
    "require_at_entry",
    "require_explicit_mutation",
    "resolve_intent",
    "restore",
    "sanctioned_setters",
    "snapshot",
    "snapshot_once",
]

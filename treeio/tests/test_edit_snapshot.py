# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `edit_snapshot`: the old one-module surface re-exports the split modules."""

from __future__ import annotations

from mikemol.treeio import ambient, context, contract, edit_snapshot, errors, restore, snapshot

_EXPORTED = [
    "AmbientConflict",
    "AmbientConflictError",
    "AmbientVocabError",
    "Ambient",
    "INTENT",
    "IntentConflict",
    "MutationContractError",
    "NEAR_MISS_SPELLINGS",
    "SANCTIONED_OVERRIDES",
    "SNAPSHOT_STATE",
    "TENANT",
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


def test_every_exported_name_is_the_split_modules_own_object() -> None:
    """A repointed caller gets the very objects, not copies, so except clauses agree."""
    assert edit_snapshot.MutationContractError is errors.MutationContractError
    assert edit_snapshot.AmbientVocabError is errors.AmbientVocabError
    assert edit_snapshot.Ambient is ambient.Ambient
    assert edit_snapshot.AmbientConflict is ambient.AmbientConflictError
    assert edit_snapshot.AmbientConflictError is ambient.AmbientConflictError
    assert edit_snapshot.IntentConflict is ambient.AmbientConflictError
    assert edit_snapshot.SANCTIONED_OVERRIDES is ambient.SANCTIONED_OVERRIDES
    assert edit_snapshot.INTENT is context.INTENT
    assert edit_snapshot.TENANT is context.TENANT
    assert edit_snapshot.SNAPSHOT_STATE is context.SNAPSHOT_STATE
    assert edit_snapshot.naming_tenant is context.naming_tenant
    assert edit_snapshot.resolve_intent is context.resolve_intent
    assert edit_snapshot.sanctioned_setters is context.sanctioned_setters
    assert edit_snapshot.NEAR_MISS_SPELLINGS is contract.NEAR_MISS_SPELLINGS
    assert edit_snapshot.cli_main is contract.cli_main
    assert edit_snapshot.guard is contract.guard
    assert edit_snapshot.require_at_entry is contract.require_at_entry
    assert edit_snapshot.require_explicit_mutation is contract.require_explicit_mutation
    assert edit_snapshot.snapshot_once is contract.snapshot_once
    assert edit_snapshot.snapshot is snapshot.snapshot
    assert edit_snapshot.announce is snapshot.announce
    assert edit_snapshot.contents is restore.contents
    assert edit_snapshot.restore is restore.restore


def test_all_lists_exactly_the_exported_names() -> None:
    """The public surface is the list, with no stray helper in it."""
    assert sorted(edit_snapshot.__all__) == sorted(_EXPORTED)

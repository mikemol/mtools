# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `indexdiverge`: which paths a `git status -z` transcript says differ."""

from __future__ import annotations

from mikemol.gatecheck import indexdiverge


def test_unstaged_and_untracked_paths_diverge_and_come_back_sorted() -> None:
    """A live worktree column and a `??` entry are both divergent, returned in sorted order."""
    got = indexdiverge.divergent(" M zeta.py\0?? alpha.py\0MM mid.py\0")
    assert got == ["alpha.py", "mid.py", "zeta.py"]


def test_a_fully_staged_path_does_not_diverge() -> None:
    """`M ` and `A ` have a blank worktree column: the index already holds the bytes."""
    assert indexdiverge.divergent("M  staged.py\0A  added.py\0") == []


def test_the_default_allowlist_excuses_cotype_and_nothing_else() -> None:
    """A dirty path under `cotype/` is excused; the same dirt elsewhere is not."""
    assert indexdiverge.ALLOW == ("cotype/",)
    assert indexdiverge.divergent(" M cotype/ledger.md\0 M cotypes/x.py\0") == ["cotypes/x.py"]


def test_an_explicit_allowlist_replaces_the_default() -> None:
    """The `allow` argument is the whole allowlist: the default does not stay in force."""
    got = indexdiverge.divergent(" M docs/a.md\0 M cotype/b.md\0", allow=("docs/",))
    assert got == ["cotype/b.md"]


def test_a_rename_origin_field_is_consumed_and_never_reported() -> None:
    """A rename's NEW path lands; its origin field is skipped, not parsed as an entry."""
    assert indexdiverge.divergent("R  new.py\0 M old.py\0 M next.py\0") == ["next.py"]
    assert indexdiverge.divergent("RM new.py\0old.py\0") == ["new.py"]


def test_a_copy_origin_field_is_consumed_too() -> None:
    """`C` carries an origin path exactly as `R` does."""
    assert indexdiverge.divergent("C  copy.py\0?? hidden.py\0 M tail.py\0") == ["tail.py"]


def test_short_fields_and_empty_input_are_ignored() -> None:
    """The trailing empty field of a NUL-terminated transcript, and a field under 4 chars, skip."""
    assert indexdiverge.divergent("") == []
    assert indexdiverge.divergent(" M\0M a\0") == []
    assert indexdiverge.divergent(" M a\0") == ["a"]

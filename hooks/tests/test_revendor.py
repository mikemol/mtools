# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pure parts of re-vendoring the mtools wheels at one commit.

W989. ⚑ THE MOVED PAIR IS THE POSITIVE CONTROL: the refusals (a short sha, a pyproject without the
marker, a wheel that is not ours) only mean something beside a source line that does move.
"""

from __future__ import annotations

from mikemol.hooks import revendor

OLD = "a61069e"
NEW = "3142177"
SHA = "31421775e3e7e140dbd1b97adef99185f6d82cd9"
SOURCES = "".join(
    f'mikemol-{d} = {{ path = "vendor/wheels/{revendor.wheel_name(d, OLD)}" }}\n'
    for d in revendor.DISTS
)
LEDGER = "vendor/wheels/mikemol_ledger-0.1.0+gc3ca6d2-py3-none-any.whl"
OTHER = f'mikemol-ledger = {{ path = "{LEDGER}" }}\n'


def test_both_dists_move_to_the_new_sha_and_nothing_else_changes() -> None:
    """The control: each path takes the new sha and the rest of the text is byte for byte kept."""
    moved = revendor.move_sources(SOURCES, NEW)
    assert revendor.pinned_shorts(moved) == {NEW}
    assert moved.count(NEW) == len(revendor.DISTS)
    assert moved.replace(NEW, OLD) == SOURCES


def test_a_vendored_wheel_of_another_dist_is_not_ours_to_move() -> None:
    """Only hooks and pathsforward move: a ledger wheel keeps its own sha."""
    text = SOURCES + OTHER
    assert revendor.pinned_shorts(text) == {OLD}
    assert OTHER in revendor.move_sources(text, NEW)


def test_a_pyproject_that_vendors_nothing_reads_no_pins() -> None:
    """No vendored paths: no pins, and the move is the identity."""
    assert revendor.pinned_shorts("dependencies = []\n") == set()
    assert revendor.move_sources("dependencies = []\n", NEW) == "dependencies = []\n"


def test_the_wheel_name_carries_the_local_version() -> None:
    """The name is the one uv build writes for a +g local version."""
    got = revendor.wheel_name("hooks", NEW)
    assert got == "mikemol_hooks-0.1.0+g3142177-py3-none-any.whl"


def test_the_local_version_is_set_once_in_the_archived_text() -> None:
    """The first 0.1.0 line becomes the +g form; a text without it is None, not a no-op."""
    got = revendor.with_local_version('name = "x"\nversion = "0.1.0"\n', NEW)
    assert got == 'name = "x"\nversion = "0.1.0+g3142177"\n'
    twice = revendor.with_local_version('version = "0.1.0"\nversion = "0.1.0"\n', NEW)
    assert twice == 'version = "0.1.0+g3142177"\nversion = "0.1.0"\n'
    assert revendor.with_local_version('version = "0.2.0"\n', NEW) is None


def test_only_a_full_lowercase_commit_is_a_target() -> None:
    """A short sha, a branch or an uppercase sha would write a pin that does not pin."""
    assert revendor.is_full_sha(SHA)
    assert revendor.short_of(SHA) == NEW
    assert not any(revendor.is_full_sha(bad) for bad in (NEW, "main", SHA.upper(), SHA + "0"))


def test_the_plan_names_the_new_sha_the_old_pin_and_the_source() -> None:
    """The plan says where the archive comes from and what it replaces; a first vendor says none."""
    text = "\n".join(revendor.plan_lines(SHA, {OLD}, "mtools"))
    assert NEW in text
    assert OLD in text
    assert "from mtools" in text
    assert "(none)" in "\n".join(revendor.plan_lines(SHA, set(), "mtools"))

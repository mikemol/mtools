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


FENCE_LINE = f'mikemol-fence = {{ path = "vendor/wheels/{revendor.wheel_name("fence", OLD)}" }}\n'


def test_a_repo_that_vendors_the_fence_moves_it_with_the_pair() -> None:
    """mtools:W1031: the fence wheel, once added, takes the new sha with hooks and pathsforward."""
    text = SOURCES + FENCE_LINE
    assert revendor.pinned_shorts(text) == {OLD}
    moved = revendor.move_sources(text, NEW)
    assert moved.count(NEW) == len((*revendor.DISTS, "fence"))
    assert moved.replace(NEW, OLD) == text


def test_the_dists_a_repo_vendors_are_read_from_its_pyproject() -> None:
    """The pair always; the fence only when its wheel path is named; nothing reads as the pair."""
    assert revendor.vendored(SOURCES) == revendor.DISTS
    assert revendor.vendored(SOURCES + FENCE_LINE) == (*revendor.DISTS, "fence")
    assert revendor.vendored(FENCE_LINE) == ("fence",)
    assert revendor.vendored("dependencies = []\n") == revendor.DISTS


def test_the_plan_builds_each_dist_the_repo_vendors() -> None:
    """With the fence vendored the plan archives, builds and moves three, not two."""
    dists = (*revendor.DISTS, "fence")
    text = "\n".join(revendor.plan_lines(SHA, {OLD}, "mtools", dists))
    assert f"uv build --wheel fence -> {revendor.wheel_name('fence', NEW)}" in text
    assert "move the 3 wheel paths" in text
    assert "move the 2 wheel paths" in "\n".join(revendor.plan_lines(SHA, {OLD}, "mtools"))


NEMIK_DISTS = ("pathsforward", "hooks", "icsstruct", "fence", "rulerseq", "frontier")
NEMIK_OLD = "b5db3c4"
NEMIK = "".join(
    f'mikemol-{d} = {{ path = "vendor/wheels/{revendor.wheel_name(d, NEMIK_OLD, "")}" }}\n'
    for d in NEMIK_DISTS
)


def test_nemiks_layout_reads_without_the_g_and_with_six_dists() -> None:
    """W1449: no `g` in the local version, and the dists beyond the pair and the fence count."""
    assert not revendor.tag_of(NEMIK)
    assert revendor.tag_of(SOURCES) == "g"
    assert revendor.tag_of("dependencies = []\n") == "g"
    assert revendor.pinned_shorts(NEMIK) == {NEMIK_OLD}
    assert revendor.vendored(NEMIK) == (
        "hooks",
        "pathsforward",
        "fence",
        "icsstruct",
        "rulerseq",
        "frontier",
    )


def test_moving_nemiks_sources_keeps_the_missing_g_missing() -> None:
    """The control: the repo's own naming survives, so the new paths are the names uv will find."""
    moved = revendor.move_sources(NEMIK, NEW)
    assert revendor.pinned_shorts(moved) == {NEW}
    assert "+g" not in moved
    assert revendor.wheel_name("hooks", NEW, "") in moved
    assert revendor.wheel_name("hooks", NEW, "") == "mikemol_hooks-0.1.0+3142177-py3-none-any.whl"


def test_the_local_version_and_the_plan_follow_the_repos_tag() -> None:
    """A tag-less repo builds `0.1.0+<short>` and the plan names exactly that wheel."""
    got = revendor.with_local_version('version = "0.1.0"\n', NEW, "")
    assert got == 'version = "0.1.0+3142177"\n'
    text = "\n".join(revendor.plan_lines(SHA, {NEMIK_OLD}, "mtools", NEMIK_DISTS, (True, "")))
    assert "+3142177 in the archive only" in text
    assert revendor.wheel_name("frontier", NEW, "") in text


LUTHEN_DISTS = ("hooks", "pathsforward", "atomicwrite", "corpus", "waldo")
LUTHEN = "".join(
    f'mikemol-{d} = {{ path = "vendor/wheels/{revendor.wheel_name(d, OLD)}" }}\n'
    for d in LUTHEN_DISTS
)


def test_atomicwrite_corpus_and_waldo_are_vendored_dists_and_move_with_the_rest() -> None:
    """W1729 (luthen-observability:W1410): a repo vendoring them gets them listed and moved."""
    assert revendor.vendored(LUTHEN) == LUTHEN_DISTS
    moved = revendor.move_sources(LUTHEN, NEW)
    assert revendor.pinned_shorts(moved) == {NEW}
    for dist in ("atomicwrite", "corpus", "waldo"):
        assert revendor.wheel_name(dist, NEW) in moved


def test_cvdcore_is_a_vendored_dist_and_moves_with_the_rest() -> None:
    """W1787 (nemik:W438): a repo vendoring the colour-blind core gets it listed and moved."""
    text = "".join(
        f'mikemol-{d} = {{ path = "vendor/wheels/{revendor.wheel_name(d, OLD)}" }}\n'
        for d in ("hooks", "cvdcore")
    )
    assert revendor.vendored(text) == ("hooks", "cvdcore")
    assert revendor.wheel_name("cvdcore", NEW) in revendor.move_sources(text, NEW)


def test_ratchet_and_atomicwrite_are_vendored_dists_and_move_with_the_rest() -> None:
    """W1946 (nemik:W1027): the ratchet census wheel the ratchet emit needs moves with the pair."""
    text = "".join(
        f'mikemol-{d} = {{ path = "vendor/wheels/{revendor.wheel_name(d, OLD)}" }}\n'
        for d in ("hooks", "atomicwrite", "ratchet")
    )
    assert revendor.vendored(text) == ("hooks", "atomicwrite", "ratchet")
    moved = revendor.move_sources(text, NEW)
    assert revendor.wheel_name("ratchet", NEW) in moved
    assert revendor.wheel_name("atomicwrite", NEW) in moved


def test_transcriptstruct_is_a_vendored_dist_and_moves_with_the_rest() -> None:
    """W2054 (luthen-observability:W1684): the commitments exporter's wheel moves with the pair."""
    text = "".join(
        f'mikemol-{d} = {{ path = "vendor/wheels/{revendor.wheel_name(d, OLD)}" }}\n'
        for d in ("hooks", "transcriptstruct")
    )
    assert revendor.vendored(text) == ("hooks", "transcriptstruct")
    assert revendor.wheel_name("transcriptstruct", NEW) in revendor.move_sources(text, NEW)


def test_the_prose_naming_the_old_commit_moves_too() -> None:
    """Nemik's MODULE.bazel comments say `mtools <old>`; they follow the pin."""
    text = "# vendored the same way at mtools b5db3c4, one sha\n"
    assert revendor.move_mentions(text, NEMIK_OLD, NEW) == (
        "# vendored the same way at mtools 3142177, one sha\n"
    )

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The shard codemod rewrites only the shards line, all or none, and refuses a stale plan."""

import json
from pathlib import Path

import pytest

from mikemol.buildtel import shardplan

_AUDIO = """
mutants_sharded(
    name = "mutants",
    shards = 3,
    size = "medium",
    tags = ["exclusive"],
)
"""
_THREE = 3
_FOUR = 4
_FIVE = 5
_SLOWEST = 300.3


def _proposal(dist: str, old: int, new: int) -> shardplan.Proposal:
    return shardplan.Proposal(dist, "mutants", old, new, 300, _SLOWEST, "")


def _repo(root: Path, *dists: str) -> None:
    for dist in dists:
        (root / dist).mkdir()
        (root / dist / "BUILD.bazel").write_text(_AUDIO, encoding="utf-8")


def test_rewrite_changes_only_the_shards_line_of_the_named_grid() -> None:
    """Everything else in the file, including the size and tags, is byte-for-byte kept."""
    got = shardplan.rewrite(_AUDIO, _proposal("audiostruct", _THREE, _FIVE))
    assert got == _AUDIO.replace("shards = 3", "shards = 5")


def test_rewrite_refuses_a_count_that_moved() -> None:
    """The diff must still match the file it was drawn from."""
    with pytest.raises(shardplan.StaleDiffError, match="no longer has shards = 4"):
        shardplan.rewrite(_AUDIO, _proposal("d", _FOUR, _FIVE))


def test_rewrite_refuses_a_grid_that_is_gone() -> None:
    """A block of another name is not the one planned."""
    gone = shardplan.Proposal("d", "other", _THREE, _FOUR, 300, _SLOWEST, "")
    with pytest.raises(shardplan.StaleDiffError, match="no mutants_sharded block named other"):
        shardplan.rewrite(_AUDIO, gone)


def test_apply_is_all_or_none_across_dists(tmp_path: Path) -> None:
    """One stale proposal stops the write of the sound one before it."""
    _repo(tmp_path, "a", "b")
    mixed = [_proposal("a", _THREE, _FOUR), _proposal("b", _FOUR, _FIVE)]
    with pytest.raises(shardplan.StaleDiffError):
        shardplan.apply(tmp_path, mixed)
    assert (tmp_path / "a" / "BUILD.bazel").read_text(encoding="utf-8") == _AUDIO
    said = shardplan.apply(tmp_path, [_proposal("a", _THREE, _FOUR)])
    assert said == ["a mutants: shards 3 -> 4"]
    assert "shards = 4" in (tmp_path / "a" / "BUILD.bazel").read_text(encoding="utf-8")


def test_apply_refuses_a_missing_build_file(tmp_path: Path) -> None:
    """A dist with no BUILD.bazel cannot be rewritten."""
    with pytest.raises(shardplan.StaleDiffError, match="missing or a link"):
        shardplan.apply(tmp_path, [_proposal("nowhere", _THREE, _FOUR)])


def test_the_command_writes_only_with_apply(tmp_path: Path) -> None:
    """Dry by default; --apply writes the plan; any other third word is a usage error."""
    _repo(tmp_path, "audiostruct")
    row = {"label": "//audiostruct:mutants_0", "millis": 300_300, "complete": True}
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps(row) + "\n", encoding="utf-8")
    build = tmp_path / "audiostruct" / "BUILD.bazel"
    assert shardplan.main([str(rows), str(tmp_path)]) == 0
    assert build.read_text(encoding="utf-8") == _AUDIO
    assert shardplan.main([str(rows), str(tmp_path), "--bogus"]) == shardplan.EXIT_USAGE
    assert shardplan.main([str(rows), str(tmp_path), "--apply"]) == 0
    assert "shards = 3" not in build.read_text(encoding="utf-8")

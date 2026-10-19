# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An explicit timeout goes only from a grid whose shards fit the size default (W1580)."""

import json
from pathlib import Path

import pytest

from mikemol.buildtel import shardplan, timeoutdrop

_LONG = """
mutants_sharded(
    name = "mutants",
    shards = 12,
    timeout = "long",
    tags = ["exclusive"],
)
"""
_PLAIN = _LONG.replace('    timeout = "long",\n', "")
_FITS_MS = 100_000
_OVER_MS = 200_000
_SLOWEST_S = 100.0
_LIMIT_S = 300
_ONE = 1


def _rows(*millis: int) -> list[shardplan.Row]:
    return [
        {"label": f"//d:mutants_{k}", "millis": ms, "complete": True} for k, ms in enumerate(millis)
    ]


def _read(text: str | None) -> shardplan.ReadBuild:
    def read(_dist: str) -> str | None:
        return text

    return read


def _drop() -> timeoutdrop.Drop:
    return timeoutdrop.Drop("d", "mutants", "long", _SLOWEST_S, _LIMIT_S)


def test_a_grid_whose_slowest_shard_fits_the_default_loses_its_timeout() -> None:
    """100 s of a 300 s default is under half: the explicit long can go."""
    got = timeoutdrop.plan(_rows(_FITS_MS, 50_000), _read(_LONG))
    assert got == [_drop()]
    assert "REMOVE timeout = 'long'" in got[0].line()


def test_a_grid_still_over_the_fraction_keeps_its_timeout_for_shardplan() -> None:
    """200 s is over half of 300 s: resharding comes first, so nothing is dropped here."""
    assert timeoutdrop.plan(_rows(_OVER_MS), _read(_LONG)) == []


def test_a_grid_with_no_timeout_or_no_block_is_left_out() -> None:
    """Nothing to remove from a block without one, and no verdict for a missing block."""
    assert timeoutdrop.plan(_rows(_FITS_MS), _read(_PLAIN)) == []
    assert timeoutdrop.plan(_rows(_FITS_MS), _read(None)) == []


def test_rewrite_removes_only_the_timeout_line() -> None:
    """Everything else in the block, and outside it, is byte for byte kept."""
    assert timeoutdrop.rewrite(_LONG, _drop()) == _PLAIN


def test_rewrite_refuses_a_timeout_that_changed_or_a_grid_that_is_gone() -> None:
    """The plan must still match the file it was drawn from."""
    moved = timeoutdrop.Drop("d", "mutants", "eternal", _SLOWEST_S, _LIMIT_S)
    with pytest.raises(shardplan.StaleDiffError, match="no longer has timeout"):
        timeoutdrop.rewrite(_LONG, moved)
    with pytest.raises(shardplan.StaleDiffError, match="no longer has timeout"):
        timeoutdrop.rewrite(_PLAIN, _drop())
    other = timeoutdrop.Drop("d", "other", "long", _SLOWEST_S, _LIMIT_S)
    with pytest.raises(shardplan.StaleDiffError, match="no mutants_sharded block named other"):
        timeoutdrop.rewrite(_LONG, other)


def test_apply_is_all_or_none_across_dists(tmp_path: Path) -> None:
    """A stale drop stops the write of the sound one before it."""
    for dist, text in (("a", _LONG), ("b", _PLAIN)):
        (tmp_path / dist).mkdir()
        (tmp_path / dist / "BUILD.bazel").write_text(text, encoding="utf-8")
    sound = timeoutdrop.Drop("a", "mutants", "long", _SLOWEST_S, _LIMIT_S)
    stale = timeoutdrop.Drop("b", "mutants", "long", _SLOWEST_S, _LIMIT_S)
    with pytest.raises(shardplan.StaleDiffError):
        timeoutdrop.apply(tmp_path, [sound, stale])
    assert (tmp_path / "a" / "BUILD.bazel").read_text(encoding="utf-8") == _LONG
    assert timeoutdrop.apply(tmp_path, [sound]) == ["a mutants: removed timeout = 'long'"]
    assert (tmp_path / "a" / "BUILD.bazel").read_text(encoding="utf-8") == _PLAIN


def test_main_is_a_dry_run_unless_apply_and_a_stale_plan_exits_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --apply nothing is written; with it the timeout goes; a usage slip is exit 2."""
    (tmp_path / "d").mkdir()
    build = tmp_path / "d" / "BUILD.bazel"
    build.write_text(_LONG, encoding="utf-8")
    rows = tmp_path / "rows.jsonl"
    rows.write_text("\n".join(json.dumps(r) for r in _rows(_FITS_MS)) + "\n", encoding="utf-8")
    assert timeoutdrop.main([str(rows), str(tmp_path)]) == 0
    assert build.read_text(encoding="utf-8") == _LONG
    assert "whose timeout can go" in capsys.readouterr().out
    assert timeoutdrop.main([str(rows), str(tmp_path), "--apply"]) == 0
    assert build.read_text(encoding="utf-8") == _PLAIN
    assert timeoutdrop.main([str(rows), str(tmp_path), "--apply"]) == 0
    assert timeoutdrop.main([str(rows)]) == timeoutdrop.EXIT_USAGE

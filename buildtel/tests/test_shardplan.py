# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A grid whose slowest shard took over half its size default gets a planned shard count (W1573)."""

import json
from pathlib import Path

from mikemol.buildtel import shardplan

_AUDIO = """
mutants_sharded(
    name = "mutants",
    shards = 3,
    size = "medium",
    tags = ["exclusive"],
)
"""
_PATHS = """
mutants_sharded(
    name = "mutants",
    shards = 12,
    timeout = "long",
)
"""
_THREE = 3
_FOUR = 4
_FIVE = 5
_TWELVE = 12
_FEW = 1000
_FULL = 300_000
_SLOWEST = 300.3


def _row(label: str, millis: int, *, complete: bool = True) -> shardplan.Row:
    return {"label": label, "millis": millis, "complete": complete, "status": "PASSED"}


def _builds(**texts: str) -> shardplan.ReadBuild:
    return texts.get


def test_a_block_declares_its_shards_its_size_and_its_timeout() -> None:
    """Size defaults to medium when absent; an explicit timeout is carried so it can be flagged."""
    assert shardplan.block_of(_AUDIO, "mutants") == shardplan.Block(_THREE, "medium", "")
    assert shardplan.block_of(_PATHS, "mutants") == shardplan.Block(_TWELVE, "medium", "long")
    assert shardplan.block_of(_AUDIO, "other") is None


def test_the_timed_out_shard_is_planned_against_half_the_medium_default() -> None:
    """The audiostruct case: 300.3 s against 300 s, total 583 s over 150 s, so four shards."""
    rows = [
        _row("//audiostruct:mutants_0", 300_300),
        _row("//audiostruct:mutants_1", 145_000),
        _row("//audiostruct:mutants_2", 138_000),
    ]
    proposals, findings = shardplan.plan(rows, _builds(audiostruct=_AUDIO))
    assert findings == []
    got = [(p.dist, p.name, p.old, p.new) for p in proposals]
    assert got == [("audiostruct", "mutants", _THREE, _FOUR)]
    assert proposals[0].slowest_s == _SLOWEST


def test_the_count_is_the_total_over_half_the_limit_and_never_less_than_one_more() -> None:
    """A total of 600 s over 150 s is four shards; a grid already at four still gets five."""
    rows = [_row(f"//d:mutants_{k}", 200_000) for k in range(_THREE)]
    proposals, _ = shardplan.plan(rows, _builds(d=_AUDIO))
    assert proposals[0].new == _FOUR
    four = _AUDIO.replace("shards = 3", "shards = 4")
    proposals, _ = shardplan.plan(rows, _builds(d=four))
    assert proposals[0].new == _FIVE


def test_a_grid_under_half_its_limit_is_left_alone() -> None:
    """149 s of 300 s is under the fraction: no proposal."""
    rows = [_row("//d:mutants_0", 149_000), _row("//d:mutants_1", 10_000)]
    assert shardplan.plan(rows, _builds(d=_AUDIO)) == ([], [])


def test_an_explicit_timeout_is_not_the_limit_and_is_named_for_removal() -> None:
    """The pathsforward shard of 416 s passes at timeout long, but is planned against 300 s."""
    rows = [_row("//p:mutants_10", 416_000), _row("//p:mutants_1", 100_000)]
    proposals, _ = shardplan.plan(rows, _builds(p=_PATHS))
    assert proposals[0].limit_s == shardplan.LIMITS["medium"]
    assert proposals[0].new > proposals[0].old
    assert "REMOVE timeout = 'long'" in proposals[0].line()


def test_an_incomplete_row_is_not_a_maximum_of_anything() -> None:
    """A row from a partial listing is left out, whatever it says."""
    rows = [_row("//d:mutants_0", _FULL, complete=False)]
    assert shardplan.plan(rows, _builds(d=_AUDIO)) == ([], [])


def test_a_slow_plain_test_and_a_grid_without_a_block_are_findings_not_silence() -> None:
    """What this planner cannot reshard is named."""
    rows = [_row("//d:test_slow", _FULL), _row("//e:mutants_0", _FEW)]
    proposals, findings = shardplan.plan(rows, _builds(d=_AUDIO))
    assert proposals == []
    assert findings[0].startswith("//d:test_slow:")
    assert "//e:mutants" in findings[1]


_CPU_OVER = 200.0
_CPU_UNDER = 20.0
_TWO = 2


def test_a_plain_test_is_judged_by_its_own_cpu_when_the_row_has_it_else_by_wall() -> None:
    """W1894: past half the limit in CPU is a split finding; long wall of low CPU is not."""
    slow_cpu = {**_row("//d:test_cpu", _FULL), "cpu_s": _CPU_OVER}
    queued = {**_row("//d:test_queued", _FULL), "cpu_s": _CPU_UNDER}
    rows = [slow_cpu, queued, _row("//d:test_nocpu", _FULL)]
    findings = shardplan.plan(rows, _builds(d=_AUDIO))[1]
    assert len(findings) == _TWO
    assert "split it per test" in findings[0]
    assert findings[0].startswith("//d:test_cpu:")
    assert findings[1].startswith("//d:test_nocpu:")


def test_the_command_prints_the_diff_and_writes_nothing(tmp_path: Path) -> None:
    """The dry run reads a rows file and a repo, prints the line, and leaves BUILD as it was."""
    build = tmp_path / "audiostruct" / "BUILD.bazel"
    build.parent.mkdir()
    build.write_text(_AUDIO, encoding="utf-8")
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps(_row("//audiostruct:mutants_0", 300_300)) + "\n", encoding="utf-8")
    assert shardplan.main([str(rows), str(tmp_path)]) == 0
    assert build.read_text(encoding="utf-8") == _AUDIO
    assert shardplan.main([str(rows)]) == shardplan.EXIT_USAGE

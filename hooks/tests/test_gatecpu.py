# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A gate's process tree is summed as CPU seconds from /proc/<pid>/stat files (W2105).

⚑ THE FIXTURE IS A FAKE /proc: one directory per pid holding a stat line in proc(5)'s shape, with a
command name that holds spaces and a parenthesis, which is where a split-on-space reader fails.
"""

from pathlib import Path

import pytest

from mikemol.hooks import gatecpu

_FILLER = " 0" * 9
_TICKS_PER_SECOND = 100
_WHOLE_TREE_S = 3.0
_CHILD_TREE_S = 1.0
_PARSED_TICKS = 42.0


def _stat(pid: int, comm: str, ppid: int, utime: int, stime: int) -> str:
    return f"{pid} ({comm}) S {ppid}{_FILLER} {utime} {stime} 0 0 20 0 1 0 1 1 1\n"


def _proc(tmp_path: Path, rows: list[tuple[int, str, int, int, int]]) -> Path:
    proc = tmp_path / "proc"
    for pid, comm, ppid, utime, stime in rows:
        (proc / str(pid)).mkdir(parents=True)
        (proc / str(pid) / "stat").write_text(_stat(pid, comm, ppid, utime, stime), "utf-8")
    (proc / "self").mkdir()
    return proc


def test_a_stat_line_with_spaces_and_parentheses_in_its_name_parses_from_the_last_paren() -> None:
    """The parent and the user+sys ticks are read after the closing parenthesis."""
    assert gatecpu.parse_stat(_stat(7, "bazel (server) x", 3, 40, 2)) == (3, _PARSED_TICKS)
    assert gatecpu.parse_stat("no parenthesis here") is None
    assert gatecpu.parse_stat("7 (short) S 1 0") is None
    assert gatecpu.parse_stat("7 (x) S one" + _FILLER + " 1 2 3") is None


def test_the_sum_covers_the_root_and_every_descendant_and_no_other_process(
    tmp_path: Path,
) -> None:
    """Root 100 with child 101 and grandchild 102; 200 is a stranger; 'self' is skipped."""
    rows = [
        (100, "bazel", 1, 100, 100),
        (101, "sh", 100, 50, 0),
        (102, "pytest (worker)", 101, 25, 25),
        (200, "other", 1, 9999, 9999),
        (300, "orphan of a pid that is gone", 4242, 5, 5),
    ]
    proc = _proc(tmp_path, rows)
    assert gatecpu.sample(proc, 100, _TICKS_PER_SECOND) == pytest.approx(_WHOLE_TREE_S)
    assert gatecpu.sample(proc, 101, _TICKS_PER_SECOND) == pytest.approx(_CHILD_TREE_S)
    assert not gatecpu.sample(proc, 4242, _TICKS_PER_SECOND)

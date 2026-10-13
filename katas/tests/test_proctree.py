# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `proctree`: the CPU of a process and all its descendants, from a fake `/proc`.

W1124. ⚑ THE UNRELATED PROCESS IS THE CONTROL: it sits in the same fake `/proc` with the most CPU
of all, and the sum for the root must not include it, so the sum is the tree's and not the host's.
No real `/proc` is read; every process here is a `stat` file written under `tmp_path`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from mikemol.katas import proctree

if TYPE_CHECKING:
    from pathlib import Path

_HZ = 100
_ROOT = 100
_TREE_TICKS = 15 + 20 + 30 + 40


def _proc(proc: Path, pid: int, ppid: int, ticks: tuple[int, int], comm: str = "worker") -> None:
    """Write one process's `stat` line, 9 untouched fields between the parent and utime."""
    folder = proc / str(pid)
    folder.mkdir()
    zeros = " ".join(["0"] * 9)
    line = f"{pid} ({comm}) S {ppid} {zeros} {ticks[0]} {ticks[1]} 0 0 20 0 1 0 0 0 0\n"
    (folder / "stat").write_text(line, encoding="utf-8")


def _tree(proc: Path) -> None:
    _proc(proc, _ROOT, 1, (10, 5))
    _proc(proc, 101, _ROOT, (20, 0))
    _proc(proc, 102, _ROOT, (0, 30))
    _proc(proc, 201, 101, (40, 0))
    _proc(proc, 900, 1, (9999, 9999))


def test_the_sum_is_the_root_and_every_descendant_and_not_the_unrelated_process(
    tmp_path: Path,
) -> None:
    """15 + 20 + 30 + 40 = 105 ticks; the 19998-tick stranger is left out."""
    _tree(tmp_path)
    assert proctree.tree_ticks(_ROOT, tmp_path) == _TREE_TICKS


def test_seconds_are_the_ticks_over_the_tick_rate(tmp_path: Path) -> None:
    """105 ticks at 100 per second is 1.05 s."""
    _tree(tmp_path)
    seconds = proctree.cpu_seconds(_ROOT, tmp_path, _HZ)
    assert seconds is not None
    assert math.isclose(seconds, _TREE_TICKS / _HZ)


def test_a_gone_root_is_none_not_zero(tmp_path: Path) -> None:
    """A finished child and an idle one are different answers."""
    _tree(tmp_path)
    assert proctree.tree_ticks(4242, tmp_path) is None
    assert proctree.cpu_seconds(4242, tmp_path, _HZ) is None


def test_a_command_name_with_spaces_and_parentheses_is_read_from_the_last_parenthesis(
    tmp_path: Path,
) -> None:
    """The fields are counted after the LAST ')', so a comm like `a (b) c` does not shift them."""
    _proc(tmp_path, _ROOT, 1, (7, 3), comm="a (b) c")
    assert proctree.tree_ticks(_ROOT, tmp_path) == 7 + 3


def test_an_unreadable_entry_is_skipped_and_a_non_process_entry_is_ignored(tmp_path: Path) -> None:
    """A garbled stat and a directory named `self` are left out; the rest still sums."""
    _tree(tmp_path)
    (tmp_path / "self").mkdir()
    (tmp_path / "555").mkdir()
    (tmp_path / "555" / "stat").write_text("garbled", encoding="utf-8")
    assert proctree.tree_ticks(_ROOT, tmp_path) == _TREE_TICKS

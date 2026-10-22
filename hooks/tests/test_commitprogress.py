# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A commit's progress is the CPU of its process tree or growth of its output (W1803)."""

import os
from pathlib import Path

from mikemol.hooks import commitprogress as progress

# pid (comm) state ppid pgrp session tty tpgid flags minflt cminflt majflt cmajflt utime stime ...
_STAT = "4242 (git (weird) name) S 17 4242 4242 0 -1 0 0 0 0 0 30 12 0 0 20 0 1 0 5 0 0\n"
_SECOND_TREE_TICKS = 200
_FLAT_LOOKS = 3


def test_a_stat_line_gives_parent_and_user_plus_system_ticks() -> None:
    """The command name may hold spaces and parentheses; fields count from the last one."""
    assert progress.parse_stat(_STAT) == (17, 42)


def test_a_line_that_is_not_a_stat_line_gives_nothing() -> None:
    """Too few fields, a non-number and text with no parenthesis are all None."""
    assert progress.parse_stat("") is None
    assert progress.parse_stat("1 (x) S 2 3") is None
    assert progress.parse_stat(_STAT.replace(" 30 12 ", " a b ")) is None


def test_the_tree_adds_the_root_and_every_descendant_and_nobody_else() -> None:
    """A grandchild counts, a sibling tree does not, and a root not in the table is 0."""
    table = {1: (0, 10), 2: (1, 5), 3: (2, 1), 4: (0, 100), 5: (4, 100)}
    assert progress.tree_ticks(table, 1) == 10 + 5 + 1
    assert progress.tree_ticks(table, 4) == _SECOND_TREE_TICKS
    assert progress.tree_ticks(table, 99) == 0


def test_cpu_or_output_growth_resets_the_witness_and_a_flat_look_adds() -> None:
    """Either kind of progress is progress; a look with neither is flat."""
    seen = progress.Witness()
    seen = progress.step(seen, 10, 100)
    assert seen == progress.Witness(10, 100, 0)
    seen = progress.step(seen, 10, 100)
    assert seen.flat == 1
    assert progress.step(seen, 11, 100).flat == 0
    assert progress.step(seen, 10, 101).flat == 0


def test_a_look_that_went_backwards_never_lowers_the_record() -> None:
    """A tree that lost a process reads fewer ticks; that is not progress and not a reset."""
    seen = progress.step(progress.Witness(), 10, 100)
    after = progress.step(seen, 4, 100)
    assert (after.ticks, after.flat) == (10, 1)


def test_a_stall_is_a_run_of_flat_looks_and_never_for_a_limit_below_one() -> None:
    """Three flat looks stall at three; a limit of zero never fires."""
    seen = progress.Witness(1, 1, 0)
    for _ in range(_FLAT_LOOKS):
        seen = progress.step(seen, 1, 1)
    assert progress.stalled(seen, _FLAT_LOOKS)
    assert not progress.stalled(seen, _FLAT_LOOKS + 1)
    assert not progress.stalled(seen, 0)


_BUSY_LOOKS = 10
_EXIT_THREE = 3


def _never_ends(_seconds: float) -> int | None:
    return None


def _zero() -> int:
    return 0


def _ends_with_three(_seconds: float) -> int | None:
    return _EXIT_THREE


def test_a_watch_ends_on_a_stall_and_never_on_elapsed_time() -> None:
    """A child that spends nothing and writes nothing is given up on after the looks."""
    table = {5: (1, 7)}
    got = progress.watch(_never_ends, 5, _zero, (_FLAT_LOOKS, 0.0), lambda: table)
    assert got is None


def test_a_watch_keeps_waiting_while_the_tree_spends_cpu_or_writes() -> None:
    """Each look that shows growth resets the count, so a busy gate is never ended."""
    ticks = iter(range(1, 50))
    waits: list[int] = []

    def wait(_seconds: float) -> int | None:
        waits.append(1)
        return 0 if len(waits) > _BUSY_LOOKS else None

    def procs() -> progress.Procs:
        return {5: (1, next(ticks))}

    assert progress.watch(wait, 5, _zero, (_FLAT_LOOKS, 0.0), procs) == 0
    assert len(waits) == _BUSY_LOOKS + 1


def test_a_watch_returns_the_exit_code_of_a_child_that_ends() -> None:
    """The code comes back as it is, including a failing one."""
    assert progress.watch(_ends_with_three, 5, _zero, (_FLAT_LOOKS, 0.0)) == _EXIT_THREE


def test_the_phase_is_the_last_mark_and_the_stall_text_names_it() -> None:
    """Marks are `pre-commit: phase NAME NS`; none marked is said as such."""
    text = "x\npre-commit: phase lint 100\nnoise\npre-commit: phase bazel 200\n"
    assert progress.phase_of(text) == "bazel"
    assert progress.phase_of("nothing\n") == progress.NO_PHASE
    said = progress.stall_text(text, _FLAT_LOOKS, 30.0)
    assert "3 looks 30 s apart" in said
    assert "last gate phase: bazel" in said


def test_the_real_process_table_holds_this_process_with_its_parent() -> None:
    """The positive control: the reader sees the process running the test."""
    table = progress.snapshot()
    assert table[os.getpid()][0] == os.getppid()
    assert progress.tree_ticks(table, os.getpid()) >= 0


def test_an_unreadable_table_or_entry_is_skipped_not_raised(tmp_path: Path) -> None:
    """A missing /proc is an empty table; one unreadable stat leaves that pid out."""
    assert progress.snapshot(tmp_path / "absent") == {}
    (tmp_path / "7").mkdir()
    (tmp_path / "8").mkdir()
    (tmp_path / "x").mkdir()

    def read(path: Path) -> str | None:
        return _STAT if path.parent.name == "7" else None

    assert progress.snapshot(tmp_path, read) == {7: (17, 42)}

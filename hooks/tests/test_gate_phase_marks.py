# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pre-commit's phase marks: the gate prints what the reader reads (W1575)."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from mikemol.hooks import gatephase

GATE = Path(__file__).parent.parent.parent / ".githooks" / "pre-commit"
BASH = shutil.which("bash") or "bash"
START = "phase() {"
NAME_CUT = 48
SCRIPT = 'set -euo pipefail\n{function}\nphase "$1"\necho "after: rc=$?"\n'


def _function() -> str:
    """Slice `phase` out of the pre-commit, from its header to its closing brace.

    Returns:
        the function's text.

    """
    text = GATE.read_text(encoding="utf-8")
    head = text.index(START)
    return text[head : text.index("\n}\n", head) + 2]


def _run(name: str) -> subprocess.CompletedProcess[str]:
    """Run `phase NAME` under bash, as the gate's `set -euo pipefail` shell would.

    Returns:
        the finished process, both streams captured.

    """
    script = SCRIPT.replace("{function}", _function())
    return subprocess.run(
        [BASH, "-c", script, "bash", name], capture_output=True, text=True, check=False
    )


def test_a_mark_is_one_whole_line_the_reader_reads_with_the_gates_own_clock() -> None:
    """The gate prints the grammar `gatephase` reads, with a nanosecond time from `date`."""
    before = time.time_ns()
    done = _run("prebuild")
    after = time.time_ns()
    found = gatephase.marks(done.stderr)
    assert [m.name for m in found] == ["prebuild"]
    assert before <= found[0].at_ns <= after
    assert "after: rc=0" in done.stdout


def test_a_name_with_spaces_and_punctuation_becomes_one_word_the_reader_accepts() -> None:
    """The reader skips a mark whose name has a space, so the gate never prints one.

    `tr` works on bytes, so the three-byte dash in a label becomes three underscores.
    """
    found = gatephase.marks(_run("check_hooks: pytest — every case passes").stderr)
    assert [m.name for m in found] == ["check_hooks__pytest_____every_case_passes"]


def test_a_long_name_is_cut_to_forty_eight_characters() -> None:
    """A label that is a whole sentence still makes a span name of a sane length."""
    found = gatephase.marks(_run("w" * (NAME_CUT * 2)).stderr)
    assert [len(m.name) for m in found] == [NAME_CUT]


def test_every_stage_marks_itself_so_a_refactor_cannot_drop_a_stage_silently() -> None:
    """The prebuild, the bazel suite and the two shared helpers each call `phase`."""
    text = GATE.read_text(encoding="utf-8")
    for call in ("phase prebuild", "phase bazel_test", 'phase "check_$_rlabel"'):
        assert call in text
    assert 'phase "witness_$_wlabel"' in text

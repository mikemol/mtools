# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each refusing rung of the commit gate says the one command that reproduces only it (W1663).

⚑ THE CONTROLS: the block sits in the detail replayed under the verdict and never in the label the
gate history matches on (W1721), and the ratchet census, a rung of its own, has one beside the
hermetic suite's.
"""

from pathlib import Path

_GATE = Path(__file__).parents[2] / ".githooks" / "pre-commit"
_BLOCK = "--- reproduce only the refusing rung"
_RUNGS = 2


def _lines() -> list[str]:
    return _GATE.read_text(encoding="utf-8").splitlines()


def test_the_ratchet_census_names_the_command_that_reproduces_only_it() -> None:
    """The block names the dist and carries the tool's own invocation under the refusing branch."""
    lines = _lines()
    at = [i for i, line in enumerate(lines) if f"{_BLOCK} ($dist: ratchet)" in line]
    assert len(at) == 1
    after = lines[at[0] + 1]
    assert "mikemol-ratchet $dist" in after
    assert after.lstrip().startswith("RUFF_BIN=$dist/")


def test_the_reproduce_blocks_go_to_the_detail_and_never_to_the_label() -> None:
    """Every block follows an append to failed_detail, the text replayed, not a note_failure."""
    lines = _lines()
    blocks = [i for i, line in enumerate(lines) if _BLOCK in line]
    assert len(blocks) == _RUNGS
    for i in blocks:
        assert 'failed_detail="$failed_detail' in lines[i - 1]
        assert "note_failure" not in lines[i]

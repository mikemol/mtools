# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ratchet-emit block is put into a gate script once, after its anchor (W1928)."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from mikemol.hooks import ratchet_hook

if TYPE_CHECKING:
    from pathlib import Path

_SPEC = ratchet_hook.Spec(
    after="ratchet check",
    tool="$wt/.venv/bin/mikemol-ratchet-emit",
    ratchet="$wt/.venv/bin/mikemol-ratchet",
    name='$(basename "$real_root")',
    tree="$wt",
)
_SCRIPT = "set -e\necho ratchet check\necho later\n"


def _args(script: Path, *extra: str) -> list[str]:
    return [
        str(script),
        "--after",
        _SPEC.after,
        "--tool",
        _SPEC.tool,
        "--ratchet",
        _SPEC.ratchet,
        "--name",
        _SPEC.name,
        "--dir",
        _SPEC.tree,
        *extra,
    ]


def test_the_block_goes_right_after_the_anchor_and_names_the_four_inputs() -> None:
    """The lines after the anchor are the block; the rest of the script is as it was."""
    result = ratchet_hook.insert(_SCRIPT, _SPEC)
    assert result is not None
    lines = result.splitlines()
    assert lines[:2] == ["set -e", "echo ratchet check"]
    assert lines[-1] == "echo later"
    assert 'RATCHET_BIN="$wt/.venv/bin/mikemol-ratchet"' in result
    assert '"$(basename "$real_root")" "$wt"' in result
    assert result.endswith("\n")


def test_a_script_that_already_has_the_block_is_left_alone() -> None:
    """Idempotent: the second insert returns the text unchanged."""
    once = ratchet_hook.insert(_SCRIPT, _SPEC)
    assert once is not None
    assert ratchet_hook.insert(once, _SPEC) == once


def test_an_anchor_in_no_line_is_not_guessed_at() -> None:
    """Never appended where it might follow an exit: the insert answers None."""
    elsewhere = ratchet_hook.Spec("no such line", "t", "r", "n", "d")
    assert ratchet_hook.insert(_SCRIPT, elsewhere) is None


def test_the_command_prints_a_dry_run_and_writes_only_with_write(tmp_path: Path) -> None:
    """Without --write the block is shown and the file is unchanged; with it the file gains it."""
    script = tmp_path / "gate.sh"
    script.write_text(_SCRIPT, encoding="utf-8")
    out = io.StringIO()
    assert ratchet_hook.main(_args(script), out) == 0
    assert "dry run" in out.getvalue()
    assert script.read_text(encoding="utf-8") == _SCRIPT
    assert ratchet_hook.main(_args(script, "--write"), io.StringIO()) == 0
    assert "mikemol-ratchet-emit" in script.read_text(encoding="utf-8")
    again = io.StringIO()
    assert ratchet_hook.main(_args(script, "--write"), again) == 0
    assert "unchanged" in again.getvalue()


def test_a_bad_command_line_or_a_missing_anchor_is_refused(tmp_path: Path) -> None:
    """Usage is exit 2; an anchor in no line or an unreadable script is exit 4."""
    script = tmp_path / "gate.sh"
    script.write_text("echo nothing\n", encoding="utf-8")
    assert ratchet_hook.main([str(script)], io.StringIO()) == ratchet_hook.EXIT_USAGE
    assert ratchet_hook.main(_args(script), io.StringIO()) == ratchet_hook.EXIT_REFUSED
    gone = tmp_path / "gone.sh"
    assert ratchet_hook.main(_args(gone), io.StringIO()) == ratchet_hook.EXIT_REFUSED

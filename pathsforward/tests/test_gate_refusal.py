# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Reconcile names a repository with no commit gate instead of blaming PATH (W2180).

⚑ THE CONTROLS: a tool that ran and refused gives its own first stderr line; an absent tool, a tool
that exits 0 and a tool that cannot start give none, so only those keep the PATH hint. ⚑ ONE RUN:
the map and the refusal line come from the same child, never from two (github-cb, b69).
"""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import landed, reconcilecmd
from mikemol.pathsforward.model import RefusedError, State

if TYPE_CHECKING:
    from pathlib import Path

CAUSE = "git cannot name its directory"


def _tool(folder: Path, code: int, said: str, out: str = "") -> str:
    script = folder / "mikemol-commit"
    ran = folder / "ran"
    lines = [
        "#!/bin/sh",
        f"echo x >> '{ran}'",
        f"echo '{out}'",
        "echo '' >&2",
        f"echo '{said}' >&2",
        f"exit {code}",
    ]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return str(script)


def test_a_tool_that_ran_and_refused_gives_its_own_line(tmp_path: Path) -> None:
    """The first non-empty stderr line, not a guess about PATH."""
    assert landed.refusal_line(_tool(tmp_path, 1, CAUSE), tmp_path) == CAUSE


def test_an_absent_or_agreeable_or_unstartable_tool_gives_no_line(tmp_path: Path) -> None:
    """None means the PATH hint stays; exit 0 is not a refusal; a missing file cannot start."""
    assert not landed.refusal_line(None, tmp_path)
    assert not landed.refusal_line(_tool(tmp_path, 0, "fine"), tmp_path)
    assert not landed.refusal_line(str(tmp_path / "nowhere"), tmp_path)


def test_the_note_names_the_repo_for_a_refusal_and_keeps_the_hint_otherwise(tmp_path: Path) -> None:
    """A refusal reads 'no commit gate for <repo> (<line>)'; no line keeps GATING_NOTE."""
    named = reconcilecmd.gating_note(CAUSE, tmp_path)
    assert named == f"no commit gate for {tmp_path.name} ({CAUSE})"
    assert reconcilecmd.gating_note("", tmp_path) == reconcilecmd.GATING_NOTE


def test_one_run_of_the_tool_gives_the_map_when_it_agrees_and_the_line_when_it_refuses(
    tmp_path: Path,
) -> None:
    """Exit 0 gives the stdout and no line; exit 1 gives no map and the first stderr line."""
    agreeable = landed.read_tool(_tool(tmp_path, 0, "fine", "[]"), tmp_path)
    assert (agreeable[0] is not None and agreeable[0].strip(), agreeable[1]) == ("[]", "")
    assert landed.read_tool(_tool(tmp_path, 1, CAUSE, "[]"), tmp_path) == (None, CAUSE)


def test_the_gate_map_is_read_through_the_tool_found_and_a_refusal_reads_as_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """read_gate returns the tool's stdout when it agrees and None when it refuses or is absent."""
    agreeing = _tool(tmp_path, 0, "fine", "[]")

    def found(root: Path) -> str | None:
        del root
        return agreeing

    monkeypatch.setattr(landed, "find_gate_tool", found)
    got = landed.read_gate(tmp_path)
    assert got is not None
    assert got.strip() == "[]"
    refusing = _tool(tmp_path, 1, CAUSE, "[]")

    def refused(root: Path) -> str | None:
        del root
        return refusing

    monkeypatch.setattr(landed, "find_gate_tool", refused)
    assert landed.read_gate(tmp_path) is None


def test_reconcile_starts_the_gate_tool_once_even_when_it_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal line rides the same child as the map: one start, not a second for stderr."""
    tool = _tool(tmp_path, 1, CAUSE)

    def named(root: Path) -> str:
        del root
        return tool

    monkeypatch.setattr(landed, "find_gate_tool", named)
    with pytest.raises(RefusedError, match=CAUSE):
        reconcilecmd.run(State({}, [], [], 0), tmp_path, write=False)
    assert (tmp_path / "ran").read_text(encoding="utf-8").count("x") == 1

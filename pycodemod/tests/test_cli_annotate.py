# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`annotate` writes observed types only where the project's mypy count falls."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_annotate import AnnotateFlags, print_annotate

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

SOURCE = "def f(x):\n    return x\n"
UNREAD = 2
WORKLIST = 1


def _seen(tmp_path: Path, name: str, param: str) -> Path:
    body = {f"{name}::f": {"params": {"x": [param]}, "returns": [param]}}
    path = tmp_path / "seen.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _run(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    # A stand-in for mypy and ruff: the `int` candidate has one finding fewer than the original.
    if not argv[0].endswith("mypy"):
        return 0, "", ""
    probe = argv[-1]
    typed = "x: int" in (cwd / probe).read_text(encoding="utf-8")
    messages = ["a"] if typed else ["a", "b"]
    lines = [f'{{"file": "{probe}", "message": "{m}"}}' for m in messages]
    return 1, "\n".join(lines), ""


def _flags(tmp_path: Path, seen: Path, *, write: bool) -> AnnotateFlags:
    return AnnotateFlags(root=str(tmp_path), write=write, seen=str(seen))


def test_a_dry_run_writes_nothing_and_write_lands_the_improvement(tmp_path: Path) -> None:
    """Without --write the file is untouched; with it the judged candidate lands."""
    target = tmp_path / "mod.py"
    target.write_text(SOURCE, encoding="utf-8")
    seen = _seen(tmp_path, str(target), "int")
    assert print_annotate([str(target)], _flags(tmp_path, seen, write=False), _run) == 0
    assert target.read_text(encoding="utf-8") == SOURCE
    assert print_annotate([str(target)], _flags(tmp_path, seen, write=True), _run) == 0
    assert "x: int" in target.read_text(encoding="utf-8")


def test_a_file_whose_count_does_not_fall_is_never_touched(tmp_path: Path) -> None:
    """The type observed is `str`, so the stand-in judge sees no improvement."""
    target = tmp_path / "mod.py"
    target.write_text(SOURCE, encoding="utf-8")
    seen = _seen(tmp_path, str(target), "str")
    assert print_annotate([str(target)], _flags(tmp_path, seen, write=True), _run) == WORKLIST
    assert target.read_text(encoding="utf-8") == SOURCE


def test_observations_that_cannot_be_read_are_exit_two(tmp_path: Path) -> None:
    """A missing file and a document that is not an object both refuse."""
    target = tmp_path / "mod.py"
    target.write_text(SOURCE, encoding="utf-8")
    gone = tmp_path / "gone.json"
    assert print_annotate([str(target)], _flags(tmp_path, gone, write=True), _run) == UNREAD
    listing = tmp_path / "list.json"
    listing.write_text("[]", encoding="utf-8")
    assert print_annotate([str(target)], _flags(tmp_path, listing, write=True), _run) == UNREAD

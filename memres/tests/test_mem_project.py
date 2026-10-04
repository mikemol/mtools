# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mem_project`: the store projects to `mem.json`, and drift is named."""

from __future__ import annotations

from contextlib import closing
from typing import TYPE_CHECKING

from mikemol.memres import mem_db, mem_project

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_MB = 1024 * 1024
_USAGE = 2
_PROJECTED = '{\n  "claims": {},\n  "file": 128\n}\n'


def _store(tmp_path: Path, peak_mb: int | None) -> Path:
    """Build a store holding one file-resolution observation, or none.

    Returns:
        The database path.

    """
    db = tmp_path / "mem.sqlite"
    with closing(mem_db.connect(db)) as conn:
        if peak_mb is not None:
            mem_db.record(conn, [("p", "file", "a", "a__calc", peak_mb * _MB)])
    return db


def test_render_is_the_sorted_manifest_json_with_a_trailing_newline(tmp_path: Path) -> None:
    """The projection is exactly the manifest, two-space indented, keys sorted."""
    assert mem_project.render(_store(tmp_path, 100), "p") == _PROJECTED


def test_render_of_a_project_with_no_observations_is_empty_not_a_false_manifest(
    tmp_path: Path,
) -> None:
    """No observations render as the empty string, never an empty object."""
    assert not mem_project.render(_store(tmp_path, None), "p")
    assert not mem_project.render(_store(tmp_path, 100), "nobody")


def test_main_writes_the_projection_and_says_what_it_projected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The file holds the projection; stderr names the project, target and resolution defaults."""
    db = _store(tmp_path, 100)
    out = tmp_path / "mem.json"
    assert mem_project.main([str(db), "p", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == _PROJECTED
    assert capsys.readouterr().err == f"mem-project: p -> {out} ({{'file': 128}})\n"


def test_main_check_passes_on_a_fresh_projection_and_writes_nothing(tmp_path: Path) -> None:
    """With `--check` a matching file is exit 0 and the file is left byte-identical."""
    db = _store(tmp_path, 100)
    out = tmp_path / "mem.json"
    out.write_text(_PROJECTED, encoding="utf-8")
    assert mem_project.main([str(db), "p", str(out), "--check"]) == 0
    assert out.read_text(encoding="utf-8") == _PROJECTED


def test_main_check_names_a_stale_or_missing_projection_and_exits_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A differing or absent file is exit 1 with the regenerate command, and is not rewritten."""
    db = _store(tmp_path, 100)
    out = tmp_path / "mem.json"
    assert mem_project.main([str(db), "p", str(out), "--check"]) == 1
    assert not out.exists()
    out.write_text('{"file": 64}\n', encoding="utf-8")
    assert mem_project.main([str(db), "p", str(out), "--check"]) == 1
    assert out.read_text(encoding="utf-8") == '{"file": 64}\n'
    assert capsys.readouterr().err.splitlines()[:2] == [
        f"mem-project: {out} is STALE against {db} - regenerate with:",
        f"  mikemol-mem-project {db} p {out}",
    ]


def test_main_leaves_the_output_alone_when_there_are_no_observations(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With nothing to project, an existing `mem.json` survives and the exit is 0."""
    db = _store(tmp_path, None)
    out = tmp_path / "mem.json"
    out.write_text("kept\n", encoding="utf-8")
    assert mem_project.main([str(db), "p", str(out)]) == 0
    assert mem_project.main([str(db), "p", str(out), "--check"]) == 0
    assert out.read_text(encoding="utf-8") == "kept\n"
    assert capsys.readouterr().err.count(f"no observations in {db} - leaving {out} alone") == _USAGE


def test_main_refuses_too_few_arguments_with_a_usage_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fewer than `<db> <project> <out.json>` is exit 2 with usage on stderr."""
    assert mem_project.main(["db", "p"]) == _USAGE
    err = capsys.readouterr().err
    assert err == "usage: mikemol-mem-project <db> <project> <out.json> [--check]\n"

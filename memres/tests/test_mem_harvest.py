# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mem_harvest`: peaks found under an output tree fold into the store."""

from __future__ import annotations

from contextlib import closing
from typing import TYPE_CHECKING, cast

from mikemol.memres import mem_db, mem_harvest

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_MB = 1024 * 1024
_USAGE = 2


def _peak(directory: Path, name: str, text: str) -> Path:
    """Plant a peak file (making its directory).

    Returns:
        The file's path.

    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def _rows(db: Path) -> list[tuple[str, str, str, str, int, str]]:
    """Read every stored observation.

    Returns:
        `(project, resolution, claim, cell, bytes, run)`, sorted.

    """
    with closing(mem_db.connect(db)) as conn:
        return cast(
            "list[tuple[str, str, str, str, int, str]]",
            conn.execute(
                "SELECT project, resolution, claim, cell, bytes, run FROM peak ORDER BY cell",
            ).fetchall(),
        )


def test_peaks_for_reads_only_this_projects_readable_measurements(tmp_path: Path) -> None:
    """Other projects, foreign stems, `unavailable:*`, zero and unreadable files are skipped."""
    mine = tmp_path / "bazel-out" / "k8" / "paperkit_proj"
    by_dir = tmp_path / "bazel-out" / "proj" / "deep"
    _peak(mine, "a__calc.peak", str(100 * _MB))
    _peak(mine, "b__dcalc.peak", str(300 * _MB))
    _peak(by_dir, "c__site1.peak", str(50 * _MB))
    _peak(mine, "foreign.peak", str(9 * _MB))
    _peak(mine, "gone__calc.peak", "unavailable:absent")
    _peak(mine, "zero__calc.peak", "0")
    _peak(tmp_path / "bazel-out" / "paperkit_other", "z__calc.peak", str(9 * _MB))
    (mine / "dir__calc.peak").mkdir()
    assert mem_harvest.peaks_for("proj", tmp_path / "bazel-out") == {
        ("file", "a", "a__calc"): 100.0,
        ("def", "b", "b__dcalc"): 300.0,
        ("def", "c", "c__site1"): 50.0,
    }


def test_peaks_for_keeps_the_worst_reading_of_one_cell(tmp_path: Path) -> None:
    """A cell seen twice reports its MAX, not its last or its mean."""
    tree = tmp_path / "bazel-out"
    _peak(tree / "one" / "paperkit_proj", "a__calc.peak", str(100 * _MB))
    _peak(tree / "two" / "paperkit_proj", "a__calc.peak", str(200 * _MB))
    _peak(tree / "three" / "paperkit_proj", "a__calc.peak", str(50 * _MB))
    assert mem_harvest.peaks_for("proj", tree) == {("file", "a", "a__calc"): 200.0}


def test_deposit_records_observations_and_never_lowers_a_stored_peak(tmp_path: Path) -> None:
    """The store gets one row per cell, tagged with the run; a smaller later deposit is a no-op."""
    db = tmp_path / "mem.sqlite"
    assert mem_harvest.deposit(db, "p", {("file", "a", "a__calc"): 100.0}, run="r1") == 1
    assert mem_harvest.deposit(db, "p", {("file", "a", "a__calc"): 40.0}, run="r2") == 1
    assert _rows(db) == [("p", "file", "a", "a__calc", 100 * _MB, "r1")]


def test_main_harvests_into_the_default_store_and_reports_what_it_deposited(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With only a project dir, the tree and store are siblings of it; the run id defaults to ''."""
    project_dir = tmp_path / "repo" / "proj"
    project_dir.mkdir(parents=True)
    tree = tmp_path / "repo" / "bazel-out" / "paperkit_proj"
    _peak(tree, "a__calc.peak", str(100 * _MB))
    _peak(tree, "b__dcalc.peak", str(300 * _MB))
    assert mem_harvest.main([str(project_dir)]) == 0
    assert _rows(tmp_path / "repo" / "mem.sqlite") == [
        ("proj", "file", "a", "a__calc", 100 * _MB, ""),
        ("proj", "def", "b", "b__dcalc", 300 * _MB, ""),
    ]
    assert capsys.readouterr().err == (
        f"mem-harvest: proj: 2 observation(s) over ['def', 'file'] -> "
        f"{tmp_path / 'repo' / 'mem.sqlite'}\n"
    )


def test_main_takes_the_tree_store_and_run_from_its_options(tmp_path: Path) -> None:
    """`--bazel-out`, `--db` and `--run` override the defaults."""
    project_dir = tmp_path / "repo" / "proj"
    project_dir.mkdir(parents=True)
    tree = tmp_path / "elsewhere"
    _peak(tree / "paperkit_proj", "a__calc.peak", str(100 * _MB))
    db = tmp_path / "custom.sqlite"
    argv = [str(project_dir), "--bazel-out", str(tree), "--db", str(db), "--run", "r9"]
    assert mem_harvest.main(argv) == 0
    assert _rows(db) == [("proj", "file", "a", "a__calc", 100 * _MB, "r9")]
    assert not (tmp_path / "repo" / "mem.sqlite").exists()


def test_main_ignores_an_option_given_without_a_value(tmp_path: Path) -> None:
    """A trailing `--bazel-out` with no value falls back to the default tree."""
    project_dir = tmp_path / "repo" / "proj"
    project_dir.mkdir(parents=True)
    _peak(tmp_path / "repo" / "bazel-out" / "paperkit_proj", "a__calc.peak", str(100 * _MB))
    assert mem_harvest.main([str(project_dir), "--bazel-out"]) == 0
    assert len(_rows(tmp_path / "repo" / "mem.sqlite")) == 1


def test_main_names_the_paperkit_directory_root_and_harvests_beside_itself(
    tmp_path: Path,
) -> None:
    """A project dir named `paperkit` is project `root`, with the tree and store inside it."""
    project_dir = tmp_path / "paperkit"
    _peak(project_dir / "bazel-out" / "paperkit_root", "a__calc.peak", str(100 * _MB))
    assert mem_harvest.main([str(project_dir)]) == 0
    assert _rows(project_dir / "mem.sqlite") == [("root", "file", "a", "a__calc", 100 * _MB, "")]


def test_main_without_a_tree_or_without_peaks_is_not_an_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Absent measurement exits 0 and says why, and writes no store."""
    project_dir = tmp_path / "repo" / "proj"
    project_dir.mkdir(parents=True)
    assert mem_harvest.main([str(project_dir)]) == 0
    assert capsys.readouterr().err == (
        f"mem-harvest: no output tree at {tmp_path / 'repo' / 'bazel-out'} - nothing to harvest\n"
    )
    (tmp_path / "repo" / "bazel-out").mkdir()
    assert mem_harvest.main([str(project_dir)]) == 0
    assert capsys.readouterr().err == (
        "mem-harvest: proj: no readable peaks (run under --config=memobserve first)\n"
    )
    assert not (tmp_path / "repo" / "mem.sqlite").exists()


def test_main_refuses_no_project_dir_with_a_usage_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No arguments is exit 2 with usage on stderr."""
    assert mem_harvest.main([]) == _USAGE
    assert capsys.readouterr().err == (
        "usage: mikemol-mem-harvest <project-dir> [--db FILE] [--bazel-out DIR] [--run ID]\n"
    )

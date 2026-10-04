# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mem_converge`: a planted external tree says which projects have converged."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.memres import mem_converge

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_USAGE = 2
_SIZED = 'pk_eval(name = "c__s1", site = "content-:gen.py:_delta(\\"paper\\")", mem = 128)\n'
_FLOOR = 'pk_eval(name = "c__s2", site = "x", mem = 0)\n'
_UNSET = 'pk_eval(name = "c__s3", site = "x")\n'


def _project(tmp_path: Path, repo: str, cells: str) -> Path:
    """Plant an external repo directory holding a BUILD.bazel of `cells`.

    Returns:
        The external directory (the parent of the repo).

    """
    external = tmp_path / "external"
    (external / repo).mkdir(parents=True, exist_ok=True)
    (external / repo / "BUILD.bazel").write_text(cells, encoding="utf-8")
    return external


def _declare(root: Path, name: str, path: str) -> None:
    """Declare project `name` at `path` in the root's MODULE.bazel."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / "MODULE.bazel").open("a", encoding="utf-8") as module:
        module.write(f'bib.project(name = "paperkit_{name}", project = "{path}")\n')


def _manifest(root: Path, rel: str, text: str) -> None:
    """Plant a manifest file at `rel` under `root`."""
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def test_survey_counts_cells_floor_cells_and_the_def_bucket(tmp_path: Path) -> None:
    """A site string holding `)` still reaches its `mem` attr; mem 0 and no mem are at the floor."""
    external = _project(tmp_path, "+bib+paperkit_library", _SIZED + _FLOOR + _UNSET)
    root = tmp_path / "root"
    _declare(root, "library", "paperkit/library")
    _manifest(root, "paperkit/library/mem.json", '{"def": 64}')
    assert mem_converge.survey(external, root) == [("library", 3, 2, 64)]


def test_survey_skips_repos_without_a_build_file_or_without_a_grid(tmp_path: Path) -> None:
    """Eligibility first: no BUILD.bazel, or a BUILD with no pk_eval cell, owes no def bucket."""
    external = _project(tmp_path, "+bib+paperkit_nogrid", 'pk_calc(name = "x")\n')
    (external / "+bib+paperkit_nobuild").mkdir()
    (external / "+bib+paperkit_nobuild" / "not-a-build.txt").write_text("x", encoding="utf-8")
    assert mem_converge.survey(external, tmp_path / "root") == []


def test_survey_reads_no_bucket_from_a_missing_broken_or_non_integer_manifest(
    tmp_path: Path,
) -> None:
    """The def bucket is None unless the manifest is JSON holding an integer `def`."""
    external = _project(tmp_path, "+bib+paperkit_a", _SIZED)
    _project(tmp_path, "+bib+paperkit_b", _SIZED)
    _project(tmp_path, "+bib+paperkit_c", _SIZED)
    root = tmp_path / "root"
    for name in "abc":
        _declare(root, name, name)
    _manifest(root, "b/mem.json", "not json")
    _manifest(root, "c/mem.json", '{"def": "big"}')
    assert mem_converge.survey(external, root) == [
        ("a", 1, 0, None),
        ("b", 1, 0, None),
        ("c", 1, 0, None),
    ]


def test_survey_puts_the_root_project_manifest_at_the_roots_own_mem_json(tmp_path: Path) -> None:
    """MODULE.bazel's `project = "."` is the root's `mem.json`, not `./mem.json` under a name."""
    external = _project(tmp_path, "+bib+paperkit_root", _SIZED)
    root = tmp_path / "root"
    _declare(root, "root", ".")
    _manifest(root, "mem.json", '{"def": 256}')
    assert mem_converge.survey(external, root) == [("root", 1, 0, 256)]


def test_survey_names_an_undeclared_project_and_falls_back_to_its_name_as_a_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An undeclared project is a finding about the owner: warned on stderr, name used as path."""
    external = _project(tmp_path, "+bib+paperkit_lone", _SIZED)
    root = tmp_path / "root"
    _manifest(root, "lone/mem.json", '{"def": 32}')
    assert mem_converge.survey(external, root) == [("lone", 1, 0, 32)]
    assert capsys.readouterr().err == (
        "mem-converge: lone is not declared in MODULE.bazel - falling back to its name as a "
        "path, which is the very conflation this function exists to avoid\n"
    )


def test_main_reports_a_converged_project_and_exits_zero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A def bucket and no floor cell reads converged; `--check` is accepted and ignored."""
    external = _project(tmp_path, "+bib+paperkit_library", _SIZED)
    root = tmp_path / "root"
    _declare(root, "library", "paperkit/library")
    _manifest(root, "paperkit/library/mem.json", '{"def": 64}')
    assert mem_converge.main([str(external), str(root), "--check"]) == 0
    captured = capsys.readouterr()
    assert captured.out == (
        "  library     cells=1       at-floor=0       def=64     converged\n"
        "mem-converge: all 1 grid project(s) converged\n"
    )
    assert not captured.err


def test_main_names_the_projects_that_have_not_converged_and_exits_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A floor cell or a missing def bucket is NOT CONVERGED, with the remedy on stderr."""
    external = _project(tmp_path, "+bib+paperkit_library", _SIZED + _FLOOR)
    root = tmp_path / "root"
    _declare(root, "library", "paperkit/library")
    assert mem_converge.main([str(external), str(root)]) == 1
    captured = capsys.readouterr()
    assert captured.out == (
        "  library     cells=2       at-floor=1       def=MISSING NOT CONVERGED\n"
    )
    assert captured.err == (
        "mem-converge: 1 of 1 project(s) have NOT converged: library - run an observe pass "
        "(--config=memobserve), then mikemol-mem-harvest + mikemol-mem-project, then refetch\n"
    )


def test_main_exits_two_when_nothing_was_asked_or_nothing_has_a_grid(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No directory prints usage; a directory with no grid says there is nothing to converge."""
    assert mem_converge.main(["--check"]) == _USAGE
    err = capsys.readouterr().err
    assert err == "usage: mem_converge.py <bazel-external-dir> [<root>] [--check]\n"
    assert mem_converge.main([str(tmp_path)]) == _USAGE
    err = capsys.readouterr().err
    assert err == "mem-converge: no project has a grid - nothing to converge\n"

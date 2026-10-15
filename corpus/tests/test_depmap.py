# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the dependency map (mtools:W1251): four edge kinds read from the tree.

⚑ THE CONTROLS ARE WHAT MUST NOT BECOME AN EDGE: a standard-library import, a path-like word in a
docstring, prose that merely contains `.md`, a name in code that is not a comment or string, and
a call whose argv is a variable. Each is planted beside the edge it must not be confused with.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.corpus import depmap

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_REFUSALS = 3
_MODULE = '''\
"""Reads `docs/guide.md` and speaks of nemik."""

import os
import rdflib
from mikemol.pathsforward import cli


def run(argv):
    import dateutil

    subprocess.run(["/usr/bin/git", "status"])
    subprocess.run(argv)
    subprocess.run(["-C", "repo", "status"])
    shutil.which("opa")
    return "x/paths-forward.json", "hello.md world", os, cli, rdflib, dateutil
'''


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "fleet"
    (root / "pkg" / "src").mkdir(parents=True)
    (root / "pkg" / "tests").mkdir()
    (root / "pkg" / "pyproject.toml").write_text("", encoding="utf-8")
    (root / "pkg" / "src" / "a.py").write_text(_MODULE, encoding="utf-8")
    (root / "pkg" / "tests" / "test_a.py").write_text("import pytest\n", encoding="utf-8")
    (root / "loose.py").write_text("# nemik in a comment\nnemik = 1\n", encoding="utf-8")
    return root


def _rows(edges: list[depmap.Edge]) -> set[tuple[str, str, str, bool]]:
    return {(e.kind, e.source, e.target, e.deferred) for e in edges}


def test_owner_names_the_distribution_and_leaves_other_names_whole() -> None:
    """The shared namespace collapses to `mikemol.<dist>`; anything else to its top-level name."""
    assert depmap.owner("mikemol.pathsforward.cli") == "mikemol.pathsforward"
    assert depmap.owner("mikemol.pathsforward") == "mikemol.pathsforward"
    assert depmap.owner("mikemol") == "mikemol"
    assert depmap.owner("rdflib.graph") == "rdflib"


def test_imports_are_split_into_module_level_and_deferred_and_drop_the_standard_library(
    tmp_path: Path,
) -> None:
    """`os` is dropped; `dateutil` is inside a function, so deferred; the rest are eager."""
    got = _rows(depmap.derive([_repo(tmp_path)]))
    src = "fleet/pkg"
    assert ("import", src, "mikemol.pathsforward", False) in got
    assert ("import", src, "rdflib", False) in got
    assert ("import", src, "dateutil", True) in got
    assert not any(row[2] == "os" for row in got)
    assert ("import", f"{src}:tests", "pytest", False) in got


def test_a_file_directly_under_the_repo_is_labelled_by_the_repo_alone(tmp_path: Path) -> None:
    """`loose.py` is in no dist, so its source is `fleet`, and a tests directory adds `:tests`."""
    sources = {e.source for e in depmap.derive([_repo(tmp_path)], "nemik")}
    assert "fleet" in sources
    assert "fleet/pkg" in sources
    assert "fleet/pkg:tests" in sources


def test_a_literal_argv_names_its_executable_and_a_variable_argv_names_nothing(
    tmp_path: Path,
) -> None:
    """`git` comes from the literal list by basename and `opa` from `which`; `argv` is blind."""
    got = {(e.kind, e.target) for e in depmap.derive([_repo(tmp_path)]) if e.kind == "subprocess"}
    assert got == {("subprocess", "git"), ("subprocess", "opa")}


def test_a_path_constant_is_an_edge_and_a_docstring_or_prose_is_not(tmp_path: Path) -> None:
    """`paths-forward.json` is named by a constant; the docstring's guide.md and prose are not."""
    paths = {e.target for e in depmap.derive([_repo(tmp_path)]) if e.kind == "path"}
    assert paths == {"x/paths-forward.json"}


def test_a_mention_is_a_comment_or_string_token_and_not_a_name_in_code(tmp_path: Path) -> None:
    """The docstring and the comment name nemik; the variable `nemik = 1` is not a mention."""
    root = _repo(tmp_path)
    edges = depmap.derive([root], "NEMIK")
    hits = {(e.source, e.file, e.line) for e in edges if e.kind == "mention"}
    assert hits == {("fleet/pkg", "pkg/src/a.py", 1), ("fleet", "loose.py", 1)}
    assert {e.target for e in edges if e.kind == "mention"} == {"nemik"}
    assert not any(e.kind == "mention" for e in depmap.derive([root]))


def test_aggregate_counts_each_edge_and_marks_a_purely_deferred_import() -> None:
    """Two occurrences count two; an import seen only inside a definition ends in `deferred`."""
    edges = [
        depmap.Edge("path", "r", "a.py", 1, "q.json"),
        depmap.Edge("path", "r", "a.py", 2, "q.json"),
        depmap.Edge("import", "r", "a.py", 0, "lazy", deferred=True),
        depmap.Edge("import", "r", "a.py", 0, "both", deferred=True),
        depmap.Edge("import", "r", "b.py", 0, "both"),
    ]
    assert depmap.aggregate(edges) == [
        "2\timport\tr\tboth",
        "1\timport\tr\tlazy\tdeferred",
        "2\tpath\tr\tq.json",
    ]


def test_occurrences_carry_file_line_and_the_deferred_mark() -> None:
    """One row per occurrence, `file:line`, with `deferred` only on a deferred edge."""
    edges = [
        depmap.Edge("subprocess", "r", "a.py", 7, "git"),
        depmap.Edge("import", "r", "a.py", 0, "lazy", deferred=True),
    ]
    assert depmap.occurrences(edges) == [
        "subprocess\tr\ta.py:7\tgit",
        "import\tr\ta.py:0\tlazy\tdeferred",
    ]


def test_main_prints_the_blind_spot_first_and_the_aggregate_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first lines say what the reader cannot see; `--rows` switches to per-occurrence rows."""
    root = str(_repo(tmp_path))
    assert depmap.main([root]) == 0
    aggregated = capsys.readouterr().out
    assert aggregated.startswith("# cannot see:")
    assert "1\tsubprocess\tfleet/pkg\tgit\n" in aggregated
    assert depmap.main(["--rows", root]) == 0
    rows = capsys.readouterr().out
    assert "subprocess\tfleet/pkg\tpkg/src/a.py:11\tgit\n" in rows
    assert depmap.main(["--mention", "nemik", root]) == 0
    assert "mention\tfleet" in capsys.readouterr().out


def test_main_refuses_a_missing_root_a_dangling_mention_and_a_non_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each usage error exits 2 and prints the usage line, and prints no map."""
    nothing = str(tmp_path / "absent")
    assert depmap.main([]) == depmap.EXIT_USAGE
    assert depmap.main(["--mention"]) == depmap.EXIT_USAGE
    assert depmap.main([nothing]) == depmap.EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.err.count("usage:") == _REFUSALS
    assert not captured.out

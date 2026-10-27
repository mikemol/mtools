# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`graph --files` checks the graph over what git tracks: a new tracked module fails first (W2011).

⚑ THE CONTROLS: a tracked module the committed graph does not name is STALE and named; an
untracked module on disk is not in the graph at all (the sandbox cannot see it); the directory walk
is what it was without the flag; git that cannot answer is exit 2, never an empty list; and tests
and the conftest come from the listed names, not the disk.
"""

import subprocess
from pathlib import Path

from mikemol.importdag import graph, trackednames

_PACKAGE = "mikemol.demo"
_STALE = 1
_NO_GIT = 2


def _repo(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "src" / "mikemol" / "demo").mkdir(parents=True)
    (dist / "tests").mkdir()
    (dist / "src" / "mikemol" / "demo" / "alpha.py").write_text("X = 1\n", encoding="utf-8")
    (dist / "tests" / "test_alpha.py").write_text("from mikemol.demo import alpha\n", "utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return dist


def _args(dist: Path, *flags: str) -> list[str]:
    return ["--dist", str(dist), "--package", _PACKAGE, *flags]


def test_the_listed_names_pick_modules_and_tests_and_nothing_else() -> None:
    """Under src/<package>/ and directly under tests/ only; a nested test and a non-test are out."""
    names = [
        "src/mikemol/demo/__init__.py",
        "src/mikemol/demo/alpha.py",
        "src/mikemol/other/beta.py",
        "tests/test_alpha.py",
        "tests/sub/test_deep.py",
        "tests/helper.py",
        "README.md",
    ]
    assert graph.listed_modules(names, _PACKAGE) == [
        "src/mikemol/demo/__init__.py",
        "src/mikemol/demo/alpha.py",
    ]
    assert graph.listed_tests(names) == ["tests/test_alpha.py"]


def test_a_tracked_module_the_graph_does_not_name_is_stale_and_named(tmp_path: Path) -> None:
    """A staged new module fails the --files check before any gate would."""
    dist = _repo(tmp_path)
    assert graph.main(_args(dist, "--write", "--files")) == 0
    assert graph.main(_args(dist, "--check", "--files")) == 0
    new = dist / "src" / "mikemol" / "demo" / "gamma.py"
    new.write_text("Y = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    assert graph.main(_args(dist, "--check", "--files")) == _STALE


def test_an_untracked_module_is_not_in_the_graph_the_sandbox_cannot_see(tmp_path: Path) -> None:
    """On disk but not tracked: the --files graph ignores it, the directory walk does not."""
    dist = _repo(tmp_path)
    assert graph.main(_args(dist, "--write", "--files")) == 0
    (dist / "src" / "mikemol" / "demo" / "ghost.py").write_text("Z = 3\n", encoding="utf-8")
    assert graph.main(_args(dist, "--check", "--files")) == 0
    assert graph.main(_args(dist, "--check")) == _STALE


def test_git_that_cannot_answer_is_exit_two_and_not_an_empty_list(tmp_path: Path) -> None:
    """A directory outside any repository has no tracked files to list."""
    loose = tmp_path / "loose"
    (loose / "src").mkdir(parents=True)
    assert trackednames.of(loose) is None
    assert graph.main(_args(loose, "--check", "--files")) == _NO_GIT


def test_the_tracked_names_are_sorted_dist_relative_and_include_staged_files(
    tmp_path: Path,
) -> None:
    """`git ls-files` for the directory: a staged new file counts."""
    dist = _repo(tmp_path)
    got = trackednames.of(dist)
    assert got == ["src/mikemol/demo/alpha.py", "tests/test_alpha.py"]

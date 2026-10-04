# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `witness_reach`: witnesses load under real child interpreters in a fake repo."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.importdag import dagnames

from mikemol.gatecheck import witness_reach

if TYPE_CHECKING:
    import pytest

_WITNESSES = {
    "good.py": "VALUE = 1\n",
    "uses_sibling.py": "import good\n\nVALUE = good.VALUE\n",
    "needs_dep.py": "import absent_dependency_for_witness_reach\n",
    "silent_exit.py": "raise SystemExit(3)\n",
    "wordy.py": 'raise RuntimeError("' + "x" * 200 + '")\n',
    "through_dagnames.py": (
        "import sys\n\n"
        'assert "mikemol.importdag.dagnames" in sys.modules, "child skipped the dagnames bind"\n'
    ),
    "__init__.py": "raise SystemExit(9)\n",
}


def _repo(tmp_path: Path, project: str = "proj", only: tuple[str, ...] = ()) -> Path:
    """Build a repository with one project whose checks directory holds the witnesses.

    Returns:
        The repository root.

    """
    checks = tmp_path / project / "checks"
    checks.mkdir(parents=True)
    for name, text in _WITNESSES.items():
        if not only or name in only:
            (checks / name).write_text(text, encoding="utf-8")
    return tmp_path


def test_trees_finds_each_projects_checks_directory_sorted(tmp_path: Path) -> None:
    """Only directories named checks directly inside a child of the root are found."""
    _repo(tmp_path, "zeta")
    _repo(tmp_path, "alpha")
    (tmp_path / "beta").mkdir()
    (tmp_path / "gamma").mkdir()
    (tmp_path / "gamma" / "checks").write_text("a file, not a tree\n", encoding="utf-8")
    assert witness_reach.trees(tmp_path) == [
        tmp_path / "alpha" / "checks",
        tmp_path / "zeta" / "checks",
    ]


def test_child_environment_leads_with_the_checks_directory(tmp_path: Path) -> None:
    """The checks directory comes first, then the roots that dagnames supplies."""
    tree = tmp_path / "proj" / "checks"
    env = witness_reach.child_environment(tree)
    base = dagnames.child_env(tree.parent)["PYTHONPATH"]
    assert env["PYTHONPATH"] == os.pathsep.join([str(tree), base])
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(tree)


def test_probe_passes_a_witness_that_loads(tmp_path: Path) -> None:
    """A loadable witness is return code zero with nothing to say."""
    tree = _repo(tmp_path, only=("good.py",)) / "proj" / "checks"
    assert witness_reach.probe(tree, "good.py") == (0, "")


def test_probe_resolves_a_sibling_import_on_the_script_route(tmp_path: Path) -> None:
    """A witness importing its neighbour loads, because the checks directory leads the path."""
    tree = _repo(tmp_path) / "proj" / "checks"
    assert witness_reach.probe(tree, "uses_sibling.py") == (0, "")


def test_probe_reports_the_last_line_of_a_missing_module(tmp_path: Path) -> None:
    """An unloadable witness is a nonzero code and the last line of the child's traceback."""
    tree = _repo(tmp_path) / "proj" / "checks"
    rc, last = witness_reach.probe(tree, "needs_dep.py")
    assert rc == 1
    assert last == "ModuleNotFoundError: No module named 'absent_dependency_for_witness_reach'"


def test_probe_reports_empty_when_the_child_says_nothing(tmp_path: Path) -> None:
    """A silent failing child is its return code and an empty line."""
    tree = _repo(tmp_path) / "proj" / "checks"
    assert witness_reach.probe(tree, "silent_exit.py") == (3, "")


def test_probe_cuts_a_long_last_line(tmp_path: Path) -> None:
    """The reported line is cut at the tail width."""
    tree = _repo(tmp_path) / "proj" / "checks"
    rc, last = witness_reach.probe(tree, "wordy.py")
    assert rc == 1
    assert len(last) == witness_reach.TAIL_WIDTH
    assert last.startswith("RuntimeError: xxx")


def test_probe_child_imports_through_the_dagnames_module(tmp_path: Path) -> None:
    """The child has bound mikemol.importdag.dagnames before the witness runs."""
    tree = _repo(tmp_path) / "proj" / "checks"
    assert witness_reach.probe(tree, "through_dagnames.py") == (0, "")


def test_parse_args_defaults_to_the_cwd_and_every_project(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no arguments the root is the current directory and no project is selected."""
    monkeypatch.chdir(Path(__file__).parent)
    opts = witness_reach.parse_args([])
    assert opts.root == Path.cwd()
    assert opts.projects == []


def test_parse_args_reads_root_and_projects() -> None:
    """The root option and the positional project names are both read."""
    opts = witness_reach.parse_args(["--root", "/x", "a", "b"])
    assert opts.root == Path("/x")
    assert opts.projects == ["a", "b"]


def test_main_reports_a_clean_tree_and_returns_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every witness loading is exit zero, with the count line and no failure marker."""
    root = _repo(tmp_path, only=("good.py", "uses_sibling.py"))
    assert witness_reach.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "proj/checks — 2 witnesses" in out
    assert "2 of 2 load cleanly under a bare interpreter · 0 FAIL" in out
    assert "XX" not in out


def test_main_names_each_failure_and_returns_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failing witness is listed with its last line and the exit is one; init is skipped."""
    root = _repo(tmp_path, only=("good.py", "needs_dep.py", "__init__.py"))
    assert witness_reach.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "proj/checks — 2 witnesses" in out
    assert "  XX needs_dep.py" in out
    assert "No module named 'absent_dependency_for_witness_reach'" in out
    assert "1 of 2 load cleanly under a bare interpreter · 1 FAIL" in out
    assert "each failure is a gate red waiting for a sweep to reach it." in out


def test_main_selects_only_the_named_projects(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A named project is probed and the others are not, even when they would fail."""
    _repo(tmp_path, "clean", only=("good.py",))
    _repo(tmp_path, "broken", only=("needs_dep.py",))
    assert witness_reach.main(["--root", str(tmp_path), "clean"]) == 0
    out = capsys.readouterr().out
    assert "clean/checks" in out
    assert "broken" not in out


def test_main_defaults_to_the_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --root the repository is the current directory."""
    _repo(tmp_path, only=("good.py",))
    monkeypatch.chdir(tmp_path)
    assert witness_reach.main([]) == 0
    assert "1 of 1 load cleanly" in capsys.readouterr().out


def test_module_runs_as_a_script_with_the_exit_code(tmp_path: Path) -> None:
    """Run as a module, the exit status is the failure verdict."""
    root = _repo(tmp_path, only=("needs_dep.py",))
    env = dagnames.child_env(root)
    r = subprocess.run(
        [sys.executable, "-m", "mikemol.gatecheck.witness_reach", "--root", str(root)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r.returncode == 1
    assert "0 of 1 load cleanly" in r.stdout

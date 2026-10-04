# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `dagnames`: importable names from a partition, by real child interpreters."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.importdag import dagnames
from mikemol.importdag.dagnames import (
    CHILD_PRELUDE,
    PACKAGE_ROOT,
    Options,
    child_env,
    literal,
    main,
    module_names,
    parse_args,
    to_module,
    unresolvable,
)

if TYPE_CHECKING:
    import pytest

COMPONENTS = """\
OTHER = {"x": ["nope.py"]}

COMPONENTS = {
    "core": ["a.py", "tools/sub.py"],
    "tests": ["t.py"],
    "odd": "not-a-list",
}

AFTER = {"y": ["z.py"]}
"""


def _engine(tmp_path: Path) -> Path:
    """Build a small engine named `eng` whose modules all import.

    Returns:
        The engine directory.

    """
    eng = tmp_path / "eng"
    (eng / "tools").mkdir(parents=True)
    (eng / "components.bzl").write_text(COMPONENTS, encoding="utf-8")
    for rel in ("a.py", "tools/sub.py", "t.py"):
        (eng / rel).write_text("VALUE = 1\n", encoding="utf-8")
    return eng


def test_literal_reads_the_named_dict_only(tmp_path: Path) -> None:
    """The dict bound to the name is read, with a non-list value dropped."""
    eng = _engine(tmp_path)
    got = literal(eng / "components.bzl", "COMPONENTS")
    assert got == {"core": ["a.py", "tools/sub.py"], "tests": ["t.py"]}


def test_literal_of_a_non_dict_is_empty(tmp_path: Path) -> None:
    """A binding that is not a dict yields an empty mapping."""
    path = tmp_path / "x.bzl"
    path.write_text("NAME = {\n1, 2\n}\n", encoding="utf-8")
    assert literal(path, "NAME") == {}


def test_to_module_dots_the_path() -> None:
    """A path becomes the dotted name, `.py` removed."""
    assert to_module("bib.py") == "bib"
    assert to_module("tools/vfs.py") == "tools.vfs"


def test_to_module_qualifies_a_subpackage_only() -> None:
    """`pkg` qualifies a subpackage name and leaves a top-level name bare."""
    assert to_module("tools/vfs.py", "paperkit") == "paperkit.tools.vfs"
    assert to_module("bib.py", "paperkit") == "bib"


def test_module_names_are_sorted_and_skippable(tmp_path: Path) -> None:
    """Every component's modules are named; `skip` drops whole components."""
    eng = _engine(tmp_path)
    assert module_names(eng) == ["a", "t", "tools.sub"]
    assert module_names(eng, skip=("tests",)) == ["a", "tools.sub"]
    assert module_names(eng, skip=("tests",), pkg="eng") == ["a", "eng.tools.sub"]


def test_child_env_orders_the_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The engine, its parent and the package location come first, then the inherited path."""
    monkeypatch.setenv("PYTHONPATH", "inherited")
    eng = tmp_path / "eng"
    want = os.pathsep.join([str(eng), str(tmp_path), str(PACKAGE_ROOT), "inherited"])
    assert child_env(eng)["PYTHONPATH"] == want


def test_child_env_without_an_inherited_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no inherited path the value is only the three roots; the rest is carried over."""
    monkeypatch.delenv("PYTHONPATH", raising=False)
    monkeypatch.setenv("IMPORTDAG_MARK", "kept")
    eng = tmp_path / "eng"
    env = child_env(eng)
    assert env["PYTHONPATH"] == os.pathsep.join([str(eng), str(tmp_path), str(PACKAGE_ROOT)])
    assert env["IMPORTDAG_MARK"] == "kept"


def test_prelude_mutates_no_path() -> None:
    """The child imports this module by its package name and edits no `sys.path`."""
    assert "sys.path" not in CHILD_PRELUDE
    assert "import mikemol.importdag.dagnames" in CHILD_PRELUDE
    assert dagnames.__name__ == "mikemol.importdag.dagnames"


def test_unresolvable_passes_importable_names(tmp_path: Path) -> None:
    """Each real child imports its name, so nothing is reported."""
    eng = _engine(tmp_path)
    assert unresolvable(["a", "eng.tools.sub", "t"], eng) == []


def test_unresolvable_reports_the_failing_name_and_why(tmp_path: Path) -> None:
    """Only the name that does not import is reported, with its child's last line."""
    eng = _engine(tmp_path)
    got = unresolvable(["a", "missing"], eng)
    assert [n for n, _ in got] == ["missing"]
    assert got[0][1].startswith("ModuleNotFoundError: No module named 'missing'")


def test_unresolvable_cuts_the_reason_at_96_characters(tmp_path: Path) -> None:
    """A long failure line is cut to 96 characters."""
    eng = _engine(tmp_path)
    (eng / "long.py").write_text(f"raise RuntimeError({'x' * 200!r})\n", encoding="utf-8")
    ((_, why),) = unresolvable(["long"], eng)
    assert why == "RuntimeError: " + "x" * 82


def test_unresolvable_reports_an_empty_reason_for_a_silent_exit(tmp_path: Path) -> None:
    """A child that exits non-zero without output is reported with an empty reason."""
    eng = _engine(tmp_path)
    (eng / "quiet.py").write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
    assert unresolvable(["quiet"], eng) == [("quiet", "")]


def test_child_binds_this_module_through_the_environment(tmp_path: Path) -> None:
    """In the child this module is already loaded, and PYTHONPATH carries the roots."""
    eng = _engine(tmp_path)
    probe = (
        "import os, sys\n"
        "bound = 'mikemol.importdag.dagnames' in sys.modules\n"
        "has_env = bool(os.environ.get('PYTHONPATH'))\n"
        "raise RuntimeError(f'bound={bound} env={has_env}')\n"
    )
    (eng / "probe.py").write_text(probe, encoding="utf-8")
    ((_, why),) = unresolvable(["probe"], eng)
    assert why == "RuntimeError: bound=True env=True"


def test_unresolvable_runs_the_child_in_root(tmp_path: Path) -> None:
    """`root` is the child's working directory, and defaults to the engine's parent."""
    eng = _engine(tmp_path)
    (eng / "where.py").write_text("import os\nraise RuntimeError(os.getcwd())\n", encoding="utf-8")
    other = tmp_path / "other"
    other.mkdir()
    assert unresolvable(["where"], eng, other) == [("where", f"RuntimeError: {other.resolve()}")]
    assert unresolvable(["where"], eng) == [("where", f"RuntimeError: {tmp_path.resolve()}")]


def test_options_default_to_the_paperkit_engine() -> None:
    """With nothing asked for, the engine is `paperkit`, nothing is skipped or verified."""
    assert Options() == Options(engine=Path("paperkit"), skip=(), pkg="", verify=False)


def test_parse_args_reads_every_option() -> None:
    """Each option takes the next word, and `--verify` is a flag."""
    argv = ["--skip", "tests,docs", "--pkg", "paperkit", "--engine", "e", "--verify"]
    assert parse_args(argv) == Options(
        engine=Path("e"), skip=("tests", "docs"), pkg="paperkit", verify=True
    )


def test_parse_args_stops_at_an_unknown_word() -> None:
    """The first unknown word ends the options, and a dangling option is ignored."""
    assert parse_args(["--bogus", "x", "--pkg", "p"]) == Options()
    assert parse_args(["--pkg"]) == Options()


def test_main_prints_the_names(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Without `--verify` the names are printed one per line and the exit code is 0."""
    eng = _engine(tmp_path)
    assert main(["--engine", str(eng), "--skip", "tests"]) == 0
    assert capsys.readouterr().out == "a\ntools.sub\n"


def test_main_verify_counts_what_imports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With `--verify` and every name importable, the count line is printed and the code is 0."""
    eng = _engine(tmp_path)
    argv = ["--engine", str(eng), "--skip", "tests", "--pkg", "eng", "--verify"]
    assert main(argv) == 0
    assert capsys.readouterr().out == "\n2 of 2 engine modules import by name\n"


def test_main_verify_fails_on_a_bad_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A name that does not import is listed, the warning is printed and the code is 1."""
    eng = _engine(tmp_path)
    (eng / "t.py").write_text("raise ImportError('boom')\n", encoding="utf-8")
    assert main(["--engine", str(eng), "--verify"]) == 1
    out = capsys.readouterr().out
    assert "  XX t " in out
    assert "ImportError: boom" in out
    assert "2 of 3 engine modules import by name" in out
    assert "a ModuleNotFoundError in every consumer" in out


def test_main_reads_sys_argv_when_not_given_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no argv, the process arguments after the program name are used."""
    eng = _engine(tmp_path)
    monkeypatch.setattr(sys, "argv", ["dagnames", "--engine", str(eng), "--skip", "tests"])
    assert main() == 0
    assert capsys.readouterr().out == "a\ntools.sub\n"


def test_module_path_import_from_a_fresh_interpreter(tmp_path: Path) -> None:
    """A fresh interpreter can import the name check by module path and run it.

    This is the property a held-out gate witness needs: nothing but the installed package.
    """
    eng = _engine(tmp_path)
    code = (
        "from pathlib import Path\n"
        "from mikemol.importdag.dagnames import module_names, unresolvable\n"
        f"eng = Path({str(eng)!r})\n"
        "print(unresolvable(module_names(eng, ('tests',), 'eng'), eng))\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert (r.returncode, r.stdout.strip()) == (0, "[]")


def test_runs_as_a_module(tmp_path: Path) -> None:
    """`python -m mikemol.importdag.dagnames` exits with `main`'s code."""
    eng = _engine(tmp_path)
    r = subprocess.run(
        [sys.executable, "-m", "mikemol.importdag.dagnames", "--engine", str(eng)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (r.returncode, r.stdout) == (0, "a\nt\ntools.sub\n")

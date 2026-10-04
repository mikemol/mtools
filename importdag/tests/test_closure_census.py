# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `closure_census`: a witness's subprocess script is checked against its cone."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.importdag.closure_census import (
    Gap,
    Tree,
    audit,
    audit_witness,
    cone,
    declared,
    default_tree,
    dispatch_table,
    engine_modules,
    main,
    parse_args,
    projects_of,
    script_imports,
    scripts_named,
    witness_modules,
)

if TYPE_CHECKING:
    import pytest

COMPONENTS = """\
COMPONENTS = {
    "core": ["bib.py", "bibparse.py"],
    "more": ["gate.py"],
}
"""

FAKE_CLOSURE = """\
import os
import sys

kind = "abs" if os.path.isabs(sys.argv[2]) else "rel"
rows = [
    "k1\\tpaperkit/bib.py",
    "k1\\tread:something",
    "junk",
    "kind\\t" + kind + ".py",
    "pp\\t" + os.environ["PYTHONPATH"],
]
sys.stdout.write("\\n".join(rows) + "\\n")
"""

WITNESS = """\
CLAIMS = {"k1": check_one, "k3": ghost}


def check_one():
    return run("python3", "checks/gen_x.py", "other.txt")
"""


def _tree(tmp_path: Path) -> Tree:
    """Build a repository with an engine, a fake closure tool and one project.

    Returns:
        The tree describing it.

    """
    root = tmp_path / "repo"
    eng = root / "paperkit"
    eng.mkdir(parents=True)
    (eng / "components.bzl").write_text(COMPONENTS, encoding="utf-8")
    (eng / "bib.py").write_text("import bibparse\n", encoding="utf-8")
    (eng / "bibparse.py").write_text("VALUE = 1\n", encoding="utf-8")
    (eng / "gate.py").write_text("VALUE = 2\n", encoding="utf-8")
    closure = root / "cl" / "closure.py"
    closure.parent.mkdir()
    closure.write_text(FAKE_CLOSURE, encoding="utf-8")
    checks = root / "proj" / "checks"
    checks.mkdir(parents=True)
    (checks / "witness.py").write_text(WITNESS, encoding="utf-8")
    (checks / "gen_x.py").write_text("import bib\n", encoding="utf-8")
    (root / "proj" / "paper.toml").write_text(
        '[checks.claim]\ncmd = "python3 checks/witness.py {target}"\n', encoding="utf-8"
    )
    return Tree(root=root, engine=eng, closure=closure)


def test_default_tree_follows_the_paperkit_layout() -> None:
    """The engine is `paperkit` and the closure script is `tools/closure.py`, under the root."""
    root = Path("r")
    assert default_tree(root) == Tree(
        root=root, engine=Path("r/paperkit"), closure=Path("r/tools/closure.py")
    )


def test_engine_modules_are_prefixed_and_sorted(tmp_path: Path) -> None:
    """Every component's paths, sorted, prefixed with the engine directory's name."""
    tree = _tree(tmp_path)
    assert engine_modules(tree) == ["paperkit/bib.py", "paperkit/bibparse.py", "paperkit/gate.py"]


def test_declared_asks_the_closure_tool(tmp_path: Path) -> None:
    """Import rows become stems by claim; non-import rows and short rows are skipped."""
    tree = _tree(tmp_path)
    got = declared("proj/checks/witness.py", engine_modules(tree), tree)
    assert got == {"k1": {"bib"}, "kind": {"rel"}, "pp": {"cl"}}


def test_dispatch_table_reads_the_registry() -> None:
    """Only a registry dict with string keys and plain-name values is read."""
    src = (
        "CLAIMS = {'a': fa, 'b': 'text', 3: fc}\n"
        "WITNESSES = {'w': fw}\n"
        "OTHER = {'x': fx}\n"
        "CLAIMS2 = 5\n"
    )
    assert dispatch_table(ast.parse(src)) == {"a": "fa", "3": "fc", "w": "fw"}


def test_scripts_named_finds_sibling_basenames() -> None:
    """A string constant naming a sibling by its last segment counts; others do not."""
    fn = ast.parse("f('checks/gen.py', 'plain.py', 7, 'other/gen2.py')")
    assert scripts_named(fn, {"gen.py", "gen2.py"}) == {"gen.py", "gen2.py"}
    assert scripts_named(fn, {"absent.py"}) == set()


def test_script_imports_reads_both_forms(tmp_path: Path) -> None:
    """A flat import and a flat from-import of an engine stem are the seed."""
    path = tmp_path / "s.py"
    path.write_text("import bib, os\nfrom gate import x\nfrom os import path\n", encoding="utf-8")
    assert script_imports(path, {"bib", "gate"}) == {"bib", "gate"}


def test_script_imports_survive_an_unreadable_script(tmp_path: Path) -> None:
    """A missing file and a syntax error each yield the empty set."""
    assert script_imports(tmp_path / "missing.py", {"bib"}) == set()
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n", encoding="utf-8")
    assert script_imports(bad, {"bib"}) == set()


def test_cone_expands_through_engine_edges(tmp_path: Path) -> None:
    """A seed brings in what it imports, transitively, and an unknown seed adds nothing."""
    tree = _tree(tmp_path)
    mods = engine_modules(tree)
    assert cone({"bib"}, mods, tree) == {"bib", "bibparse"}
    assert cone({"gate", "nowhere"}, mods, tree) == {"gate"}


def test_witness_modules_come_from_a_bib_and_the_toml(tmp_path: Path) -> None:
    """A script is a witness when a `.bib` or `paper.toml` names it and it exists."""
    tree = _tree(tmp_path)
    assert witness_modules(tree.root / "proj") == [tree.root / "proj" / "checks" / "witness.py"]
    other = tree.root / "p2"
    (other / "checks").mkdir(parents=True)
    (other / "checks" / "named.py").write_text("", encoding="utf-8")
    (other / "checks" / "unnamed.py").write_text("", encoding="utf-8")
    (other / "w.bib").write_text(
        "@x{k, cmd = {python3 checks/named.py}, c = {ghost.py}}\n", "utf-8"
    )
    assert witness_modules(other) == [other / "checks" / "named.py"]


def test_witness_modules_of_a_project_without_checks(tmp_path: Path) -> None:
    """No `checks` directory means no witnesses."""
    assert witness_modules(tmp_path) == []


def test_audit_witness_flags_the_unstaged_cone(tmp_path: Path) -> None:
    """The script's cone minus the claim's declared roots is the gap."""
    tree = _tree(tmp_path)
    proj = tree.root / "proj"
    got = audit_witness(proj / "checks" / "witness.py", proj, engine_modules(tree), tree)
    assert got == [Gap(claim="k1", script="proj/checks/gen_x.py", missing=["bibparse"])]


def test_audit_witness_passes_a_covered_cone(tmp_path: Path) -> None:
    """When the declared roots already hold the whole cone there is no gap."""
    tree = _tree(tmp_path)
    proj = tree.root / "proj"
    (proj / "checks" / "gen_x.py").write_text("import gate\n", encoding="utf-8")
    (tree.engine / "gate.py").write_text("VALUE = 2\n", encoding="utf-8")
    closure = "print('k1\\tpaperkit/gate.py')\n"
    tree.closure.write_text(closure, encoding="utf-8")
    assert audit_witness(proj / "checks" / "witness.py", proj, engine_modules(tree), tree) == []


def test_audit_witness_without_siblings_has_no_gaps(tmp_path: Path) -> None:
    """A witness alone in its checks directory names no sibling script."""
    tree = _tree(tmp_path)
    (tree.root / "proj" / "checks" / "gen_x.py").unlink()
    proj = tree.root / "proj"
    assert audit_witness(proj / "checks" / "witness.py", proj, engine_modules(tree), tree) == []


def test_audit_witness_outside_the_root_is_passed_absolute(tmp_path: Path) -> None:
    """A witness out of tree reaches the closure tool as an absolute path."""
    tree = _tree(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "checks").mkdir()
    (outside / "checks" / "witness.py").write_text(WITNESS, encoding="utf-8")
    (outside / "checks" / "gen_x.py").write_text("import bib\n", encoding="utf-8")
    kind = tmp_path / "kind.txt"
    closure = (
        "import os, sys\n"
        f"open({str(kind)!r}, 'w').write('abs' if os.path.isabs(sys.argv[2]) else 'rel')\n"
    )
    tree.closure.write_text(closure, encoding="utf-8")
    got = audit_witness(outside / "checks" / "witness.py", outside, engine_modules(tree), tree)
    assert got == [Gap(claim="k1", script="elsewhere/checks/gen_x.py", missing=["bib", "bibparse"])]
    assert kind.read_text(encoding="utf-8") == "abs"


def test_audit_collects_every_witness(tmp_path: Path) -> None:
    """The gaps of every witness module of the project are returned."""
    tree = _tree(tmp_path)
    got = audit(tree.root / "proj", engine_modules(tree), tree)
    assert got == [Gap(claim="k1", script="proj/checks/gen_x.py", missing=["bibparse"])]


def test_projects_of_includes_the_root_project(tmp_path: Path) -> None:
    """A subdirectory with checks is a project, and so is the root when it has its own."""
    tree = _tree(tmp_path)
    assert projects_of(tree.root) == [tree.root / "proj"]
    (tree.root / "checks").mkdir()
    assert projects_of(tree.root) == [tree.root, tree.root / "proj"]


def test_parse_args_defaults_to_the_current_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no options the tree is the paperkit layout under the working directory."""
    monkeypatch.chdir(tmp_path)
    tree, wanted = parse_args(["paper", "report"])
    assert tree == default_tree(Path.cwd())
    assert wanted == {"paper", "report"}


def test_parse_args_reads_root_and_closure(tmp_path: Path) -> None:
    """`--root` and `--closure` take the next word, resolved; the rest are project labels."""
    tree, wanted = parse_args(["--root", str(tmp_path), "p", "--closure", "c/x.py"])
    assert tree == Tree(
        root=tmp_path.resolve(),
        engine=tmp_path.resolve() / "paperkit",
        closure=Path("c/x.py").resolve(),
    )
    assert wanted == {"p"}


def test_parse_args_treats_a_dangling_option_as_a_label() -> None:
    """An option with no value after it is a project label, not an option."""
    _, wanted = parse_args(["--root"])
    assert wanted == {"--root"}


def test_main_reports_the_gap(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A gap is printed with what was examined, and the exit code is 1."""
    tree = _tree(tmp_path)
    argv = ["--root", str(tree.root), "--closure", str(tree.closure)]
    assert main(argv) == 1
    out = capsys.readouterr().out
    assert out.startswith("  GAP k1\n      shells out to : proj/checks/gen_x.py\n")
    assert "      NOT staged    : bibparse\n" in out
    assert "\nexamined 1 witness module(s):\n    proj/checks/witness.py\n" in out
    assert "\n1 under-declared witness(es)\n" in out
    assert "ModuleNotFoundError waiting for a module to gain a dependency" in out


def test_main_clean_and_filtered(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A project filtered out is not examined: the count is 0 and the exit code is 0."""
    tree = _tree(tmp_path)
    argv = ["--root", str(tree.root), "--closure", str(tree.closure), "other"]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert out == "\nexamined 0 witness module(s):\n\n0 under-declared witness(es)\n"


def test_main_names_a_project_without_a_witness(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A project with a checks directory but no named witness is listed as skipped."""
    tree = _tree(tmp_path)
    (tree.root / "checks").mkdir()
    argv = ["--root", str(tree.root), "--closure", str(tree.closure), "(root)"]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert "  NO bib-named witness found in: (root)\n" in out
    assert "examined 0 witness module(s)" in out


def test_main_reads_sys_argv_when_not_given_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no argv, the process arguments after the program name are used."""
    tree = _tree(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["census", "--root", str(tree.root), "--closure", str(tree.closure)]
    )
    assert main() == 1
    assert "1 under-declared witness(es)" in capsys.readouterr().out


def test_runs_as_a_module(tmp_path: Path) -> None:
    """`python -m mikemol.importdag.closure_census` exits with `main`'s code."""
    tree = _tree(tmp_path)
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "mikemol.importdag.closure_census",
            "--root",
            str(tree.root),
            "--closure",
            str(tree.closure),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
    assert "1 under-declared witness(es)" in r.stdout

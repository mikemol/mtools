# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.ambient`: the union census of ambient-cwd dependence.

⚑⚑ THE FIXTURE TREE HAS `scratch/` AND `docs/` AND NOTHING ELSE: `agda/y` must read UNKNOWN, which
is the witness that no frozen roster of another repository's directories leaks in.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from mikemol.pycodemod import ambient as amb

if TYPE_CHECKING:
    from pathlib import Path

_MOD = """import os
import subprocess
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))


def reader(where, *rest, **opts):
    os.path.exists("scratch/x.py")
    open(where)
    open(os.path.join(ROOT, "a"))
    open("agda/y")
    open(name)
    os.getcwd()
    subprocess.run(["python3", "scratch/x.py"])
    subprocess.run(["scratch/tool.py"])
    listdir("scratch/**", head)
    Path(f"{ROOT}/x")
    Path(f"docs/{name}")
    glob("/abs/*")
    os.chdir("/tmp")
    open("docs" + "/z")
    open(rest)
    open(opts)
    f()
    open(os.path.join("scratch", n))
    open(os.path.join(os.getcwd(), n))
    open(file=x)
    def inner():
        open(where)

class K:
    async def m(self):
        open(fn())
"""


def _tree(tmp_path: Path) -> Path:
    for name in ("scratch", "docs", ".git"):
        (tmp_path / name).mkdir()
    (tmp_path / "README").write_text("", encoding="utf-8")
    return tmp_path


def _expr(src: str) -> ast.expr:
    node = ast.parse(src, mode="eval")
    return node.body


def test_subtrees_are_discovered_from_the_tree_alone(tmp_path: Path) -> None:
    """⚑⚑ Visible directories only; no frozen fallback; an unlistable tree is empty."""
    assert amb.repo_subtrees(_tree(tmp_path)) == {"scratch", "docs"}
    assert amb.repo_subtrees(tmp_path / "absent") == frozenset()


def test_the_census_classifies_every_unanchored_call(tmp_path: Path) -> None:
    """⚑⚑⚑ SCOPED, REPO, UNKNOWN and MUTATES, with `getcwd` a row of its own."""
    root = _tree(tmp_path)
    mod = root / "mod.py"
    mod.write_text(_MOD, encoding="utf-8")
    got = amb.ambient([str(mod)], root)
    assert [(r.line, r.kind, r.verdict, r.shown, r.context) for r in got.rows] == [
        (9, "os.path:exists", "REPO", "scratch/x.py", "reader"),
        (10, "builtin:open", "SCOPED", "where", "reader"),
        (12, "builtin:open", "UNKNOWN", "agda/y", "reader"),
        (13, "builtin:open", "UNKNOWN", "name", "reader"),
        (14, "getcwd", "SCOPED", "os.getcwd()", "reader"),
        (16, "proc:run", "REPO", "scratch/tool.py", "reader"),
        (17, "os:listdir", "SCOPED", "head", "reader"),
        (19, "pathlib:Path", "REPO", "docs/", "reader"),
        (21, "chdir", "MUTATES", "os.chdir('/tmp')", "reader"),
        (22, "builtin:open", "REPO", "docs", "reader"),
        (23, "builtin:open", "SCOPED", "rest", "reader"),
        (24, "builtin:open", "SCOPED", "opts", "reader"),
        (26, "builtin:open", "REPO", "scratch", "reader"),
        (27, "builtin:open", "SCOPED", "os.getcwd()", "reader"),
        (27, "getcwd", "SCOPED", "os.getcwd()", "reader"),
        (28, "builtin:open", "UNKNOWN", "x", "reader"),
        (30, "builtin:open", "SCOPED", "where", "reader.inner"),
        (34, "builtin:open", "UNKNOWN", "<computed>", "K.m"),
    ]
    assert got.population == 1
    assert got.skipped == []


def test_the_census_reports_what_it_could_not_read(tmp_path: Path) -> None:
    """⚑⚑ Undecodable, unreadable and unparseable are skips; the population counts them all."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n", encoding="utf-8")
    good = tmp_path / "good.py"
    good.write_text("open('x')\n", encoding="utf-8")
    missing = str(tmp_path / "absent.py")
    paths = [str(latin), str(bad), str(good), missing]
    got = amb.ambient(paths, tmp_path)
    assert got.skipped == [
        amb.Skip(str(latin), "undecodable", "UnicodeDecodeError"),
        amb.Skip(str(bad), "unparseable", "SyntaxError"),
        amb.Skip(missing, "unreadable", "FileNotFoundError"),
    ]
    assert got.population == len(paths)
    assert [(r.verdict, r.shown, r.context) for r in got.rows] == [("UNKNOWN", "x", "<module>")]


def test_anchoring_follows_the_head_of_the_expression() -> None:
    """⚑ A join, a sum and an f-string are anchored by their HEAD; `__file__` anchors anywhere."""
    anchored = [
        "ROOT",
        "self.root",
        "'/abs'",
        "f'/abs{x}'",
        "f'{ROOT}/x'",
        "ROOT + 'x'",
        "'x' + __file__",
        "join(ROOT, 'x')",
        "dirname(abspath(__file__))",
    ]
    loose = [
        "x",
        "'rel'",
        "f'{x}/y'",
        "f''",
        "'x' + ROOT",
        "join('x', ROOT)",
        "join()",
        "abspath()",
        "dirname(x)",
        "3",
        "fns[0]",
    ]
    assert [src for src in anchored if not amb.anchored(_expr(src))] == []
    assert [src for src in loose if amb.anchored(_expr(src))] == []


def test_path_arg_reads_the_argv_head_and_the_path_keywords() -> None:
    """⚑⚑ A subprocess argv's head is the path; an empty argv and no path argument give None."""

    def head(src: str) -> str | None:
        call = _expr(src)
        assert isinstance(call, ast.Call)
        got = amb.path_arg(call)
        return None if got is None else ast.unparse(got)

    assert head("run(['a/b', 'c'])") == "'a/b'"
    assert head("run(('a/b',))") == "'a/b'"
    assert head("run([])") is None
    assert head("open(p, 'r')") == "p"
    assert head("walk(top=t)") == "t"
    assert head("open(mode='r')") is None


def test_callee_name_is_unqualified() -> None:
    """`os.path.exists` and `exists` both name `exists`; a call through an expression names none."""
    names = []
    for src in ("os.path.exists(p)", "exists(p)", "fns[0](p)"):
        call = _expr(src)
        assert isinstance(call, ast.Call)
        names.append(amb.callee_name(call))
    assert names == ["exists", "exists", None]


def test_known_misses_are_declared() -> None:
    """The census states its blind spots, keyed, rather than reading a zero as a fact."""
    assert {key for key, _ in amb.KNOWN_MISSES} >= {"alias", "argv", "subprocess-argv"}

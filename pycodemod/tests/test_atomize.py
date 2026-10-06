# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `atomize-imports`: a flat sibling import becomes a package import, provably.

⚑⚑ EACH REWRITE IS READ BACK AS TEXT, and each refusal is asserted to leave the file unwritten: a
rewriter whose refusals still change the file is the failure these tests exist to catch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import atomize, cli_atomize
from mikemol.pycodemod.imports import importers

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _package(tmp_path: Path) -> str:
    pkg = tmp_path / "pk"
    pkg.mkdir()
    for stem in ("bib", "other", "random"):
        (pkg / f"{stem}.py").write_text("X = 1\n", encoding="utf-8")
    return str(pkg)


def _consumer(tmp_path: Path, text: str) -> str:
    path = tmp_path / "pk" / "consumer.py"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _plan(tmp_path: Path, text: str) -> tuple[atomize.Atomized, str]:
    pkg = _package(tmp_path)
    path = _consumer(tmp_path, text)
    return atomize.atomize([path], atomize.siblings_of(pkg), "pk"), path


def _nothing(*_args: object) -> atomize.Atomized:
    return atomize.Atomized()


def test_from_import_becomes_package_import_and_uses_are_qualified(tmp_path: Path) -> None:
    """⚑ `from bib import a, b` is one `import pk.bib`, and `a`, `b` read `pk.bib.a`, `pk.bib.b`."""
    result, path = _plan(tmp_path, "from bib import a, b\n\nprint(a, b(1))\n")
    assert result.texts[path] == "import pk.bib\n\nprint(pk.bib.a, pk.bib.b(1))\n"
    assert [s.verdict for s in result.sites] == [atomize.REWRITE]


def test_bare_import_use_is_qualified(tmp_path: Path) -> None:
    """⚑ `import bib` keeps its neighbours and its uses gain the package."""
    result, path = _plan(tmp_path, "import os, bib\n\nbib.f(os.sep)\n")
    assert result.texts[path] == "import os, pk.bib\n\npk.bib.f(os.sep)\n"


def test_aliases_are_followed_to_their_definition(tmp_path: Path) -> None:
    """⚑ `import bib as b` and `from other import a as z` name their definition sites after."""
    result, path = _plan(tmp_path, "import bib as b\nfrom other import a as z\n\nb.f(z)\n")
    assert result.texts[path] == "import pk.bib\nimport pk.other\n\npk.bib.f(pk.other.a)\n"


def test_repeated_imports_of_one_module_collapse_to_one(tmp_path: Path) -> None:
    """⚑ Two `from bib import` lines in one body leave one `import pk.bib`."""
    result, path = _plan(tmp_path, "from bib import a\nfrom bib import b\n\na(b)\n")
    assert result.texts[path] == "import pk.bib\n\npk.bib.a(pk.bib.b)\n"


def test_a_repeat_with_a_comment_is_kept(tmp_path: Path) -> None:
    """⚑ A repeat that carries a comment line is never dropped: commentary is not tidied away."""
    result, path = _plan(tmp_path, "from bib import a\n# why\nfrom bib import b\n\na(b)\n")
    assert result.texts[path] == "import pk.bib\n# why\nimport pk.bib\n\npk.bib.a(pk.bib.b)\n"


def test_a_rebound_name_refuses_the_statement_and_changes_nothing(tmp_path: Path) -> None:
    """⚑⚑ A name assigned elsewhere is not provably the import, so the statement is refused."""
    result, _ = _plan(tmp_path, "from bib import a\n\na = 2\n")
    assert [s.verdict for s in result.sites] == [atomize.REFUSED]
    assert result.texts == {}


def test_a_star_import_is_refused(tmp_path: Path) -> None:
    """⚑ A star import binds names no scope can resolve, so it is refused."""
    result, _ = _plan(tmp_path, "from bib import *\n")
    assert [s.verdict for s in result.sites] == [atomize.REFUSED]
    assert result.texts == {}


def test_a_local_that_shadows_the_name_is_left_alone(tmp_path: Path) -> None:
    """⚑⚑ A parameter named like the import keeps its name; only the true reference moves."""
    result, path = _plan(tmp_path, "from bib import a\n\n\ndef f(a):\n    return a\n\n\nf(a)\n")
    assert result.texts[path] == "import pk.bib\n\n\ndef f(a):\n    return a\n\n\nf(pk.bib.a)\n"


def test_a_string_reference_refuses_the_statement(tmp_path: Path) -> None:
    """⚑ An `__all__` entry names the import by string, which no rewrite can follow."""
    result, _ = _plan(tmp_path, 'from bib import a\n\n__all__ = ["a"]\n')
    assert [s.verdict for s in result.sites] == [atomize.REFUSED]
    assert result.texts == {}


def test_a_sibling_that_shadows_the_stdlib_is_not_rewritten(tmp_path: Path) -> None:
    """⚑ A sibling called `random` is reported as shadowing, and `import random` is untouched."""
    pkg = _package(tmp_path)
    siblings = atomize.siblings_of(pkg)
    assert siblings.shadowing == {"random"}
    path = _consumer(tmp_path, "import random\n")
    assert atomize.atomize([path], siblings, "pk").sites == []


def test_a_write_leaves_only_what_was_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """⚑⚑ After a write the census finds exactly the refused sites, and the exit says unfinished."""
    pkg = _package(tmp_path)
    path = _consumer(tmp_path, "from bib import a\nfrom other import *\n\nprint(a)\n")
    flags = cli_atomize.AtomizeFlags(package="pk", package_dir=pkg, write=True)
    assert cli_atomize.print_atomize([path], flags) == 1
    out = capsys.readouterr().out
    assert "delta" not in out
    assert "atomize wrote 1 files" in out
    assert [r.line for r in importers([path], "other").rows] == [2]
    assert importers([path], "bib").rows == []


def test_a_write_is_refused_when_the_sets_disagree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """⚑⚑⚑ A planner that misses a site the census finds writes nothing: A Δ B must be empty."""
    pkg = _package(tmp_path)
    path = _consumer(tmp_path, "from bib import a\n")
    flags = cli_atomize.AtomizeFlags(package="pk", package_dir=pkg, write=True)
    monkeypatch.setattr(atomize, "atomize", _nothing)
    assert cli_atomize.print_atomize([path], flags) == 1
    assert "census-only bib" in capsys.readouterr().out
    assert (tmp_path / "pk" / "consumer.py").read_text(encoding="utf-8") == "from bib import a\n"

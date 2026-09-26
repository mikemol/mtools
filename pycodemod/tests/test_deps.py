# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the import census: every top-level import graded against a declared manifest."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import deps

if TYPE_CHECKING:
    from pathlib import Path

_MANIFEST = """\
[project]
name = "x"
dependencies = ["libcst>=1.0", "SQLAlchemy ; python_version >= '3.13'"]

[project.optional-dependencies]
extra = ["pytest"]
"""

_TOOL = """\
import os
import libcst
from sqlalchemy import func
import undeclared_pkg
import pytest
import no_such_module_anywhere
import helper
from . import sibling
"""


def _tree(tmp_path: Path) -> tuple[list[str], Path]:
    (tmp_path / "pyproject.toml").write_text(_MANIFEST, encoding="utf-8")
    (tmp_path / "tool.py").write_text(_TOOL, encoding="utf-8")
    (tmp_path / "helper.py").write_text("x = 1\n", encoding="utf-8")
    vend = tmp_path / "vendor"
    vend.mkdir()
    (vend / "bundled.py").write_text("import helper\n", encoding="utf-8")
    paths = [str(tmp_path / "tool.py"), str(tmp_path / "helper.py"), str(vend / "bundled.py")]
    return paths, tmp_path / "pyproject.toml"


def _verdicts(tmp_path: Path, vendored: tuple[str, ...] = ()) -> dict[str, str]:
    paths, manifest = _tree(tmp_path)
    return {r.module: r.verdict for r in deps.import_census(paths, manifest, vendored).rows}


def test_each_import_gets_one_verdict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑⚑ Stdlib, declared (base and extras), undeclared, missing and first-party, each named.

    undeclared_pkg is importable (put on the path here) and in no manifest: UNDECLARED. A relative
    import names no package and is not counted.
    """
    site = tmp_path / "site"
    (site / "undeclared_pkg").mkdir(parents=True)
    (site / "undeclared_pkg" / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(site))
    assert _verdicts(tmp_path) == {
        "os": "STDLIB",
        "libcst": "DECLARED",
        "sqlalchemy": "DECLARED",
        "pytest": "DECLARED",
        "undeclared_pkg": "UNDECLARED",
        "no_such_module_anywhere": "MISSING",
        "helper": "FIRST-PARTY",
    }


def test_vendored_is_the_callers_path_fragment(tmp_path: Path) -> None:
    """⚑ A first-party module used under a caller-named vendored path is VENDORED."""
    assert _verdicts(tmp_path, ("/vendor/",))["helper"] == "VENDORED"


def test_a_row_counts_files_and_names_one(tmp_path: Path) -> None:
    """Each row carries how many files import the module and the first of them."""
    paths, manifest = _tree(tmp_path)
    rows = {r.module: r for r in deps.import_census(paths, manifest).rows}
    assert (rows["helper"].files, rows["helper"].example) == (2, min(paths[0], paths[2]))


def test_the_declared_match_ignores_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑⚑ A capitalised import matches its lowercase declaration; the origin compared as written."""
    pkg = tmp_path / "site" / "CapMod"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path / "site"))
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text('[project]\nname = "x"\ndependencies = ["capmod"]\n', encoding="utf-8")
    tool = tmp_path / "t.py"
    tool.write_text("import CapMod\n", encoding="utf-8")
    rows = deps.import_census([str(tool)], manifest).rows
    assert [(r.module, r.verdict) for r in rows] == [("CapMod", "DECLARED")]


@pytest.mark.parametrize("content", [None, "not = [valid toml", "\xff"])
def test_an_unreadable_manifest_refuses(tmp_path: Path, content: str | None) -> None:
    """⚑⚑⚑ A missing, invalid or undecodable manifest raises; it never reads as no declarations."""
    manifest = tmp_path / "pyproject.toml"
    if content == "\xff":
        manifest.write_bytes(b"\xff\xfe")
    elif content is not None:
        manifest.write_text(content, encoding="utf-8")
    with pytest.raises(deps.ManifestError, match="cannot read"):
        deps.import_census([], manifest)


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe import os\n", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑ An unreadable, undecodable or unparseable file is skipped with its reason."""
    _, manifest = _tree(tmp_path)
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = deps.import_census([str(path)], manifest)
    whys: list[str] = [s.why for s in got.skipped]
    assert (got.rows, whys) == ([], [why])

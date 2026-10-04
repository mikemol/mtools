# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `dagderive`: stem-resolved edges recorded as paths, and the closure walk."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.importdag.dagderive import cone, edges, imports, stem_index

if TYPE_CHECKING:
    from pathlib import Path

NAMES = {"bib", "bibparse", "vfs", "_fixture_model"}


def test_flat_import_is_an_edge() -> None:
    """`import bib` yields the stem."""
    assert imports("import bib\n", NAMES) == {"bib"}


def test_package_import_is_the_same_edge() -> None:
    """`from paperkit import bibparse` yields the stem, not the package."""
    assert imports("from paperkit import bibparse\n", NAMES) == {"bibparse"}


def test_subpackage_import_is_the_same_edge() -> None:
    """`from paperkit.tools import vfs` yields the stem."""
    assert imports("from paperkit.tools import vfs\n", NAMES) == {"vfs"}


def test_flat_from_import_is_an_edge() -> None:
    """`from _fixture_model import fx` yields the module, not the imported name."""
    assert imports("from _fixture_model import fx\n", NAMES) == {"_fixture_model"}


def test_names_restrict_the_result() -> None:
    """A name outside `names` is not an edge, in either spelling."""
    text = "import os\nfrom paperkit import other\nimport bib\n"
    assert imports(text, NAMES) == {"bib"}


def test_pkg_names_the_engine_package() -> None:
    """A from-import of a package other than `pkg` is read only when it is an engine stem."""
    assert imports("from elsewhere import bib\n", NAMES) == set()
    assert imports("from elsewhere import bib\n", NAMES, pkg="elsewhere") == {"bib"}


def test_a_name_in_a_comment_or_string_is_not_an_edge() -> None:
    """The syntax tree is read, not the text."""
    assert imports('# import bib\nx = "import vfs"\n', NAMES) == set()


def test_unparseable_text_has_no_edges() -> None:
    """A syntax error yields the empty set rather than raising."""
    assert imports("def (:\n", NAMES) == set()


def test_stem_index_maps_stem_to_path() -> None:
    """Each stem names its one path."""
    got = stem_index(["a.py", "tests/b.py"])
    assert got == {"a": "a.py", "b": "tests/b.py"}


def test_stem_index_exempts_package_markers() -> None:
    """Two `__init__.py` do not collide and are not indexed."""
    assert stem_index(["__init__.py", "tests/__init__.py", "a.py"]) == {"a": "a.py"}


def test_stem_index_refuses_an_ambiguous_stem() -> None:
    """A repeated stem raises, and the message names the paths."""
    with pytest.raises(ValueError, match=r"ambiguous.*bib\.py.*tests/bib\.py"):
        stem_index(["bib.py", "tests/bib.py"])


def _write(root: Path, rel: str, text: str) -> None:
    """Write `text` at `root/rel`, creating directories."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_edges_record_paths_on_both_sides(tmp_path: Path) -> None:
    """An edge is the importer's path and the imported module's path."""
    _write(tmp_path, "a.py", "import b\nfrom paperkit import c\nimport a\n")
    _write(tmp_path, "b.py", "x = 1\n")
    _write(tmp_path, "tests/c.py", "import b\n")
    got = edges(tmp_path, ["a.py", "b.py", "tests/c.py"])
    assert got == [("a.py", "b.py"), ("a.py", "tests/c.py"), ("tests/c.py", "b.py")]


def test_edges_refuse_an_ambiguous_stem(tmp_path: Path) -> None:
    """The ambiguity refusal reaches the caller of `edges`."""
    _write(tmp_path, "a.py", "")
    _write(tmp_path, "t/a.py", "")
    with pytest.raises(ValueError, match="ambiguous"):
        edges(tmp_path, ["a.py", "t/a.py"])


def test_cone_is_transitive_and_includes_start() -> None:
    """The walk follows every hop, handles a cycle, and returns the start."""
    graph = {"a.py": ["b.py"], "b.py": ["c.py", "a.py"], "c.py": [], "d.py": ["a.py"]}
    assert cone("a.py", graph) == {"a.py", "b.py", "c.py"}


def test_cone_of_an_unknown_module_is_itself() -> None:
    """A module with no recorded edges has the cone of just itself."""
    assert cone("z.py", {}) == {"z.py"}

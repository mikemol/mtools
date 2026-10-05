# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve a set of files' imports against each other: layout-free, ambiguity reported."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.importdag.resolve import (
    Resolution,
    derive,
    import_names,
    index,
    module_names,
    resolve,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_import_names_reads_plain_from_and_relative_forms() -> None:
    """`import a.b`, `from c import d` (c and c.d) and `from . import e` (bare e) name modules."""
    text = "import a.b\nfrom c import d\nfrom . import e\nfrom .f import g\n"
    assert import_names(text) == {"a.b", "c", "c.d", "e", "f", "f.g"}


def test_import_names_of_text_that_does_not_parse_is_empty() -> None:
    """A syntax error names nothing, as `dagderive.imports` reads it."""
    assert import_names("def broken(:\n") == frozenset()


def test_module_names_lists_every_dotted_suffix_longest_first() -> None:
    """A path under src roots is named by each suffix, so a short import still finds it."""
    assert module_names("pkg/src/m/x.py") == ("pkg.src.m.x", "src.m.x", "m.x", "x")


def test_a_package_marker_is_named_by_its_package() -> None:
    """`__init__` is dropped: it is reached as the package's own name."""
    assert module_names("pkg/sub/__init__.py") == ("pkg.sub", "sub")


def test_an_empty_path_has_no_names() -> None:
    """No path parts, no names, and no index error on the empty list."""
    assert module_names("") == ()


def test_index_collects_every_file_a_suffix_could_name() -> None:
    """Two files sharing a stem share its entry; a longer suffix keeps them apart."""
    table = index(["a/x.py", "b/x.py", "a/y.py"])
    assert table["x"] == {"a/x.py", "b/x.py"}
    assert table["a.x"] == {"a/x.py"}
    assert table["y"] == {"a/y.py"}


def test_a_unique_import_resolves_to_its_file() -> None:
    """The plain case: one file answers the name."""
    table = index(["a/x.py", "a/y.py"])
    assert resolve("a/y.py", ["x"], table) == Resolution(frozenset({"a/x.py"}), ())


def test_the_longest_dotted_prefix_wins() -> None:
    """`a.b.c` is a/b/c.py, not the shorter `a` (a.py), which a prefix scan from one would pick."""
    table = index(["a.py", "a/b/c.py"])
    assert resolve("main.py", ["a.b.c"], table).files == {"a/b/c.py"}


def test_an_attribute_falls_back_to_the_module_that_holds_it() -> None:
    """`a.b.thing` has no file `thing`, so the shorter prefix `a.b` is the module."""
    table = index(["a/b.py"])
    assert resolve("main.py", ["a.b.thing"], table).files == {"a/b.py"}


def test_a_file_does_not_import_itself() -> None:
    """The only file naming `x` is the importer: no edge, and nothing is ambiguous."""
    table = index(["a/x.py"])
    assert resolve("a/x.py", ["x"], table) == Resolution(frozenset(), ())


def test_a_name_with_no_file_resolves_to_nothing() -> None:
    """A third-party or stdlib name matches no indexed file."""
    table = index(["a/x.py"])
    assert resolve("a/y.py", ["os", "numpy.linalg"], table) == Resolution(frozenset(), ())


def test_an_ambiguous_name_prefers_the_sibling() -> None:
    """`import a` beside scripts/b.py is scripts/a.py, though tools/a.py has the same stem."""
    table = index(["scripts/a.py", "tools/a.py", "scripts/b.py"])
    assert resolve("scripts/b.py", ["a"], table) == Resolution(frozenset({"scripts/a.py"}), ())


def test_an_ambiguous_name_with_no_sibling_is_reported_and_gets_no_edge() -> None:
    """Two candidates, none beside the importer: no edge, and the name is returned."""
    table = index(["scripts/a.py", "tools/a.py", "other/c.py"])
    assert resolve("other/c.py", ["a"], table) == Resolution(frozenset(), ("a",))


def test_a_sibling_beats_a_deeper_file_of_the_same_stem() -> None:
    """Only `d/a.py` sits beside `d/c.py`; `d/x/a.py` is a different directory's `a`."""
    table = index(["d/a.py", "d/x/a.py", "d/c.py"])
    assert resolve("d/c.py", ["a"], table) == Resolution(frozenset({"d/a.py"}), ())


def test_the_ambiguous_names_are_sorted() -> None:
    """The report is deterministic: names sorted, each once."""
    table = index(["p/a.py", "q/a.py", "p/b.py", "q/b.py", "r/c.py"])
    got = resolve("r/c.py", ["b", "a", "b"], table)
    assert got.ambiguous == ("a", "b")


def test_every_name_contributes_its_file() -> None:
    """Files from several names are unioned."""
    table = index(["a/x.py", "a/y.py", "a/z.py"])
    assert resolve("a/z.py", ["x", "y"], table).files == {"a/x.py", "a/y.py"}


def test_derive_reads_each_file_and_resolves_it(tmp_path: Path) -> None:
    """The files are read from `root`, and the result is in `paths` order."""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "a" / "y.py").write_text("from a.x import VALUE\n", encoding="utf-8")
    got = derive(tmp_path, ["a/y.py", "a/x.py"])
    assert list(got) == ["a/y.py", "a/x.py"]
    assert got["a/y.py"] == Resolution(frozenset({"a/x.py"}), ())
    assert got["a/x.py"] == Resolution(frozenset(), ())

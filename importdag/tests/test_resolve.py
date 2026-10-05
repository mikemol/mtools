# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve a file set's imports against each other: layout-free, relative exact, never guessed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.importdag.resolve import (
    Reference,
    Resolution,
    Unsettled,
    derive,
    index,
    module_names,
    references,
    resolve,
)

if TYPE_CHECKING:
    from pathlib import Path


def _abs(*names: str) -> list[Reference]:
    """Build absolute references, level 0, for each dotted name.

    Returns:
        One reference per name.

    """
    return [Reference(0, name) for name in names]


def test_references_read_plain_from_and_relative_forms() -> None:
    """Each import keeps its level: absolute is 0, `from ..h import i` is level 2."""
    text = "import a.b\nfrom c import d\nfrom . import e\nfrom .f import g\nfrom ..h import i\n"
    assert references(text) == {
        Reference(0, "a.b"),
        Reference(0, "c"),
        Reference(0, "c.d"),
        Reference(1, ""),
        Reference(1, "e"),
        Reference(1, "f"),
        Reference(1, "f.g"),
        Reference(2, "h"),
        Reference(2, "h.i"),
    }


def test_references_of_text_that_does_not_parse_is_empty() -> None:
    """A syntax error names nothing, as `dagderive.imports` reads it."""
    assert references("def broken(:\n") == frozenset()


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
    table = index(["a/x.py", "b/x.py", "a/y.py"]).names
    assert table["x"] == {"a/x.py", "b/x.py"}
    assert table["a.x"] == {"a/x.py"}
    assert table["y"] == {"a/y.py"}


def test_index_keeps_the_set_of_paths_even_from_a_one_shot_iterable() -> None:
    """The paths are listed once, so a generator indexes the names and the file set alike."""
    got = index(path for path in ["a/x.py", "b/y.py"])
    assert got.files == {"a/x.py", "b/y.py"}
    assert got.names["x"] == {"a/x.py"}


def test_a_unique_import_resolves_to_its_file() -> None:
    """The plain case: one file answers the name."""
    got = resolve("a/y.py", _abs("x"), index(["a/x.py", "a/y.py"]))
    assert got == Resolution(frozenset({"a/x.py"}), ())


def test_the_longest_dotted_prefix_wins() -> None:
    """`a.b.c` is a/b/c.py, not the shorter `a` (a.py), which a prefix scan from one would pick."""
    got = resolve("main.py", _abs("a.b.c"), index(["a.py", "a/b/c.py"]))
    assert got.files == {"a/b/c.py"}


def test_an_attribute_falls_back_to_the_module_that_holds_it() -> None:
    """`a.b.thing` has no file `thing`, so the shorter prefix `a.b` is the module."""
    assert resolve("main.py", _abs("a.b.thing"), index(["a/b.py"])).files == {"a/b.py"}


def test_a_file_does_not_import_itself() -> None:
    """The only file naming `x` is the importer: no edge, and nothing is ambiguous."""
    assert resolve("a/x.py", _abs("x"), index(["a/x.py"])) == Resolution(frozenset(), ())


def test_a_name_with_no_file_resolves_to_nothing() -> None:
    """A third-party or stdlib name matches no indexed file."""
    got = resolve("a/y.py", _abs("os", "numpy.linalg"), index(["a/x.py"]))
    assert got == Resolution(frozenset(), ())


def test_an_ambiguous_name_prefers_the_sibling() -> None:
    """`import a` beside scripts/b.py is scripts/a.py, though tools/a.py has the same stem."""
    table = index(["scripts/a.py", "tools/a.py", "scripts/b.py"])
    got = resolve("scripts/b.py", _abs("a"), table)
    assert got == Resolution(frozenset({"scripts/a.py"}), ())


def test_an_ambiguous_name_with_no_sibling_is_reported_with_its_candidates() -> None:
    """Two candidates, none beside the importer: no edge, and the name returns with both."""
    table = index(["scripts/a.py", "tools/a.py", "other/c.py"])
    got = resolve("other/c.py", _abs("a"), table)
    assert got == Resolution(frozenset(), (Unsettled("a", ("scripts/a.py", "tools/a.py")),))


def test_the_candidates_are_every_file_that_answers_and_are_sorted() -> None:
    """Three files answer `a`; they are listed in sorted order whatever the index order."""
    table = index(["r/a.py", "p/a.py", "q/a.py", "z/c.py"])
    got = resolve("z/c.py", _abs("a"), table)
    assert got.ambiguous == (Unsettled("a", ("p/a.py", "q/a.py", "r/a.py")),)


def test_a_sibling_beats_a_deeper_file_of_the_same_stem() -> None:
    """Only `d/a.py` sits beside `d/c.py`; `d/x/a.py` is a different directory's `a`."""
    table = index(["d/a.py", "d/x/a.py", "d/c.py"])
    assert resolve("d/c.py", _abs("a"), table) == Resolution(frozenset({"d/a.py"}), ())


def test_the_unsettled_name_is_the_ambiguous_prefix_not_the_whole_import() -> None:
    """`import a.thing` with two files `a` reports `a`, the name a decision must settle."""
    table = index(["p/a.py", "q/a.py", "r/c.py"])
    got = resolve("r/c.py", _abs("a.thing"), table)
    assert got.ambiguous == (Unsettled("a", ("p/a.py", "q/a.py")),)


def test_a_name_imported_in_several_forms_is_reported_once() -> None:
    """`import a` and `from a import x` name `a` twice; the report holds it once."""
    table = index(["p/a.py", "q/a.py", "r/c.py"])
    got = resolve("r/c.py", references("import a\nfrom a import x\n"), table)
    assert got.ambiguous == (Unsettled("a", ("p/a.py", "q/a.py")),)


def test_the_unsettled_names_are_sorted() -> None:
    """The report is deterministic: names sorted, each once."""
    table = index(["p/a.py", "q/a.py", "p/b.py", "q/b.py", "r/c.py"])
    got = resolve("r/c.py", [*_abs("b", "a"), Reference(0, "b")], table)
    assert [item.name for item in got.ambiguous] == ["a", "b"]


def test_a_declared_resolution_settles_an_ambiguous_name() -> None:
    """Declaring `a` means tools/a.py gives that edge and clears the report."""
    table = index(["scripts/a.py", "tools/a.py", "other/c.py"])
    got = resolve("other/c.py", _abs("a"), table, {"a": "tools/a.py"})
    assert got == Resolution(frozenset({"tools/a.py"}), ())


def test_a_declared_resolution_applies_to_the_prefix_of_a_longer_name() -> None:
    """`import a.thing` with `a` declared resolves to the declared file."""
    table = index(["p/a.py", "q/a.py", "r/c.py"])
    got = resolve("r/c.py", _abs("a.thing"), table, {"a": "p/a.py"})
    assert got == Resolution(frozenset({"p/a.py"}), ())


def test_a_declaration_that_is_not_a_candidate_is_ignored() -> None:
    """A stale declaration cannot pin a name to a file that no longer answers it."""
    table = index(["scripts/a.py", "tools/a.py", "other/c.py"])
    got = resolve("other/c.py", _abs("a"), table, {"a": "gone/a.py"})
    assert got == Resolution(frozenset(), (Unsettled("a", ("scripts/a.py", "tools/a.py")),))


def test_a_declaration_never_overrides_a_name_that_settles_without_it() -> None:
    """The sibling still wins: a declaration settles ambiguity, it does not rewrite a name."""
    table = index(["scripts/a.py", "tools/a.py", "scripts/b.py"])
    got = resolve("scripts/b.py", _abs("a"), table, {"a": "tools/a.py"})
    assert got == Resolution(frozenset({"scripts/a.py"}), ())


def test_every_name_contributes_its_file() -> None:
    """Files from several names are unioned."""
    table = index(["a/x.py", "a/y.py", "a/z.py"])
    assert resolve("a/z.py", _abs("x", "y"), table).files == {"a/x.py", "a/y.py"}


def test_a_relative_import_names_the_file_beside_the_importer() -> None:
    """`from . import n` in pkg/m.py is pkg/n.py, not the other/n.py with the same name."""
    table = index(["pkg/m.py", "pkg/n.py", "other/n.py"])
    got = resolve("pkg/m.py", references("from . import n\n"), table)
    assert got == Resolution(frozenset({"pkg/n.py"}), ())


def test_two_dots_start_one_directory_up_and_are_never_ambiguous() -> None:
    """`from .. import streams` in pkg/sub/m.py is pkg/streams.py, and never ambiguous."""
    table = index(["pkg/streams.py", "pkg/sub/streams.py", "streams.py", "pkg/sub/m.py"])
    got = resolve("pkg/sub/m.py", references("from .. import streams\n"), table)
    assert got == Resolution(frozenset({"pkg/streams.py"}), ())


def test_a_package_is_preferred_to_a_module_of_the_same_name() -> None:
    """Python's own precedence: `x/__init__.py` over `x.py` for `from . import x`."""
    table = index(["pkg/m.py", "pkg/x/__init__.py", "pkg/x.py"])
    got = resolve("pkg/m.py", references("from . import x\n"), table)
    assert got.files == {"pkg/x/__init__.py"}


def test_a_relative_from_import_names_the_package_and_its_submodule() -> None:
    """`from .a import b` imports package a and submodule b, and the package shadows a.py."""
    table = index(["pkg/m.py", "pkg/a/b.py", "pkg/a/__init__.py", "pkg/a.py"])
    got = resolve("pkg/m.py", references("from .a import b\n"), table)
    assert got.files == {"pkg/a/__init__.py", "pkg/a/b.py"}


def test_a_relative_from_import_of_an_attribute_falls_back_to_the_module() -> None:
    """`from .a import thing` with no submodule `thing` is the module a.py."""
    table = index(["pkg/m.py", "pkg/a.py"])
    got = resolve("pkg/m.py", references("from .a import thing\n"), table)
    assert got.files == {"pkg/a.py"}


def test_a_dotted_relative_module_is_looked_up_by_its_path() -> None:
    """`from .a.b import c` is pkg/a/b.py."""
    table = index(["pkg/m.py", "pkg/a/b.py"])
    got = resolve("pkg/m.py", references("from .a.b import c\n"), table)
    assert got.files == {"pkg/a/b.py"}


def test_importing_a_non_module_from_the_package_names_the_package_itself() -> None:
    """`from . import CONSTANT` imports pkg/__init__.py, where the constant lives."""
    table = index(["pkg/m.py", "pkg/__init__.py"])
    got = resolve("pkg/m.py", references("from . import CONSTANT\n"), table)
    assert got.files == {"pkg/__init__.py"}


def test_a_relative_import_never_resolves_to_the_importer_itself() -> None:
    """`from . import m` inside m.py skips m.py and falls back to the package."""
    table = index(["pkg/m.py", "pkg/__init__.py"])
    got = resolve("pkg/m.py", references("from . import m\n"), table)
    assert got.files == {"pkg/__init__.py"}


def test_a_relative_import_in_a_package_marker_starts_in_its_own_directory() -> None:
    """`from . import m` in pkg/__init__.py is pkg/m.py."""
    table = index(["pkg/__init__.py", "pkg/m.py"])
    got = resolve("pkg/__init__.py", references("from . import m\n"), table)
    assert got.files == {"pkg/m.py"}


def test_a_relative_import_at_the_tree_root() -> None:
    """At the tree root there is no directory prefix: `from . import n` is n.py."""
    table = index(["m.py", "n.py"])
    assert resolve("m.py", references("from . import n\n"), table).files == {"n.py"}


def test_a_level_that_reaches_the_root_resolves_but_one_above_it_does_not() -> None:
    """In a/m.py, level 2 is the root (x.py is found) and level 3 is above it (nothing)."""
    table = index(["a/m.py", "x.py"])
    assert resolve("a/m.py", references("from .. import x\n"), table).files == {"x.py"}
    assert resolve("a/m.py", references("from ... import x\n"), table).files == frozenset()


def test_derive_reads_each_file_and_resolves_it(tmp_path: Path) -> None:
    """The files are read from `root`, relative and absolute imports both resolve."""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "a" / "y.py").write_text("from . import x\n", encoding="utf-8")
    (tmp_path / "a" / "z.py").write_text("from a.x import VALUE\n", encoding="utf-8")
    got = derive(tmp_path, ["a/z.py", "a/y.py", "a/x.py"])
    assert list(got) == ["a/z.py", "a/y.py", "a/x.py"]
    assert got["a/y.py"] == Resolution(frozenset({"a/x.py"}), ())
    assert got["a/z.py"] == Resolution(frozenset({"a/x.py"}), ())
    assert got["a/x.py"] == Resolution(frozenset(), ())


def test_derive_passes_the_declared_resolutions_through(tmp_path: Path) -> None:
    """A declaration given to derive settles an ambiguous name; without it the name returns."""
    for name in ("p/m.py", "q/m.py", "r/user.py"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("import m\n" if name == "r/user.py" else "x = 1\n", encoding="utf-8")
    paths = ["p/m.py", "q/m.py", "r/user.py"]
    assert derive(tmp_path, paths)["r/user.py"].ambiguous == (Unsettled("m", ("p/m.py", "q/m.py")),)
    pinned = derive(tmp_path, paths, {"m": "q/m.py"})["r/user.py"]
    assert pinned == Resolution(frozenset({"q/m.py"}), ())

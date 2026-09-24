# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.corpus.import_edges`: substrate's `import_edges_selftest` arms, ported.

The live-file positive control read substrate's own tree through `corpus.ROOT`; it becomes a
synthetic file with a known local import, since there is no root to read from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.corpus import import_edges

if TYPE_CHECKING:
    from pathlib import Path

# Every shape that DOES execute on import, and several that do not (substrate's fixture).
_SRC = """
import plain
from pkg.sub import thing
import dotted.name

if True:
    import in_if

try:
    import in_try
except ImportError:
    import in_handler
finally:
    import in_finally

for _x in ():
    import in_for

with open("/dev/null") as _fh:
    import in_with

def fn():
    import in_function
    from deferred.pkg import other

class K:
    import in_class

from . import relative
"""

# Names that execute when the module is imported.
_EAGER = {"plain", "pkg", "dotted", "in_if", "in_try", "in_handler", "in_finally",
          "in_for", "in_with"}

# Names that fire only when something is called.
_LAZY = {"in_function", "deferred", "in_class"}


def _fixture(tmp_path: Path) -> str:
    """Write the shape fixture.

    Returns:
        its path.

    """
    path = tmp_path / "shapes.py"
    path.write_text(_SRC, encoding="utf-8")
    return str(path)


def test_every_module_scope_import_shape_is_an_eager_edge(tmp_path: Path) -> None:
    """Imports at module scope, including inside if/try/except/finally/for/with, are all seen.

    ⚑ Those bodies DO execute on import; a walk that skipped them under-reports, the worse
    direction: a suite certified as not reaching a store that aborts when run.
    """
    got = import_edges.module_level(_fixture(tmp_path))
    assert _EAGER - got == set()


def test_imports_inside_definitions_never_leak_into_module_level(tmp_path: Path) -> None:
    """An import inside a def or class is NOT a module-level edge.

    ⚑⚑⚑ The arm that would have caught substrate's measured 54-of-99 false positive: a lazy import
    read as eager made a lexer and a text gate both "reach" a store.
    """
    assert import_edges.module_level(_fixture(tmp_path)) & _LAZY == set()


def test_deferred_imports_are_reported_separately(tmp_path: Path) -> None:
    """Imports inside definitions are returned by `deferred`, not merged into module level."""
    assert _LAZY - import_edges.deferred(_fixture(tmp_path)) == set()


def test_a_relative_import_is_not_an_edge(tmp_path: Path) -> None:
    """`from . import x` contributes no name: it names nothing an index can resolve."""
    got = import_edges.module_level(_fixture(tmp_path))
    assert "" not in got
    assert "relative" not in got


def test_an_unparseable_or_missing_file_yields_no_edges(tmp_path: Path) -> None:
    """A syntax error or a vanished file degrades to no edges rather than raising.

    ⚑ A census asks every discovered file; the failure surfaces when the file is RUN.
    """
    broken = tmp_path / "broken.py"
    broken.write_text("def (:\n", encoding="utf-8")
    assert import_edges.module_level(str(broken)) == frozenset()
    assert import_edges.deferred(str(tmp_path / "absent.py")) == frozenset()


def test_a_known_local_import_is_seen(tmp_path: Path) -> None:
    """A file with a known local import has that edge: the positive control.

    ⚑ Zero edges is what a broken reader returns AND what a stdlib-only module returns; naming a
    file whose imports are known separates the two.
    """
    path = tmp_path / "user.py"
    path.write_text("from mypkg import helper\n", encoding="utf-8")
    assert "mypkg" in import_edges.module_level(str(path))


def test_the_dotted_reading_names_submodule_candidates(tmp_path: Path) -> None:
    """`from X import Y` yields `X` and the candidate `X.Y`; the top-level reading yields `X`.

    ⚑ Every file in a package imports the package, so only the dotted reading can tell which
    module an intra-package edge points at.
    """
    path = tmp_path / "pkgfile.py"
    path.write_text("from mypkg.sub import helper\n", encoding="utf-8")
    assert import_edges.module_level_dotted(str(path)) == {"mypkg.sub", "mypkg.sub.helper"}
    assert import_edges.module_level(str(path)) == {"mypkg"}
    assert import_edges.deferred_dotted(str(path)) == frozenset()

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `atomize-imports` leaves a module's import cone where it found it (W846).

⚑⚑ A DISPATCH-TABLE MODULE'S MODULE-LEVEL IMPORTS ARE THE BASE EVERY ENTRY SHARES, so a
function-level import hoisted to module level grows every entry's cone to the whole engine
(paperkit:W296, found by diffing per-claim closure roots, original against rewritten). The rewrite
renames those imports and must never add one.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from mikemol.pycodemod import atomize

if TYPE_CHECKING:
    from pathlib import Path


def _package(tmp_path: Path) -> str:
    pkg = tmp_path / "pk"
    pkg.mkdir()
    for stem in ("bib", "other"):
        (pkg / f"{stem}.py").write_text("X = 1\n", encoding="utf-8")
    (pkg / "middle.py").write_text("from bib import PATH\n", encoding="utf-8")
    return str(pkg)


def _rewritten(tmp_path: Path, text: str) -> str:
    """Atomize a consumer of the sibling modules and return its new text.

    Returns:
        the consumer's rewritten source.

    """
    pkg = _package(tmp_path)
    path = tmp_path / "pk" / "consumer.py"
    path.write_text(text, encoding="utf-8")
    middle = str(tmp_path / "pk" / "middle.py")
    result = atomize.atomize([middle, str(path)], atomize.siblings_of(pkg), "pk")
    return result.texts[str(path)]


def _module_level_imports(text: str) -> set[str]:
    """Name the modules a text imports at module level, nested statements excluded.

    Returns:
        the dotted names of its top-level `import` statements.

    """
    return {
        alias.name
        for node in ast.parse(text).body
        if isinstance(node, ast.Import)
        for alias in node.names
    }


def test_a_dispatch_table_module_gains_no_module_level_import(tmp_path: Path) -> None:
    """The module-level imports are the original's, renamed: the closure base does not grow."""
    src = (
        "import other\nimport middle\n\n\n"
        "def a():\n    import bib\n    return other.X + bib.Y\n\n\n"
        "def b():\n    return middle.PATH\n"
    )
    assert _module_level_imports(_rewritten(tmp_path, src)) == {"pk.other", "pk.middle"}


def test_the_originals_module_level_imports_are_the_same_modules(tmp_path: Path) -> None:
    """Control: the original's own module-level imports name the same two modules."""
    src = "import other\nimport middle\n\n\ndef b():\n    return middle.PATH\n"
    assert _module_level_imports(src) == {"other", "middle"}
    assert _module_level_imports(_rewritten(tmp_path, src)) == {"pk.other", "pk.middle"}


def test_a_function_import_of_a_module_nobody_imports_at_module_level_stays_in_the_function(
    tmp_path: Path,
) -> None:
    """A lazy path stays lazy: the module is imported by the function and by no one else."""
    src = "import other\n\n\ndef f():\n    import bib\n    return other.X + bib.Y\n"
    assert "pk.bib" not in _module_level_imports(_rewritten(tmp_path, src))

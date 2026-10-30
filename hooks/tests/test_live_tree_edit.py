# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An edit importing a hooks module the built venv lacks is named before it kills a commit (W2092).

⚑ THE POSITIVE CONTROL IS THE REAL INSTANCE: commit_kata gained `from mikemol.hooks import
stackahead` before the built venv held that module and the next commit died at import.
"""

from mikemol.hooks import live_tree_edit

_BUILT = {"mikemol.hooks.commit_kata", "mikemol.hooks.gatephase"}


def test_an_import_of_a_module_the_venv_lacks_is_named_in_both_import_forms() -> None:
    """`from mikemol.hooks import x` and `import mikemol.hooks.y` both name the missing module."""
    source = "from mikemol.hooks import stackahead\nimport mikemol.hooks.flakemetric\n"
    missing = live_tree_edit.unbuilt_imports(source, _BUILT)
    assert missing == ["mikemol.hooks.flakemetric", "mikemol.hooks.stackahead"]


def test_a_held_module_and_a_foreign_import_are_not_named() -> None:
    """The negatives: a held module (either form), the package itself and non-hooks imports."""
    source = (
        "from mikemol.hooks.commit_kata import main\n"
        "from mikemol.hooks import gatephase\n"
        "import mikemol.hooks\n"
        "import json\n"
        "from mikemol.fence import guard\n"
        "from mikemol.hooksextra import thing\n"
    )
    assert live_tree_edit.unbuilt_imports(source, _BUILT) == []


def test_a_from_import_of_a_submodule_with_names_is_judged_by_the_module() -> None:
    """`from mikemol.hooks.stackahead import blobs` names the module, not `blobs`."""
    source = "from mikemol.hooks.stackahead import blobs, paths\n"
    assert live_tree_edit.unbuilt_imports(source, _BUILT) == ["mikemol.hooks.stackahead"]


def test_a_relative_import_is_unreadable_and_never_judged() -> None:
    """The caller cannot resolve it without the file's module name: it is named, not guessed."""
    source = "from . import sibling\nfrom .peer import x\nfrom ..up.deep import y\n"
    assert live_tree_edit.unbuilt_imports(source, set()) == []
    assert live_tree_edit.unreadable(source) == [".", "..up.deep", ".peer"]
    assert live_tree_edit.unreadable("import os\n") == []


def test_a_source_that_does_not_parse_names_nothing() -> None:
    """The edit's own lint refuses a syntax error; this check adds no second voice."""
    assert live_tree_edit.unbuilt_imports("from mikemol.hooks import (\n", _BUILT) == []
    assert live_tree_edit.unreadable("def broken(:\n") == []

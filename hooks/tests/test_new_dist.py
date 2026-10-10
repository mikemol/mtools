# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pure core of mikemol-new-dist, over text fixtures shaped like the real files.

W944. ⚑ THE CLEAN RENAME IS THE POSITIVE CONTROL: without it, "a bad input is refused" cannot be
told from a generator that refuses everything. Every fixture is inline, so no repository, uv or
network is read.
"""

from __future__ import annotations

import pytest

from mikemol.hooks import new_dist

_BUILD = (
    "# SPDX\n# history of pathwalk's birth (mtools:W573)\n\n"
    'load("@pathwalk_dev//:requirements.bzl", dev_requirement = "requirement")\n'
    'py_library(name = "pathwalk", srcs = glob(["src/mikemol/pathwalk/**/*.py"]))\n'
)
_PYPROJECT = (
    "[project]\n# ⚑ THE WALK extracted from pycodemod.\n# second history line\n"
    'name = "mikemol-pathwalk"\nversion = "0.1.0"\n'
    'description = "Expand directory operands."\n'
    'keywords = ["walk", "worktree"]\n\n'
    '[tool.setuptools.package-data]\n"mikemol.pathwalk" = ["py.typed"]\n\n'
    '[tool.ruff.lint.per-file-ignores]\n"tests/test_walk.py" = ["assert"]\n'
    '"src/mikemol/pathwalk/walk.py" = ["suspicious-subprocess-import"]\n'
)
_REQ_DEV = (
    "mypy==2.3.1\n    # via mikemol-atomicwrite (pyproject.toml:dev)\n"
    "pytest==9.0\n    # via mikemol-pathwalk (pyproject.toml:dev)\n"
)
_TEMPLATE = {
    "BUILD.bazel": _BUILD,
    "paper.toml": '[paper]\ntitle = "mikemol.pathwalk"\nout = "PATHWALK.md"\n',
    "pyproject.toml": _PYPROJECT,
    "requirements.txt": "# generated for pathwalk\n",
    "requirements-dev.txt": _REQ_DEV,
}
_MODULE = (
    'pip.parse(\n    hub_name = "pathwalk_deps",\n    python_version = "3.13",\n'
    '    requirements_lock = "//pathwalk:requirements.txt",\n)\n\n# next dist\n'
    'pip.parse(\n    hub_name = "pathwalk_dev",\n    python_version = "3.13",\n'
    '    uv_lock = "//pathwalk:uv.lock",\n)\n'
    'use_repo(\n    pip,\n    "pathwalk_deps",\n    "pathwalk_dev",\n    "other_deps",\n)\n'
)
_INSTALL = (
    "# Installing\n\nThere are 3 of them, listed below.\n\n"
    "- `atomicwrite` (`mikemol-atomicwrite`): durable writes. A library, no scripts.\n"
    "- `fence` (`mikemol-fence`): run a command in a cgroup. Scripts:\n  `mikemol-fence`.\n"
    "- `pathwalk` (`mikemol-pathwalk`): the walk. A library, no scripts.\n\nAfter the list.\n"
)
_TWO_ATTRIBUTIONS = 2
_NEW_ENTRY = "- `htmlstruct` (`mikemol-htmlstruct`): HTML read as structure. A library, no scripts."


def test_the_skeleton_renames_the_template_everywhere_and_cuts_its_history() -> None:
    """The positive control: the new name appears, the template's name and history do not."""
    files = new_dist.skeleton("htmlstruct", "Read HTML as structure.", _TEMPLATE)
    build = files["BUILD.bazel"]
    assert "@htmlstruct_dev" in build
    assert "src/mikemol/htmlstruct/**" in build
    assert "history of" not in build
    assert "pathwalk" not in build.replace("from //pathwalk;", "")
    py = files["pyproject.toml"]
    assert 'name = "mikemol-htmlstruct"' in py
    assert 'description = "Read HTML as structure."' in py
    assert 'keywords = ["htmlstruct"]' in py
    assert "THE WALK" not in py
    assert '"mikemol.htmlstruct" = ["py.typed"]' in py
    assert "pathwalk" not in py
    assert py.endswith('[tool.ruff.lint.per-file-ignores]\n"tests/test_smoke.py" = ["assert"]\n')


def test_the_requirements_attributions_name_the_new_distribution() -> None:
    """`via mikemol-<dist> (pyproject.toml:dev)` is retargeted whichever dist the template had."""
    dev = new_dist.skeleton("htmlstruct", "d", _TEMPLATE)["requirements-dev.txt"]
    assert dev.count("via mikemol-htmlstruct (pyproject.toml:dev)") == _TWO_ATTRIBUTIONS
    assert "atomicwrite" not in dev


def test_the_package_the_test_and_the_empty_files_are_generated() -> None:
    """A smoke test so the suite is never empty; the ratchet baseline and warrants start empty."""
    files = new_dist.skeleton("htmlstruct", "Read HTML.", _TEMPLATE)
    init = files["src/mikemol/htmlstruct/__init__.py"]
    assert init.endswith('"""mikemol.htmlstruct: Read HTML."""\n')
    assert not files["src/mikemol/htmlstruct/py.typed"]
    assert not files["ratchet-preview.txt"]
    assert not files["warrants.bib"]
    assert "import mikemol.htmlstruct as package" in files["tests/test_smoke.py"]
    assert 'out = "HTMLSTRUCT.md"' in files["paper.toml"]
    assert files["rubric.tsv"].startswith("# rubric.tsv")


@pytest.mark.parametrize("bad", ["", "Html", "9html", "html-struct", "html struct", "html_struct"])
def test_a_name_that_is_not_a_lowercase_word_is_refused(bad: str) -> None:
    """The name becomes a directory, a package, a hub and a project name."""
    with pytest.raises(ValueError, match="must match"):
        new_dist.skeleton(bad, "d", _TEMPLATE)


@pytest.mark.parametrize("bad", ["", "   ", 'has "quote"', "has \\ backslash", "two\nlines"])
def test_a_description_that_would_break_a_toml_string_is_refused(bad: str) -> None:
    """One non-empty line with no quote or backslash."""
    with pytest.raises(ValueError, match="description"):
        new_dist.skeleton("htmlstruct", bad, _TEMPLATE)


def test_a_template_missing_a_file_is_refused_by_name() -> None:
    """The refusal names what is missing."""
    partial = {k: v for k, v in _TEMPLATE.items() if k != "pyproject.toml"}
    with pytest.raises(ValueError, match=r"pyproject\.toml"):
        new_dist.skeleton("htmlstruct", "d", partial)


def test_module_edit_adds_both_hubs_and_both_use_repo_names_after_the_templates() -> None:
    """Copies of the template's blocks, placed after them, with the new name."""
    out = new_dist.module_edit(_MODULE, "htmlstruct")
    assert 'hub_name = "htmlstruct_deps"' in out
    assert 'requirements_lock = "//htmlstruct:requirements.txt"' in out
    assert 'uv_lock = "//htmlstruct:uv.lock"' in out
    assert '"pathwalk_deps",\n    "htmlstruct_deps"' in out
    assert '"pathwalk_dev",\n    "htmlstruct_dev"' in out
    assert out.count("scaffolded by mikemol-new-dist") == 1


def test_module_edit_refuses_a_present_name_or_a_missing_anchor() -> None:
    """Never a second hub of the same name; never a guess at where an absent block goes."""
    once = new_dist.module_edit(_MODULE, "htmlstruct")
    with pytest.raises(ValueError, match="already declares"):
        new_dist.module_edit(once, "htmlstruct")
    with pytest.raises(ValueError, match="exactly one"):
        new_dist.module_edit("nothing here\n", "htmlstruct")


def test_install_edit_inserts_alphabetically_and_bumps_the_count() -> None:
    """The new entry sorts between fence and pathwalk, after the multi-line fence entry."""
    out = new_dist.install_edit(_INSTALL, "htmlstruct", "HTML read as structure.")
    assert "There are 4 of them" in out
    lines = out.splitlines()
    new = lines.index(_NEW_ENTRY)
    assert lines[new - 1] == "  `mikemol-fence`."
    assert lines[new + 1].startswith("- `pathwalk`")


def test_install_edit_appends_after_the_last_entry_when_the_name_sorts_last() -> None:
    """Before the paragraph that follows the list, not at the end of the file."""
    out = new_dist.install_edit(_INSTALL, "zzz", "Last.")
    assert out.index("- `pathwalk`") < out.index("- `zzz`") < out.index("After the list.")


def test_install_edit_refuses_a_present_name_or_a_missing_count() -> None:
    """The count sentence is the anchor for the bump."""
    with pytest.raises(ValueError, match="already lists"):
        new_dist.install_edit(_INSTALL, "fence", "d")
    with pytest.raises(ValueError, match="There are N"):
        new_dist.install_edit("- `a` (`mikemol-a`): x\n", "b", "d")

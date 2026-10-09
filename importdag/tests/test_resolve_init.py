# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Importing a module also imports its packages' `__init__.py` files, and only those it spans."""

from __future__ import annotations

from mikemol.importdag.resolve import Reference, index, resolve

_PKG = (
    "src/nemik/__init__.py",
    "src/nemik/adapter.py",
    "src/nemik/model.py",
    "src/nemik/sub/__init__.py",
    "src/nemik/sub/leaf.py",
    "tools/runner.py",
)


def _files(importer: str, *refs: Reference, tree: tuple[str, ...] = _PKG) -> frozenset[str]:
    """Resolve references from one file against a tree.

    Returns:
        The files the importer's references mean, parents included.

    """
    return resolve(importer, refs, index(tree)).files


def test_an_absolute_import_carries_the_package_initializer() -> None:
    """`nemik.model` is model.py and also the package it lives in (the measured W792 case)."""
    got = _files("tools/runner.py", Reference(0, "nemik.model"))
    assert got == {"src/nemik/model.py", "src/nemik/__init__.py"}


def test_every_package_directory_the_name_spans_contributes_outermost_first() -> None:
    """`nemik.sub.leaf` runs nemik/__init__ and nemik/sub/__init__ before leaf."""
    got = _files("tools/runner.py", Reference(0, "nemik.sub.leaf"))
    assert got == {
        "src/nemik/sub/leaf.py",
        "src/nemik/sub/__init__.py",
        "src/nemik/__init__.py",
    }


def test_a_suffix_name_spans_only_the_directories_it_names() -> None:
    """`sub.leaf` runs sub/__init__ and not nemik/__init__, whose role the suffix cannot know."""
    got = _files("tools/runner.py", Reference(0, "sub.leaf"))
    assert got == {"src/nemik/sub/leaf.py", "src/nemik/sub/__init__.py"}


def test_importing_a_package_by_name_carries_its_outer_packages() -> None:
    """`nemik.sub` is sub/__init__.py, and nemik/__init__.py runs before it."""
    got = _files("tools/runner.py", Reference(0, "nemik.sub"))
    assert got == {"src/nemik/sub/__init__.py", "src/nemik/__init__.py"}


def test_a_relative_import_counts_from_its_base_directory() -> None:
    """`from .model import x` in adapter.py names model.py and the package it sits in."""
    got = _files("src/nemik/adapter.py", Reference(1, "model"))
    assert got == {"src/nemik/model.py", "src/nemik/__init__.py"}


def test_a_relative_climb_counts_from_the_climbed_directory() -> None:
    """`from ..model import x` in sub/leaf.py starts at nemik/, so nemik/__init__ is the base."""
    got = _files("src/nemik/sub/leaf.py", Reference(2, "model"))
    assert got == {"src/nemik/model.py", "src/nemik/__init__.py"}


def test_a_file_is_never_its_own_import() -> None:
    """A package's own __init__.py importing its submodule does not gain an edge to itself."""
    got = _files("src/nemik/__init__.py", Reference(1, "model"))
    assert got == {"src/nemik/model.py"}


def test_a_directory_without_an_initializer_contributes_nothing() -> None:
    """A namespace package has no file to import, so the module alone is the edge."""
    tree = ("lib/ns/core.py", "app/main.py")
    assert _files("app/main.py", Reference(0, "ns.core"), tree=tree) == {"lib/ns/core.py"}


def test_a_top_level_module_has_no_package_to_carry() -> None:
    """A file at the root has no parent directory, so nothing is added."""
    tree = ("util.py", "main.py")
    assert _files("main.py", Reference(0, "util"), tree=tree) == {"util.py"}

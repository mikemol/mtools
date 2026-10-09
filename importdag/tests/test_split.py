# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `split`: which imports fire when a module is imported, and which only later."""

from __future__ import annotations

from mikemol.importdag.resolve import Reference, references, split


def _names(found: frozenset[Reference]) -> set[str]:
    """Return the dotted names of the references, levels dropped.

    Returns:
        The set of names.

    """
    return {ref.name for ref in found}


def test_a_module_scope_import_is_eager() -> None:
    """`import a` at the top of a module fires when the module is imported."""
    got = split("import a\nfrom b import c\n")
    assert _names(got.eager) == {"a", "b", "b.c"}
    assert got.deferred == frozenset()


def test_an_import_inside_a_function_is_deferred() -> None:
    """An import in a def fires only when the function is called."""
    got = split("def f():\n    import a\n")
    assert got.eager == frozenset()
    assert _names(got.deferred) == {"a"}


def test_an_import_under_a_guard_is_still_eager() -> None:
    """An if, try, with or loop at module scope still runs on import."""
    text = "if X:\n    import a\ntry:\n    import b\nexcept E:\n    import c\n"
    assert _names(split(text).eager) == {"a", "b", "c"}


def test_an_import_under_try_star_is_eager() -> None:
    """A `try*` is a try for this purpose; it must not drop its imports."""
    got = split("try:\n    import a\nexcept* E:\n    import b\n")
    assert _names(got.eager) == {"a", "b"}


def test_a_nested_function_import_is_deferred() -> None:
    """A def inside a def, inside a guard, is deferred however deep."""
    got = split("if X:\n    def f():\n        def g():\n            import a\n")
    assert got.eager == frozenset()
    assert _names(got.deferred) == {"a"}


def test_a_class_body_import_is_deferred_as_corpus_has_it() -> None:
    """The split agrees with corpus.import_edges, which counts a class body deferred (W861)."""
    got = split("class C:\n    import a\n")
    assert got.eager == frozenset()
    assert _names(got.deferred) == {"a"}


def test_a_relative_import_keeps_its_level() -> None:
    """The split keeps the dots, which the resolver needs."""
    got = split("from . import x\n")
    assert got.eager == frozenset({Reference(1, ""), Reference(1, "x")})


def test_the_two_halves_together_are_every_reference() -> None:
    """Eager and deferred cover exactly what `references` finds, so nothing is lost."""
    text = "import a\ndef f():\n    from b import c\nif X:\n    import d\n"
    got = split(text)
    assert got.eager | got.deferred == references(text)


def test_a_text_that_does_not_parse_has_no_references() -> None:
    """Syntax errors yield two empty halves rather than raising."""
    got = split("def (:\n")
    assert got.eager == frozenset()
    assert got.deferred == frozenset()

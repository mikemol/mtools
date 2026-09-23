# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The mutation grid addresses each def-site by a qualified path, so same-named defs are distinct.

⚑⚑⚑ WRITTEN AGAINST A MEASURED DEFECT. `mutate(source, name)` mutated the FIRST def carrying a
bare name, so every same-named def in a module was reported as its own site and mutated the same
node. On ratchet a Protocol stub `parse` came back SURVIVED three times: each `parse` mutated the
stub. Every test here fails on the bare-name runner by assertion, not by an error.
"""

from __future__ import annotations

import ast

import mutate_runner

_MUTANT = "raise AssertionError('mutant')"

_TWO_CLASSES = """\
class First:
    def run(self):
        return 1


class Second:
    def run(self):
        return 2
"""

_PROTOCOL_AND_IMPL = """\
from typing import Protocol


class Parser(Protocol):
    def parse(self, text: str) -> str: ...


def parse(text: str) -> str:
    return text.strip()
"""

_NESTED = """\
def outer():
    def inner():
        return 1
    return inner()


def inner():
    return 2
"""

_UNIQUE = """\
def alpha():
    \"\"\"Doc.\"\"\"
    return 1


def beta():
    return 2
"""


def _paths(source: str) -> list[str]:
    """Return each site's address, asserting first that a site carries one at all.

    Returns:
        the qualified paths `sites` reports, in its order.

    """
    found = mutate_runner.sites(ast.parse(source))
    assert all(isinstance(site, tuple) for site in found), "a site must carry its qualified path"
    return [path for path, _node in found]


def _body_of(source: str, path: str) -> str:
    """Return the unparsed body of the def at `path` in `source`.

    Returns:
        the body's statements, unparsed, one per line.

    Raises:
        LookupError: when no def-site carries that path.

    """
    for got, node in mutate_runner.sites(ast.parse(source)):
        if got == path:
            return "\n".join(ast.unparse(stmt) for stmt in node.body)
    raise LookupError(path)


def test_methods_of_two_classes_are_two_sites_and_the_second_mutates_the_second() -> None:
    """Two classes' `run` methods are distinct sites, and mutating one leaves the other alone."""
    assert _paths(_TWO_CLASSES) == ["First.run", "Second.run"]
    mutant = mutate_runner.mutate(_TWO_CLASSES, "Second.run")
    assert _body_of(mutant, "Second.run") == _MUTANT
    assert _body_of(mutant, "First.run") == "return 1"


def test_a_protocol_stub_and_a_function_of_its_name_are_separate_sites() -> None:
    """A Protocol stub and a same-named function are two sites; the function mutates itself."""
    assert _paths(_PROTOCOL_AND_IMPL) == ["Parser.parse", "parse"]
    mutant = mutate_runner.mutate(_PROTOCOL_AND_IMPL, "parse")
    assert _body_of(mutant, "parse") == _MUTANT
    assert _body_of(mutant, "Parser.parse") == "..."


def test_a_nested_def_is_addressed_through_its_enclosing_function() -> None:
    """A nested def is `outer.<locals>.inner`, distinct from a module-level `inner`."""
    assert _paths(_NESTED) == ["outer", "outer.<locals>.inner", "inner"]
    mutant = mutate_runner.mutate(_NESTED, "inner")
    assert _body_of(mutant, "inner") == _MUTANT
    assert _body_of(mutant, "outer.<locals>.inner") == "return 1"


def test_a_module_of_unique_names_is_addressed_and_mutated_as_before() -> None:
    """Positive control: unique top-level names keep their bare paths and the same mutant."""
    assert _paths(_UNIQUE) == ["alpha", "beta"]
    mutant = mutate_runner.mutate(_UNIQUE, "alpha")
    assert _body_of(mutant, "alpha") == f"'Doc.'\n{_MUTANT}"
    assert _body_of(mutant, "beta") == "return 2"

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The one site finder both the declared specs and the dist grid use (W1761).

Each policy field is a point on which the two old finders differed, so each has a witness (a
source where the fields give different answers) and the controls are the other policy on the same
source.
"""

import ast

from mikemol.mutation import sitewalk

_SOURCE = """
def top():
    x = 1
    return x

def one(): return 1

async def fetch():
    def inner():
        return 1
    return inner

class Box:
    def put(self):
        def helper():
            return 2
        return helper

    @property
    def size(self):
        return 1

    @size.setter
    def size(self, value):
        return value

    pick = lambda: 0
"""

_PROTOCOLS = """
import typing
import typing_extensions
from typing import Protocol

class Bare(Protocol):
    def a(self):
        ...

class Qualified(typing.Protocol):
    def b(self):
        ...

class Extended(typing_extensions.Protocol):
    def c(self):
        ...

class Subscripted(Protocol[int]):
    def d(self):
        ...

class Plain:
    def e(self):
        return 1
"""


def _paths(source: str, policy: sitewalk.Policy) -> list[str]:
    return [site.path for site in sitewalk.walk(ast.parse(source), policy)]


def test_the_definition_policy_skips_one_liners_names_plainly_and_keeps_async_defs() -> None:
    """The declared-spec scope: `outer.inner`, async defs are sites, a one-liner is not."""
    assert _paths(_SOURCE, sitewalk.DEFINITION) == [
        "top",
        "fetch",
        "fetch.inner",
        "Box.put",
        "Box.put.helper",
        "Box.size",
        "Box.size",
    ]


def test_the_grid_policy_keeps_one_liners_marks_locals_and_labels_repeats() -> None:
    """The dist grid: Python's own `<locals>` path, `#2` on a repeat, async defs only walked."""
    assert _paths(_SOURCE, sitewalk.GRID) == [
        "top",
        "one",
        "fetch.<locals>.inner",
        "Box.put",
        "Box.put.<locals>.helper",
        "Box.size",
        "Box.size#2",
    ]


def test_a_nested_def_has_no_owner_and_a_method_has_its_class() -> None:
    """The owner is the class a method sits directly in, never a function's enclosing class."""
    owners = {
        site.path: (site.owner.name if site.owner else None)
        for site in sitewalk.walk(ast.parse(_SOURCE), sitewalk.GRID)
    }
    assert owners["Box.put"] == "Box"
    assert owners["Box.put.<locals>.helper"] is None
    assert owners["top"] is None


def test_a_protocols_methods_are_never_sites_under_either_policy() -> None:
    """Bare, qualified, extended and subscripted bases are all Protocols; a plain class is not."""
    for policy in (sitewalk.DEFINITION, sitewalk.GRID):
        assert _paths(_PROTOCOLS, policy) == ["Plain.e"]


def test_a_class_with_no_protocol_base_is_not_one() -> None:
    """The control for the rule above: `is_protocol` is false for a plain class and no bases."""
    plain, other = ast.parse("class A: ...\nclass B(Base): ...").body
    assert isinstance(plain, ast.ClassDef)
    assert isinstance(other, ast.ClassDef)
    assert not sitewalk.is_protocol(plain)
    assert not sitewalk.is_protocol(other)

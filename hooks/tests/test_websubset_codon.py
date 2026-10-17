# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the Codon-only refusal rules (mtools:W1324): each beside its clean control.

⚑ EACH RULE FIRES FOR THE codon TARGET AND NOT FOR py2many, and NOT ON THE NEAREST ACCEPTED SHAPE:
a bare `@dataclass`, `except A:`, `*args` beside keyword-only parameters, and `import typing`.
"""

from __future__ import annotations

from mikemol.hooks import websubset

_PLANTS: dict[str, str] = {
    "future-import": "from __future__ import annotations\n",
    "type-statement": "type Row = tuple[int, str]\n",
    "keyword-only-star": "def f(a: int, *, b: int) -> int:\n    return a\n",
    "dataclass-decorator-args": "@dataclass(frozen=True)\nclass P:\n    x: int\n",
    "tuple-except": "try:\n    pass\nexcept (A, B):\n    pass\n",
    "type-checking-import": "from typing import TYPE_CHECKING\n",
    "datetime-utc": "x = datetime.UTC\n",
    "dict-spread": "b = {**a, 'y': 2}\n",
    "stdlib-import": "import subprocess\nfrom hashlib import sha256\nimport os.path, io.x\n",
    "dataclasses-import": "from dataclasses import dataclass\nimport dataclasses\n",
    "variable-length-tuple": "x: tuple[str, ...] = ()\ny: Tuple[int, ...] = ()\n",
    "undefined-builtin": "x = frozenset([1])\ny = callable(print)\n",
    "union-none": (
        "def f(a: int) -> int | None:\n"
        "    return a\n"
        "def g(b: list[int] | None) -> int:\n"
        "    return 0\n"
    ),
}
_CLEAN = (
    "import typing\n"
    "import json\n"
    "from datetime import timezone\n"
    "@dataclass\n"
    "class P:\n"
    "    x: int\n"
    "def f(a: int, *rest: int, b: int) -> int:\n"
    "    return a\n"
    "try:\n"
    "    pass\n"
    "except A:\n"
    "    pass\n"
    "b = {'y': 2}\n"
    "pair: tuple[int, str] = (1, 'a')\n"
    "rows: list[str] = []\n"
    "from typing import Optional\n"
    "def h(a: int) -> Optional[int]:\n"
    "    return a\n"
)


def _rules(source: str, target: str) -> set[str]:
    return {finding.rule for finding in websubset.check(source, target) if finding.rule != "syntax"}


def test_each_codon_rule_fires_on_its_plant_for_codon_and_not_for_py2many() -> None:
    """Every plant is found by the codon target under its own id, and py2many reports nothing."""
    for rule, source in _PLANTS.items():
        assert rule in _rules(source, "codon")
        assert not _rules(source, "py2many")


def test_the_nearest_accepted_shapes_raise_no_codon_rule() -> None:
    """Bare `@dataclass`, `except A`, `*rest` beside keyword-only, and `import typing` are clean."""
    assert not _rules(_CLEAN, "codon") - websubset.RULES["py2many"]

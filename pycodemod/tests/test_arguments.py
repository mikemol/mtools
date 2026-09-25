# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.arguments`: every reading reports every side of its split.

⚑⚑ `f(**cfg)` IS THE ARM: the origin called it LACKING the keyword, which `cfg` may well carry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import arguments as args
from mikemol.pycodemod import core, sites

if TYPE_CHECKING:
    from pathlib import Path

_CALLS = """f(k=1)
f(k=x)
f()
f(**cfg)
if a:
    f(1, k=None)
g(k=2)
"""


def _file(tmp_path: Path) -> str:
    path = tmp_path / "m.py"
    path.write_text(_CALLS, encoding="utf-8")
    return str(path)


def _lines(wheres: list[args.Where]) -> list[int]:
    return [w.line for w in wheres]


def test_forwards_has_a_side_for_the_splat(tmp_path: Path) -> None:
    """⚑⚑ Passes, lacks, and cannot-tell: a `**cfg` call is never counted as lacking."""
    got = args.forwards(sites.scan([_file(tmp_path)], "f"), "k")
    assert (_lines(got.passes), _lines(got.lacks), _lines(got.cannot_tell)) == (
        [1, 2, 6],
        [3],
        [4],
    )


def test_asserted_splits_literal_from_computed(tmp_path: Path) -> None:
    """`None` is a literal; a name is computed; a call not passing the keyword is on no side."""
    got = args.asserted(sites.scan([_file(tmp_path)], "f"), "k")
    assert (_lines(got.literal), _lines(got.computed)) == ([1, 6], [2])


def test_values_report_the_constant_or_unknown_over_the_total(tmp_path: Path) -> None:
    """⚑⚑ Never a guess: `k=x` is UNKNOWN, `k=None` is None, and the denominator is every call."""
    path = _file(tmp_path)
    got = args.values(sites.scan([path], "f"), "k")
    assert [(r.where.line, r.value, r.context) for r in got.rows] == [
        (1, 1, "<module>"),
        (2, core.UNKNOWN, "<module>"),
        (6, None, "<module>"),
    ]
    assert got.total == len(sites.scan([path], "f").facts)


def test_an_int_reads_a_position(tmp_path: Path) -> None:
    """An ordinal reads the positional argument; a `**` splat holds no position."""
    got = args.values(sites.scan([_file(tmp_path)], "f"), 0)
    assert [(r.where.line, r.value) for r in got.rows] == [(6, 1)]


def test_guarded_splits_calls_under_a_test_from_the_top(tmp_path: Path) -> None:
    """A call under `if a:` carries the test; every other call is at the top of its scope."""
    got = args.guarded(sites.scan([_file(tmp_path)], "f"))
    assert [(w.line, conds) for w, conds in got.under] == [(6, ("a",))]
    assert _lines(got.top) == [1, 2, 3, 4]


def test_values_many_reads_several_callees_from_one_scan(tmp_path: Path) -> None:
    """Each callee's rows and total, from one unnarrowed scan; an absent callee has total 0."""
    got = args.values_many(sites.scan([_file(tmp_path)]), {"f": "k", "g": "k", "h": 0})
    assert [(r.where.line, r.value) for r in got["g"].rows] == [(7, 2)]
    assert (got["f"].total, got["g"].total, got["h"].total) == (5, 1, 0)


def test_values_many_refuses_a_narrowed_scan(tmp_path: Path) -> None:
    """⚑⚑ A scan narrowed to `f` would report `g` as never called: a zero about the scan."""
    with pytest.raises(ValueError, match="unnarrowed"):
        args.values_many(sites.scan([_file(tmp_path)], "f"), {"g": "k"})


def test_calls_filter_by_callee_in_span_order(tmp_path: Path) -> None:
    """`calls` keeps span order and filters by callee name when asked."""
    got = sites.scan([_file(tmp_path)])
    assert [(w.line, f.name) for w, f in args.calls(got, "g")] == [(7, "g")]
    assert len(args.calls(got)) == len(got.facts)


def test_missing_renders_as_a_word() -> None:
    """The not-passed sentinel renders as a word, never as data."""
    assert repr(args.MISSING) == "MISSING"

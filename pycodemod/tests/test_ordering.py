# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.ordering`: the producer census and the re-sort span query.

⚑⚑ `count` IS THE PRODUCER ARM: the origin read `n += 1; return n` as a reified collection. It
must be absent while `union`, built by `|=`, is present.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import ordering

if TYPE_CHECKING:
    from pathlib import Path

_PRODUCERS = """import collections
def names(xs):
    return sorted(xs)
def lit():
    return {1}
def comp(xs):
    return [x for x in xs]
def acc(xs):
    out = []
    for x in xs:
        out.append(x)
    return out
def count(xs):
    n = 0
    for _ in xs:
        n += 1
    return n
def union(xs):
    s = set()
    s |= xs
    return s
def counter(xs):
    return collections.Counter(xs)
class K:
    def keys(self):
        return sorted(self.d)
def scalar():
    return 1
async def later(xs):
    return sorted(xs)
"""

_CONSUMERS = """def use(xs, k):
    a = sorted(names(xs))
    b = sorted(names(xs), key=len)
    c = sorted(k.keys())
    d = sorted(other(xs))
    return a, b, c, d
class C:
    def m(self, xs):
        return sorted(names(xs))
async def a(xs):
    return sorted(later(xs))
"""


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_reifies_finds_every_shape_and_not_an_integer_counter(tmp_path: Path) -> None:
    """⚑⚑ Literals, comprehensions, builders and accumulators are found; `n += 1` is not one."""
    prod = _write(tmp_path, "prod.py", _PRODUCERS)
    got = ordering.reifies([prod])
    assert [(r.line, r.name, r.kind, r.why) for r in got.rows] == [
        (3, "names", "sorted", "returns-sorted"),
        (5, "lit", "set", "returns-literal"),
        (7, "comp", "list", "returns-comp"),
        (12, "acc", "accum", "returns-accum"),
        (21, "union", "accum", "returns-accum"),
        (23, "counter", "dict", "returns-call"),
        (26, "K.keys", "sorted", "returns-sorted"),
        (30, "later", "sorted", "returns-sorted"),
    ]


def test_resorts_pair_a_consumer_with_its_producer(tmp_path: Path) -> None:
    """⚑⚑ A redundant re-sort, a rekeyed one, and neither for an unknown producer — each located."""
    prod = _write(tmp_path, "prod.py", _PRODUCERS)
    cons = _write(tmp_path, "cons.py", _CONSUMERS)
    got = ordering.resorts([cons], ordering.reifies([prod, cons]))
    assert [(r.line, r.caller, r.callee, r.why, r.producers) for r in got.rows] == [
        (2, "use", "names", "resort-of-sorted", ((prod, 3),)),
        (3, "use", "names", "resort-rekeyed", ((prod, 3),)),
        (4, "use", "keys", "resort-of-sorted", ((prod, 26),)),
        (9, "C.m", "names", "resort-of-sorted", ((prod, 3),)),
        (11, "a", "later", "resort-of-sorted", ((prod, 30),)),
    ]


def test_both_censuses_report_every_file_they_could_not_read(tmp_path: Path) -> None:
    """⚑ An unread file is a skip in each census, never an empty result."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    bad = _write(tmp_path, "bad.py", "def (:\n")
    missing = str(tmp_path / "absent.py")
    paths = [str(latin), bad, missing]
    reified = ordering.reifies(paths)
    for got in (reified.skipped, ordering.resorts(paths, reified).skipped):
        assert [(s.path, s.why) for s in got] == [
            (str(latin), "undecodable"),
            (bad, "unparseable"),
            (missing, "unreadable"),
        ]

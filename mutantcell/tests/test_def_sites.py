# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `def_sites`: the mutation surface of a source, and where each site sits."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.mutantcell import def_sites

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_USAGE_EXIT = 2
# line:  1 class A:
#        2     def method(self):
#        3         def inner():
#        4             return 1
#        5         return inner
#        6     def one_liner(self): return 2
#        7 def top():
#        8     return 3
#        9 async def coro():
#       10     return 4
_SOURCE = (
    "class A:\n"
    "    def method(self):\n"
    "        def inner():\n"
    "            return 1\n"
    "        return inner\n"
    "    def one_liner(self): return 2\n"
    "def top():\n"
    "    return 3\n"
    "async def coro():\n"
    "    return 4\n"
)


def test_def_sites_lists_qualified_body_isolable_defs_in_source_order() -> None:
    """Methods and nested defs are qualname-prefixed; the one-liner is not a site."""
    assert def_sites.def_sites(_SOURCE) == ["A.method", "A.method.inner", "top", "coro"]


def test_def_sites_walks_into_non_def_blocks() -> None:
    """A def inside an `if` block still counts, under the enclosing prefix."""
    text = "if True:\n    def guarded():\n        return 1\ntry:\n    pass\nexcept E:\n    pass\n"
    assert def_sites.def_sites(text) == ["guarded"]


def test_def_sites_of_unparseable_text_is_empty() -> None:
    """A source that does not parse has no sites: the sweep skips it rather than failing."""
    assert def_sites.def_sites("def (:\n") == []


def test_def_lines_locates_every_def_and_class_including_one_liners() -> None:
    """Classes and the one-liner appear, each as `(first_line, last_line)`."""
    assert def_sites.def_lines(_SOURCE) == {
        "A": (1, 6),
        "A.method": (2, 5),
        "A.method.inner": (3, 4),
        "A.one_liner": (6, 6),
        "top": (7, 8),
        "coro": (9, 10),
    }


def test_def_lines_of_unparseable_text_is_empty() -> None:
    """An unparseable source has no locations."""
    assert def_sites.def_lines("def (:\n") == {}


def test_main_prints_relpath_tab_qualname_per_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The bare output is `relpath<TAB>qualname`, one line per site, per file in order."""
    one = tmp_path / "one.py"
    one.write_text(_SOURCE, encoding="utf-8")
    two = tmp_path / "two.py"
    two.write_text("def solo():\n    return 1\n", encoding="utf-8")
    assert def_sites.main([str(one), str(two)]) == 0
    one_name, two_name = str(one), str(two)
    assert capsys.readouterr().out == (
        f"{one_name}\tA.method\n{one_name}\tA.method.inner\n{one_name}\ttop\n"
        f"{one_name}\tcoro\n{two_name}\tsolo\n"
    )


def test_main_with_lines_adds_the_span_column_and_the_flag_is_not_a_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--lines` prints `relpath<TAB>qualname<TAB>first-last` for every def and class."""
    src = tmp_path / "one.py"
    src.write_text("def top():\n    return 3\n", encoding="utf-8")
    assert def_sites.main(["--lines", str(src)]) == 0
    assert capsys.readouterr().out == f"{src}\ttop\t1-2\n"


def test_main_without_a_file_is_a_usage_refusal(capsys: pytest.CaptureFixture[str]) -> None:
    """No operand: usage on stderr, nothing on stdout, exit 2."""
    assert def_sites.main([]) == _USAGE_EXIT
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err.startswith("usage: def_sites.py [--lines] <file.py> ...")


def test_main_reads_sys_argv_when_given_no_argument(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The console-script path: `main()` takes its operands from `sys.argv[1:]`."""
    src = tmp_path / "one.py"
    src.write_text("def top():\n    return 3\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["def_sites", str(src)])
    assert def_sites.main() == 0
    assert capsys.readouterr().out == f"{src}\ttop\n"

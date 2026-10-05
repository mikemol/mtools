# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `declarations`: a distribution's declared defect classes, read and planted."""

from __future__ import annotations

import pytest

from mikemol.mutation import declarations, regexop

SRC = """\
def key(code, rel):
    return f"{code}::{rel}"
"""
TWO = (
    "# the defect classes this distribution fears\n"
    "\n"
    "src/mikemol/x/a.py|gains-line|return f|return 1; f|def=key\n"
    "  # an indented comment is a comment too\n"
    "src/mikemol/x/b.py|gains-line|a%7Cb|c|\n"
)
LABELS = ["src/mikemol/x/a.py::gains-line", "src/mikemol/x/b.py::gains-line"]
TWO_MODULES = 2


def test_a_declaration_file_is_read_in_order_skipping_comments_and_blank_lines() -> None:
    """Two declarations come back in file order; the module and the four spec fields are split."""
    got = declarations.read_declarations(TWO)
    assert [d.label for d in got] == LABELS
    first = regexop.RegexSpec("gains-line", "return f", "return 1; f", def_name="key")
    assert got[0].spec == first
    assert got[1].spec.pattern == "a|b"


def test_an_empty_or_comment_only_file_declares_nothing() -> None:
    """None by default: no text, or only comments, is no declaration and no error."""
    assert declarations.read_declarations("") == []
    assert declarations.read_declarations("# nothing yet\n\n") == []


def test_a_line_without_a_module_field_is_refused_with_its_number() -> None:
    """A line that is not `<module>|...` is refused, naming the line, never skipped."""
    with pytest.raises(ValueError, match=r"line 2: want <module>\|"):
        declarations.read_declarations("# ok\nnot-a-declaration\n")


@pytest.mark.parametrize("module", ["", "/etc/x.py", "../x.py", "a/../../x.py", "src/x.txt"])
def test_a_module_outside_the_distribution_or_not_python_is_refused(module: str) -> None:
    """An empty, absolute, climbing or non-`.py` module is refused by line number."""
    with pytest.raises(ValueError, match=r"line 1: module .* must be a relative \.py path"):
        declarations.read_declarations(f"{module}|n|a|b|\n")


def test_a_bad_spec_field_or_regex_is_refused_with_its_number() -> None:
    """A bad scope and an invalid regex each carry the line they were found on."""
    with pytest.raises(ValueError, match=r"line 1: .*bad scope"):
        declarations.read_declarations("a.py|n|a|b|nope\n")
    with pytest.raises(ValueError, match=r"line 2: "):
        declarations.read_declarations("a.py|n|a|b|\na.py|m|(|b|\n")


def test_a_name_declared_twice_for_one_module_is_refused() -> None:
    """The same name twice in one module is refused; the same name in another module is fine."""
    with pytest.raises(ValueError, match=r"line 2: 'n' is declared twice for a\.py"):
        declarations.read_declarations("a.py|n|a|b|\na.py|n|c|d|\n")
    got = declarations.read_declarations("a.py|n|a|b|\nb.py|n|a|b|\n")
    assert len(got) == TWO_MODULES


def test_plant_rewrites_the_source_where_the_pattern_matches() -> None:
    """A matching spec returns the perturbed source; the unmatched part stays byte-identical."""
    spec = regexop.RegexSpec("gains-line", r'f"\{code\}::\{rel\}"', 'f"{code}::{rel}:{1}"')
    assert declarations.plant(SRC, spec) == SRC.replace('f"{code}::{rel}"', 'f"{code}::{rel}:{1}"')


def test_plant_answers_none_for_a_stale_spec_never_an_unchanged_source() -> None:
    """A pattern matching nothing, or a def the module lacks, plants nothing: None."""
    assert declarations.plant(SRC, regexop.RegexSpec("stale", "nothing-here", "x")) is None
    ghost = regexop.RegexSpec("ghost", "return", "pass", def_name="missing")
    assert declarations.plant(SRC, ghost) is None


def test_plant_lets_a_rewrite_that_breaks_the_source_raise() -> None:
    """A rewrite leaving unparseable source is a bad declaration: the ValueError propagates."""
    with pytest.raises(ValueError, match="does not parse"):
        declarations.plant(SRC, regexop.RegexSpec("breaks", "return", "return ("))

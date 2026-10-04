# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bibparse`: the strict grammar, verbatim values, and errors that name places."""

from __future__ import annotations

import pytest

from mikemol.bibparse.bibparse import BibSyntaxError, Entry, Position, parse

_WIDTH = 100

_RUNAWAY = "@misc{k,\n  claim = {never {closes}\n  check = {cmd:true},\n"
_BAD_CASES = [
    # text, message fragment, line, col
    (_RUNAWAY, "unterminated value", 2, 11),
    ("@misc{k,\n  a = {1},\n  a = {2},\n}", "field `a` is given twice in `k`", 3, 3),
    ("@misc(k,\n}", "paren-delimited entries", 1, 6),
    ("@string{x = {y}}", "`@string` is not supported", 1, 9),
    ("@Preamble{x}", "`@preamble` is not supported", 1, 11),
    ("@comment{x}", "`@comment` is not supported", 1, 10),
    ("@misc k,", "expected `{` after `@misc`", 1, 7),
    ("@misc{k\n a = {1}}", "expected `,` after the key `k`", 2, 2),
    ("@misc{k,\n a {1}}", "expected `=` after field `a` in `k`", 2, 4),
    ("@misc{k,\n a = 1}", "must have a `{...}` value", 2, 6),
    ("@misc{k,\n a = {1} b = {2}}", "expected `,` or `}` after field `a` in `k`", 2, 10),
    ("@misc{k,\n a = {1},\n", "unterminated entry `k`", 1, 1),
    ("hello", "expected `@` to start an entry", 1, 1),
    ("@{k,", "expected an entry type after `@`", 1, 2),
    ("@misc{,", "expected an entry key", 1, 7),
    ("@misc{k,\n = {1}}", "expected a field name in `k`", 2, 2),
]


@pytest.mark.parametrize(("text", "fragment", "line", "col"), _BAD_CASES)
def test_malformed_input_raises_naming_its_message_and_position(
    text: str,
    fragment: str,
    line: int,
    col: int,
) -> None:
    """Every refusal is a BibSyntaxError carrying its line and column, never a partial result."""
    with pytest.raises(BibSyntaxError) as caught:
        parse(text, "x.bib")
    assert fragment in str(caught.value)
    assert caught.value.lineno == line
    assert caught.value.offset == col
    assert caught.value.path == "x.bib"
    assert str(caught.value).startswith(f"x.bib:{line}:{col}: ")


def test_default_path_is_the_bib_placeholder() -> None:
    """Without a path the position reads `<bib>`."""
    with pytest.raises(BibSyntaxError) as caught:
        parse("hello")
    assert str(caught.value).startswith("<bib>:1:1: expected `@`")


def test_unterminated_value_names_the_opening_brace_and_quotes_nothing() -> None:
    """The runaway case points at where the value OPENED and carries no excerpt line."""
    with pytest.raises(BibSyntaxError) as caught:
        parse(_RUNAWAY)
    assert "\n" not in caught.value.msg
    assert caught.value.msg.endswith("is swallowed into this one")


def test_error_quotes_its_own_line_stripped() -> None:
    """The excerpt is the offending line only, stripped, on its own indented line."""
    with pytest.raises(BibSyntaxError) as caught:
        parse("@misc{k,\n a {1}}\n@misc{j, a = {1}}")
    assert caught.value.msg.endswith("\n    a {1}}")


def test_error_on_the_last_line_without_a_newline_quotes_it_whole() -> None:
    """An error on an unterminated final line still quotes that line."""
    with pytest.raises(BibSyntaxError) as caught:
        parse("@misc(k,")
    assert caught.value.msg.endswith("\n    @misc(k,")


def test_error_excerpt_is_cut_to_the_width() -> None:
    """A long offending line is quoted only up to the width."""
    line = "@misc(" + "x" * 3 * _WIDTH
    with pytest.raises(BibSyntaxError) as caught:
        parse(line)
    assert caught.value.msg.split("\n    ")[1] == line[:_WIDTH]


def test_a_syntax_error_built_directly_carries_its_position() -> None:
    """With no excerpt the message is one line; an excerpt is appended stripped."""
    plain = BibSyntaxError("boom", Position("f.bib", 4, 7))
    assert plain.msg == "f.bib:4:7: boom"
    assert (plain.path, plain.lineno, plain.offset) == ("f.bib", 4, 7)
    quoted = BibSyntaxError("boom", Position("f.bib", 4, 7), "   text  ")
    assert quoted.msg == "f.bib:4:7: boom\n    text"
    assert isinstance(quoted, SyntaxError)


def test_a_column_zero_brace_inside_a_field_does_not_truncate_the_entry() -> None:
    """The defect the parser exists to remove: a line-initial closing brace closes its own only."""
    text = "@misc{k,\n  claim = {x {y\n}\n  z},\n  check = {cmd:true},\n}\n"
    entries = parse(text)
    assert len(entries) == 1
    assert entries[0].fields == {"claim": "x {y\n}\n  z", "check": "cmd:true"}


def test_entry_records_type_key_fields_in_order_and_start_line() -> None:
    """Types are lowercased, keys keep their punctuation, fields keep file order."""
    text = (
        "% header\n@MISC{a-b.c:d/e+f,\n  z = {1},\n  a = {2},\n  m = {3},\n}\n\n"
        "@book{k2, y = {4}}\n"
    )
    first, second = parse(text)
    assert (first.typ, first.key, first.line) == ("misc", "a-b.c:d/e+f", 2)
    assert list(first.fields) == ["z", "a", "m"]
    assert (second.typ, second.key, second.line) == ("book", "k2", 8)
    assert second.fields == {"y": "4"}


def test_values_are_verbatim_and_a_trailing_comma_is_optional() -> None:
    """A trailing space is meaningful, an empty value is empty, and the last comma is optional."""
    assert parse("@misc{k, join = {. }, e = {}, }")[0].fields == {"join": ". ", "e": ""}
    assert parse("@misc{k, a = {1}}")[0].fields == {"a": "1"}


def test_percent_comments_are_skipped_between_and_inside_entries() -> None:
    """A `%` comment is lexer trivia, even one holding a brace or a bare `@`."""
    text = "% [@key] and }\n@misc{k,\n % } comment\n a = {1}, % tail\n}\n% end"
    assert [e.fields for e in parse(text)] == [{"a": "1"}]


def test_nested_and_escaped_braces_are_counted_correctly() -> None:
    """Nesting balances, an escaped brace does not count, an escaped backslash does not escape."""
    nested = parse("@misc{k, a = {a {b {c}} d}}")[0].fields["a"]
    assert nested == "a {b {c}} d"
    assert parse("@misc{k, a = {a \\} b}}")[0].fields["a"] == "a \\} b"
    assert parse("@misc{k, a = {a \\{ b}}")[0].fields["a"] == "a \\{ b"
    assert parse("@misc{k, a = {a \\\\}}")[0].fields["a"] == "a \\\\"


def test_an_at_sign_inside_a_value_is_just_text() -> None:
    """Only an `@` between entries starts one."""
    value = 'cmd:grep -q "python@sha256:"'
    assert parse(f"@misc{{k, check = {{{value}}}}}")[0].fields["check"] == value


def test_empty_and_comment_only_text_has_no_entries() -> None:
    """No entries is a result, not an error."""
    assert parse("") == []
    assert parse("  % only a comment\n") == []


def test_entry_defaults_are_independent() -> None:
    """A bare Entry has no fields and line zero, and two do not share a dict."""
    one, two = Entry("t", "a"), Entry("t", "b")
    one.fields["x"] = "1"
    assert two.fields == {}
    assert (one.line, two.line) == (0, 0)

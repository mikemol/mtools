# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `gen_warrants --write`: the bib and the rubric updated together, or neither."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import gen_warrants

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

TEST_MODULE = '''"""A module."""


def test_it_does_a_thing() -> None:
    """It does a thing."""
'''
BRACE_MODULE = '''"""A module."""


def test_it_has_a_brace() -> None:
    """It names {a brace}."""
'''
TSV = "# rubric\nold\tThe Old Section\n"
JSONL = '{"key": "old", "title": "The Old Section"}\n'
REFUSED = 2


def _dist(root: Path, rubric: str | None, module: str = TEST_MODULE) -> Path:
    """Make a distribution `d` with one test module, an empty bib and an optional rubric.

    Returns:
        the distribution directory.

    """
    base = root / "d"
    (base / "tests").mkdir(parents=True)
    (base / "tests" / "test_m.py").write_text(module, encoding="utf-8")
    (base / "warrants.bib").write_text("", encoding="utf-8")
    if rubric is not None:
        name = "rubric.jsonl" if rubric.startswith("{") else "rubric.tsv"
        (base / name).write_text(rubric, encoding="utf-8")
    return base


def _read(base: Path, name: str) -> str:
    """Read one of the distribution's files.

    Returns:
        its text.

    """
    return (base / name).read_text(encoding="utf-8")


def _run(root: Path, *args: str) -> int:
    """Run the generator over `root` for the distribution `d`, module `m`.

    Returns:
        its exit code.

    """
    return gen_warrants.main(["--root", str(root), *args])


def test_write_appends_the_warrants_and_a_tab_separated_row_for_a_new_section(
    tmp_path: Path,
) -> None:
    """A new section gets a `key<TAB>title` row after the old rows, which are untouched."""
    base = _dist(tmp_path, TSV)
    assert _run(tmp_path, "--write", "--title", "fresh=A Fresh Section", "d", "m=fresh") == 0
    assert "section = {fresh}" in _read(base, "warrants.bib")
    assert _read(base, "rubric.tsv") == TSV + "fresh\tA Fresh Section\n"


def test_write_adds_a_json_object_row_to_a_jsonl_rubric(tmp_path: Path) -> None:
    """The row is written in the rubric's own format, with named fields."""
    base = _dist(tmp_path, JSONL)
    assert _run(tmp_path, "--write", "--title", "fresh=A Fresh Section", "d", "m=fresh") == 0
    rows = _read(base, "rubric.jsonl").splitlines()
    assert rows == [JSONL.strip(), '{"key": "fresh", "title": "A Fresh Section"}']


def test_a_new_section_with_no_title_refuses_before_writing_anything(tmp_path: Path) -> None:
    """Exit 2, and neither the bib nor the rubric has changed: no half-update exists."""
    base = _dist(tmp_path, TSV)
    assert _run(tmp_path, "--write", "d", "m=fresh") == REFUSED
    assert not _read(base, "warrants.bib")
    assert _read(base, "rubric.tsv") == TSV


def test_a_known_section_adds_no_row_and_needs_no_title(tmp_path: Path) -> None:
    """An existing key is left as it is; only the warrants are appended."""
    base = _dist(tmp_path, TSV)
    assert _run(tmp_path, "--write", "d", "m=old") == 0
    assert "section = {old}" in _read(base, "warrants.bib")
    assert _read(base, "rubric.tsv") == TSV


def test_a_brace_in_a_docstring_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """The could-not-transcribe code, with the rubric untouched too."""
    base = _dist(tmp_path, TSV, BRACE_MODULE)
    code = _run(tmp_path, "--write", "--title", "fresh=A Fresh Section", "d", "m=fresh")
    assert code == REFUSED
    assert not _read(base, "warrants.bib")
    assert _read(base, "rubric.tsv") == TSV


def test_the_stream_form_never_touches_the_rubric_nor_asks_for_a_title(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --write the entries go to stdout as before, whatever the section is."""
    base = _dist(tmp_path, TSV)
    assert _run(tmp_path, "d", "m=fresh") == 0
    assert "section = {fresh}" in capsys.readouterr().out
    assert _read(base, "rubric.tsv") == TSV


def test_a_title_with_a_tab_is_refused_since_a_tsv_row_cannot_carry_it(tmp_path: Path) -> None:
    """The very character that broke the rubric twice cannot be smuggled into a heading."""
    base = _dist(tmp_path, TSV)
    assert _run(tmp_path, "--write", "--title", "fresh=bad\ttitle", "d", "m=fresh") == REFUSED
    assert _read(base, "rubric.tsv") == TSV


def test_an_unterminated_last_row_is_ended_before_the_new_one_is_appended(tmp_path: Path) -> None:
    """A rubric whose last line has no newline does not fuse with the row appended after it."""
    base = _dist(tmp_path, "old\tThe Old Section")
    assert _run(tmp_path, "--write", "--title", "fresh=A Fresh Section", "d", "m=fresh") == 0
    assert _read(base, "rubric.tsv") == "old\tThe Old Section\nfresh\tA Fresh Section\n"


def test_a_distribution_with_no_rubric_gets_its_warrants_and_no_new_file(tmp_path: Path) -> None:
    """Nothing is invented: no rubric file means no rubric row and no rubric created."""
    base = _dist(tmp_path, None)
    assert _run(tmp_path, "--write", "d", "m=fresh") == 0
    assert "section = {fresh}" in _read(base, "warrants.bib")
    assert gen_warrants.rubric_file(base) is None


def test_rubric_keys_reads_both_formats_and_skips_comments(tmp_path: Path) -> None:
    """Keys come from the first tab field or the `key` member; comments and blanks name none."""
    tsv = tmp_path / "rubric.tsv"
    tsv.write_text("# c\n\nalpha\tA\nbeta\tB\n", encoding="utf-8")
    jsonl = tmp_path / "rubric.jsonl"
    jsonl.write_text('{"key": "gamma", "title": "G"}\n\n{"key": "delta", "title": "D"}\n')
    assert gen_warrants.rubric_keys(tsv) == {"alpha", "beta"}
    assert gen_warrants.rubric_keys(jsonl) == {"gamma", "delta"}

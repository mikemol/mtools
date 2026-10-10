# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A prune also drops the rubric rows it left without a warrant (W925).

⚑ Deleting a test module drops its warrants but left its section's rubric row, and the pairing gate
refuses a rubric row without a warrant: the prune left the pairing in a state the gate rejects, and
the row was removed by hand. These arms pin the rule the gate uses, in both rubric formats.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import gen_warrants

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_BIB = (
    "@misc{d-m-works,\n  section = {kept},\n  title  = {t},\n}\n"
    "@misc{d-m-also,\n  section = {kept2},\n  title  = {section = {gone}},\n}\n"
)
_TSV = "# comment\nkept\tKept heading\t\ngone\tGone heading\t\nkept2\tSecond\t\n"


def _rubric(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_a_row_without_a_warrant_is_dropped_and_the_others_keep_their_bytes(tmp_path: Path) -> None:
    """The trailing tab of a kept row survives, and the comment line is untouched."""
    path = _rubric(tmp_path, "rubric.tsv", _TSV)
    assert gen_warrants.prune_rubric(path, _BIB) == 1
    assert path.read_text(encoding="utf-8") == "# comment\nkept\tKept heading\t\nkept2\tSecond\t\n"


def test_a_section_named_inside_a_title_is_not_a_section(tmp_path: Path) -> None:
    """The control: `gone` appears in a title line only, so its row still goes."""
    path = _rubric(tmp_path, "rubric.tsv", "gone\tGone\t\n")
    assert gen_warrants.prune_rubric(path, _BIB) == 1


def test_a_rubric_with_every_section_present_is_left_alone(tmp_path: Path) -> None:
    """Nothing to drop means no rewrite."""
    text = "kept\tKept\t\nkept2\tSecond\t\n"
    path = _rubric(tmp_path, "rubric.tsv", text)
    assert gen_warrants.prune_rubric(path, _BIB) == 0
    assert path.read_text(encoding="utf-8") == text


def test_the_jsonl_rubric_is_pruned_the_same_way(tmp_path: Path) -> None:
    """Both rubric formats follow one rule."""
    rows = '{"key": "kept", "title": "A"}\n{"key": "gone", "title": "B"}\n'
    path = _rubric(tmp_path, "rubric.jsonl", rows)
    assert gen_warrants.prune_rubric(path, _BIB) == 1
    assert path.read_text(encoding="utf-8") == '{"key": "kept", "title": "A"}\n'


def test_the_prune_says_how_many_rows_it_dropped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The count reaches stderr, beside the warrants-dropped line."""
    (tmp_path / "warrants.bib").write_text(_BIB, encoding="utf-8")
    _rubric(tmp_path, "rubric.tsv", _TSV)
    gen_warrants.drop_empty_rubric_rows(tmp_path)
    assert "1 rubric rows left without a warrant dropped" in capsys.readouterr().err


def test_a_distribution_with_no_rubric_is_silent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No rubric file, nothing to prune, nothing printed."""
    (tmp_path / "warrants.bib").write_text(_BIB, encoding="utf-8")
    gen_warrants.drop_empty_rubric_rows(tmp_path)
    assert not capsys.readouterr().err

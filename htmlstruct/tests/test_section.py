# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `text FILE --section N | --heading TEXT`: one headed section's text (mtools:W1403).

⚑ THE CONTROLS ARE THE EDGES OF A SECTION: it ends at the next heading of EQUAL OR HIGHER rank (a
lower-rank sub-heading stays inside it), script text never appears, and a selector that matches
nothing is a MISS (exit 1), never an empty answer. The page is an MHTML archive like the saved
Google AI-mode pages whose headed sections carry no id. Every fixture is SYNTHETIC.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.htmlstruct import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_BODY = (
    "<h1>Page</h1><p>intro</p>"
    "<h2>AI Mode reply for scanning</h2><p>use  SANE</p><script>var hidden = 1</script>"
    "<h3>Sub step</h3><p>run scanimage</p>"
    "<h2>Another reply</h2><p>second text</p>"
)
_ARCHIVE = (
    'Content-Type: multipart/related; boundary="B"\n\n'
    "--B\nContent-Type: text/html\nContent-Location: https://x/a.html\n\n"
    f"{_BODY}\n--B--\n"
)


def _page(tmp_path: Path) -> str:
    path = tmp_path / "page.mhtml"
    path.write_text(_ARCHIVE, encoding="utf-8")
    return str(path)


def _out(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().out


def test_a_section_by_row_holds_its_subsections_and_stops_at_an_equal_rank_heading(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Row 2 is the h2: its text and its h3's, then it stops at the next h2."""
    assert cli.main(["text", _page(tmp_path), "--section", "2"]) == cli.EXIT_OK
    assert _out(capsys) == "use SANE Sub step run scanimage\n"


def test_a_section_by_heading_text_matches_exactly_then_by_prefix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The full heading and its leading words select the same section."""
    page = _page(tmp_path)
    assert cli.main(["text", page, "--heading", "AI Mode reply for scanning"]) == cli.EXIT_OK
    full = _out(capsys)
    assert cli.main(["text", page, "--heading", "AI Mode reply"]) == cli.EXIT_OK
    assert _out(capsys) == full


def test_the_last_section_runs_to_the_end_and_a_lower_rank_section_stops_at_the_next_h2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Row 4 is the last h2, to the page end; row 3, the h3, stops where the next h2 begins."""
    page = _page(tmp_path)
    assert cli.main(["text", page, "--section", "4"]) == cli.EXIT_OK
    assert _out(capsys) == "second text\n"
    assert cli.main(["text", page, "--section", "3"]) == cli.EXIT_OK
    assert _out(capsys) == "run scanimage\n"


def test_script_text_is_never_part_of_a_section(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: `var hidden = 1` sits inside the first reply and is not printed."""
    assert cli.main(["text", _page(tmp_path), "--section", "2"]) == cli.EXIT_OK
    assert "hidden" not in _out(capsys)


def test_a_row_or_heading_that_matches_nothing_is_a_miss_and_a_bad_row_is_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 for an out-of-range row or an unknown heading; exit 2 for a row that is no number."""
    page = _page(tmp_path)
    assert cli.main(["text", page, "--section", "9"]) == cli.EXIT_MISS
    assert cli.main(["text", page, "--heading", "no such heading"]) == cli.EXIT_MISS
    assert not _out(capsys)
    assert cli.main(["text", page, "--section", "two"]) == cli.EXIT_USAGE

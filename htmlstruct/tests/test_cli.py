# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the command: each verb's output, and the exit code that names each kind of nothing.

W908. ⚑ THE ANSWERED CALLS ARE THE POSITIVE CONTROL for the refusals: an exit of 2 or 3 only means
something beside a call that exits 0 with the same machinery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.htmlstruct import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_PAGE = (
    '<title>The Page</title><meta name="Description" content="About">'
    '<h1 id="top">Heading</h1><p id="p">hello <a href="/x" rel="next">link</a></p>'
    "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>"
)
_ARCHIVE = (
    'Content-Type: multipart/related; boundary="B"\n\n'
    '<h1 id="decoy">Preamble</h1>\n'
    "--B\nContent-Type: text/html\nContent-Location: https://x/a.html\n\n"
    '<h1 id="t">From archive</h1>\n'
    "--B\nContent-Type: text/plain\nContent-Location: https://x/n.txt\n\nnote\n"
    "--B--\n"
)


def _file(tmp_path: Path, name: str, body: str) -> str:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return str(path)


def _out(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().out


def test_each_html_verb_prints_one_record_per_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: every verb answers with exit 0 and tab-separated records."""
    page = _file(tmp_path, "p.html", _PAGE)
    assert cli.main(["outline", page]) == cli.EXIT_OK
    assert _out(capsys) == "1\ttop\tHeading\n"
    assert cli.main(["links", page]) == cli.EXIT_OK
    assert _out(capsys) == "/x\tnext\tlink\n"
    assert cli.main(["tables", page]) == cli.EXIT_OK
    assert _out(capsys) == "TABLE 1\n*a\t*b\n1\t2\n"
    assert cli.main(["meta", page]) == cli.EXIT_OK
    assert _out(capsys) == "title\tThe Page\ndescription\tAbout\n"
    assert cli.main(["text", page, "p"]) == cli.EXIT_OK
    assert _out(capsys) == "hello link\n"


def test_an_absent_id_is_a_miss_with_exit_one_and_no_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A valid question with no answer is not an empty success."""
    page = _file(tmp_path, "p.html", _PAGE)
    assert cli.main(["text", page, "nope"]) == cli.EXIT_MISS
    captured = capsys.readouterr()
    assert not captured.out
    assert "MISS" in captured.err


def test_usage_errors_exit_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown verb, a wrong operand count and a missing file are refusals, not empty answers."""
    page = _file(tmp_path, "p.html", _PAGE)
    for argv in (
        [],
        ["frobnicate", page],
        ["outline"],
        ["outline", page, "extra"],
        ["text", page],
        ["outline", str(tmp_path / "missing.html")],
    ):
        assert cli.main(argv) == cli.EXIT_USAGE
        assert not _out(capsys)


def test_an_archive_answers_the_html_verbs_through_its_root_and_lists_its_parts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An .mhtml file is read through its first part; `parts` lists what is in it."""
    archive = _file(tmp_path, "a.mhtml", _ARCHIVE)
    assert cli.main(["outline", archive]) == cli.EXIT_OK
    assert _out(capsys) == "1\tt\tFrom archive\n"
    assert cli.main(["parts", archive]) == cli.EXIT_OK
    assert _out(capsys) == "https://x/a.html\ttext/html\t28\nhttps://x/n.txt\ttext/plain\t4\n"


def test_a_part_is_written_as_raw_bytes_and_an_unknown_one_is_a_miss(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """`part` writes the decoded payload to standard output; a bad location exits 1."""
    archive = _file(tmp_path, "a.mht", _ARCHIVE)
    assert cli.main(["part", archive, "https://x/n.txt"]) == cli.EXIT_OK
    assert capfd.readouterr().out == "note"
    assert cli.main(["part", archive, "https://x/none"]) == cli.EXIT_MISS
    assert not capfd.readouterr().out


def test_input_that_is_not_a_document_is_a_skip_with_exit_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bytes that are not text, and a non-archive given to `parts`, are skips."""
    binary = tmp_path / "b.html"
    binary.write_bytes(b"\xff\xfe\x00bad")
    assert cli.main(["outline", str(binary)]) == cli.EXIT_SKIP
    assert "SKIP" in capsys.readouterr().err
    page = _file(tmp_path, "p.html", _PAGE)
    assert cli.main(["parts", page]) == cli.EXIT_SKIP
    assert "SKIP" in capsys.readouterr().err

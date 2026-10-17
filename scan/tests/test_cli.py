# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the command: the four steps in order, and a failure that names its step (W1425).

⚑ NO SCANNER, NO PROGRAM: one `Run` plants pages for `scanimage` (a different count per pass) and
records the converters' argvs; the operator wait is a recorder. The controls are the three ways the
sequence goes wrong: the backs scanned before the wait, unequal passes quietly becoming a PDF, and a
failed first pass still asking the operator to flip.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.scan import adf, cli

if TYPE_CHECKING:
    from collections.abc import Sequence

_FAILED = 1
_USAGE = 2
_TWO = 2
_DPI = 150


def _machine(counts: Sequence[int], code: int = 0) -> tuple[adf.Run, list[list[str]]]:
    # Plants counts[n] pages on the n-th scanimage call; img2pdf and ocrmypdf are only recorded.
    asked: list[list[str]] = []
    passes: list[int] = []

    def run(argv: Sequence[str]) -> tuple[int, str]:
        asked.append(list(argv))
        if argv[0] != "scanimage":
            return 0, ""
        batch = next(a for a in argv if a.startswith("--batch="))
        folder = Path(batch.removeprefix("--batch=")).parent
        for number in range(1, counts[len(passes)] + 1):
            (folder / f"page-{number:03d}.tif").write_text("x", encoding="utf-8")
        passes.append(1)
        return code, "scanner said this"

    return run, asked


def _wait(heard: list[str]) -> cli.Wait:
    def wait(message: str) -> None:
        heard.append(message)

    return wait


def _argv(tmp_path: Path) -> list[str]:
    return ["dev", str(tmp_path / "doc.pdf"), "--work", str(tmp_path / "w")]


def test_fronts_then_the_wait_then_backs_then_the_pdf_in_page_order(tmp_path: Path) -> None:
    """f1 b1 f2 b2: the backs reversed, the wait between the passes, then join and OCR."""
    run, asked = _machine((_TWO, _TWO))
    heard: list[str] = []
    assert cli.main(_argv(tmp_path), run, _wait(heard)) == cli.EXIT_OK
    assert heard == [cli.FLIP]
    assert [a[0] for a in asked] == ["scanimage", "scanimage", "img2pdf", "ocrmypdf"]
    joined = [f"{Path(p).parent.name}/{Path(p).name}" for p in asked[2][1:5]]
    assert joined == [
        "front/page-001.tif",
        "back/page-002.tif",
        "front/page-002.tif",
        "back/page-001.tif",
    ]
    assert asked[3][-1] == str(tmp_path / "doc.pdf")


def test_unequal_passes_are_refused_and_nothing_is_joined(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: 2 fronts and 1 back exit 1 naming both counts and the kept pages, no PDF."""
    run, asked = _machine((_TWO, 1))
    assert cli.main(_argv(tmp_path), run, _wait([])) == cli.EXIT_FAILED
    err = capsys.readouterr().err
    assert "2 front(s) but 1 back(s)" in err
    assert f"pages kept in {tmp_path / 'w'}" in err
    assert [a[0] for a in asked] == ["scanimage", "scanimage"]


def test_a_failed_first_pass_never_asks_the_operator_to_flip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A scanner exit 1 on the fronts gives exit 1 with its words, and the wait is not called."""
    run, _ = _machine((_TWO, _TWO), code=_FAILED)
    heard: list[str] = []
    assert cli.main(_argv(tmp_path), run, _wait(heard)) == cli.EXIT_FAILED
    assert not heard
    assert "scanner said this" in capsys.readouterr().err


def test_bad_arguments_are_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """One positional, an unknown flag, a valueless flag and a bad resolution all exit 2."""
    run, asked = _machine((1, 1))
    bad_lines = (
        ["dev"],
        ["a", "b", "--nope", "1"],
        ["a", "b", "--mode"],
        ["a", "b", "--resolution", "x"],
    )
    for bad in bad_lines:
        assert cli.main(bad, run, _wait([])) == _USAGE
    assert cli.USAGE in capsys.readouterr().err
    assert not asked


def test_the_operator_wait_prints_the_instruction_and_reads_one_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The real wait writes its message to stderr and consumes exactly one line of stdin."""
    stdin = io.StringIO("\nsecond line\n")
    monkeypatch.setattr("sys.stdin", stdin)
    cli.wait_on_operator(cli.FLIP)
    assert cli.FLIP in capsys.readouterr().err
    assert stdin.readline() == "second line\n"


def test_the_console_entry_exits_with_the_commands_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no arguments the entry reaches `main` and exits 2, starting no scanner."""
    monkeypatch.setattr("sys.argv", ["mikemol-scan"])
    with pytest.raises(SystemExit) as exited:
        cli.entry()
    assert exited.value.code == _USAGE


def test_options_reach_the_scan_settings(tmp_path: Path) -> None:
    """The positive control for parsing: resolution and mode come through, source keeps ADF."""
    words = ["dev", "o.pdf", "--resolution", str(_DPI), "--mode", "Color", "--work", str(tmp_path)]
    job = cli.parse(words)
    assert job is not None
    assert (job.settings.resolution, job.settings.mode) == (_DPI, "Color")
    assert job.settings.source == "ADF"
    assert job.work == tmp_path

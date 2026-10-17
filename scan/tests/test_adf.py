# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for one ADF pass: the command asked for, and what is accepted back (W1423).

⚑ NO SCANNER, NO SUBPROCESS: `Run` is replaced by a function that plants page files the way
scanimage would and returns an exit code. The controls are the refusals: a directory already holding
pages (a second pass mixed into the first), a nonzero exit, and an exit 0 that wrote nothing, each
raised with the tool's words. Exit 7 (feeder out of documents) with pages written is accepted, and
exit 7 with none is not.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.scan import adf

if TYPE_CHECKING:
    from collections.abc import Sequence

_FAILED = 1
_THREE = 3
_EXIT = 3


def _scanner(count: int, code: int = 0, said: str = "") -> adf.Run:
    # A stand-in for scanimage: plants `count` pages in the --batch directory, then exits `code`.
    def run(argv: Sequence[str]) -> tuple[int, str]:
        batch = next(a for a in argv if a.startswith("--batch="))
        folder = batch.removeprefix("--batch=").rsplit("/", 1)[0]
        for number in range(1, count + 1):
            (Path(folder) / f"page-{number:03d}.tif").write_text("x", encoding="utf-8")
        return code, said

    return run


def test_the_command_names_the_device_source_resolution_mode_and_batch_pattern(
    tmp_path: Path,
) -> None:
    """Every part is its own argv word; the batch pattern lives in the pass's own directory."""
    argv = adf.command("escl:http://scanner", tmp_path, adf.Settings())
    assert argv[:4] == ["scanimage", "-d", "escl:http://scanner", "--source"]
    assert argv[argv.index("--resolution") + 1] == "300"
    assert argv[argv.index("--mode") + 1] == "Gray"
    assert f"--batch={tmp_path / adf.PATTERN}" in argv


def test_a_pass_returns_its_pages_in_feed_order(tmp_path: Path) -> None:
    """Three pages planted: they come back as page-001 to page-003, sorted."""
    got = adf.run_pass("dev", tmp_path / "fronts", _scanner(_THREE))
    assert [p.name for p in got] == ["page-001.tif", "page-002.tif", "page-003.tif"]


def test_exit_seven_with_pages_is_the_feeder_running_out_and_is_accepted(tmp_path: Path) -> None:
    """The end of a batch: scanimage's out-of-documents status is not a failure when pages exist."""
    got = adf.run_pass("dev", tmp_path / "p", _scanner(2, adf.ENDED_EMPTY, "out of documents"))
    assert len(got) == _THREE - 1


def test_a_failed_exit_and_an_empty_pass_are_refused_with_the_tools_words(tmp_path: Path) -> None:
    """The control: exit 1 raises; exit 0 with no page raises; exit 7 with no page raises."""
    with pytest.raises(adf.ScanError, match=r"exit 1.*device busy"):
        adf.run_pass("dev", tmp_path / "a", _scanner(2, _FAILED, "device busy"))
    with pytest.raises(adf.ScanError, match="0 page"):
        adf.run_pass("dev", tmp_path / "b", _scanner(0))
    with pytest.raises(adf.ScanError, match="0 page"):
        adf.run_pass("dev", tmp_path / "c", _scanner(0, adf.ENDED_EMPTY))


def test_the_real_runner_returns_a_childs_exit_code_and_its_stderr() -> None:
    """The one function that starts a process, exercised on a child that is not a scanner."""
    program = "import sys; sys.stderr.write('feeder jam'); sys.exit(3)"
    assert adf.run_command([sys.executable, "-c", program]) == (_EXIT, "feeder jam")


def test_a_directory_already_holding_pages_is_refused_before_scanning(tmp_path: Path) -> None:
    """The control: a second pass into the first's directory never runs scanimage."""
    asked: list[object] = []

    def run(argv: Sequence[str]) -> tuple[int, str]:
        asked.append(argv)
        return 0, ""

    folder = tmp_path / "mixed"
    folder.mkdir()
    (folder / "page-001.tif").write_text("x", encoding="utf-8")
    with pytest.raises(adf.ScanError, match="already holds"):
        adf.run_pass("dev", folder, run)
    assert not asked

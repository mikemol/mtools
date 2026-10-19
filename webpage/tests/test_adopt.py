# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The adopt mode moves waits onto webpage.until and watches the page first (nemik:W715, W1684)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.webpage import waits

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

SOURCE = (
    "import webpage\n"
    "\n"
    "\n"
    "def run(page, url):\n"
    "    page.goto(url)\n"
    "    page.wait_for_function(READY, timeout=0)\n"
)
WANT = (
    "import webpage\n"
    "\n"
    "\n"
    "def run(page, url):\n"
    "    webpage.watch(page)\n"
    "    page.goto(url)\n"
    "    webpage.until(page, READY)\n"
)


def test_a_wait_becomes_until_and_the_page_is_watched_first() -> None:
    """The wait is rewritten and a watch line goes above the goto, at its indent."""
    assert waits.adopt(SOURCE) == WANT


def test_a_second_run_changes_nothing() -> None:
    """Once adopted there is nothing left to rewrite."""
    assert waits.adopt(WANT) == WANT


def test_a_file_that_does_not_import_webpage_is_left_alone() -> None:
    """Without the helper to call, the file is not touched."""
    source = SOURCE.replace("import webpage\n", "import os\n")
    assert waits.adopt(source) == source


def test_a_wait_with_other_arguments_is_left_alone() -> None:
    """A call that is not (expr, timeout=0) has no safe rewrite, so it stays as written."""
    source = SOURCE.replace("READY, timeout=0", "READY, arg=1, timeout=0")
    assert "webpage.until" not in waits.adopt(source)
    assert "webpage.watch" not in waits.adopt(source)


def test_the_adopt_flag_writes_through_main(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--adopt --write turns a file's waits into webpage.until and says how many files changed."""
    target = tmp_path / "test_x.py"
    target.write_text(SOURCE, encoding="utf-8")
    assert waits.main(["--adopt", "--write", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == WANT
    assert "1 file(s) rewritten" in capsys.readouterr().out

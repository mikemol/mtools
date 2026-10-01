# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the header mode: the four shared behaviours and each settled difference (W306)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import cli
from mikemol.pycodemod.header import COMPLETE, MISSING, PARTIAL, WRONG, plan

if TYPE_CHECKING:
    from pathlib import Path

_SPDX = "# SPDX-License-Identifier: Apache-2.0\n"
_COPY = "# Copyright (c) 2026 Mike Mol\n"
_SHEBANG = "#!/usr/bin/env python3\n"
_CODING = "# -*- coding: latin-1 -*-\n"
_DOC = '"""doc."""\nx = 1\n'


def _new(text: str, holder: str | None = "Mike Mol") -> str:
    """Plan one file's header the house way.

    Returns:
        the text the file should become.

    """
    return plan(text, spdx="Apache-2.0", holder=holder, year=2026).text


def test_a_shebang_stays_first_and_the_docstring_stays_the_modules() -> None:
    """Shared (A): the header goes after the shebang, above the docstring, which is untouched."""
    assert _new(_SHEBANG + _DOC) == _SHEBANG + _SPDX + _COPY + _DOC


def test_a_complete_header_is_left_byte_identical() -> None:
    """Shared (A): idempotent, so writing twice is a no-op."""
    once = _new(_DOC)
    result = plan(once, spdx="Apache-2.0", holder="Mike Mol", year=2027)
    assert (result.state, result.text) == (COMPLETE, once)


def test_an_empty_file_gets_the_header() -> None:
    """Shared (A): an empty module gains the two lines."""
    assert _new("") == _SPDX + _COPY


@pytest.mark.parametrize("prelude", [_CODING, _SHEBANG + _CODING])
def test_a_pep_263_coding_line_stays_on_line_one_or_two(prelude: str) -> None:
    """⚑ The header goes AFTER a coding line: Python reads one only on line 1 or 2 (rule 2)."""
    assert _new(prelude + _DOC) == prelude + _SPDX + _COPY + _DOC


def test_a_comment_that_mentions_coding_below_line_two_is_not_a_coding_line() -> None:
    """PEP 263's pattern on lines 1-2 only: a later 'coding:' comment does not move the header."""
    text = "# first\n# second\n# coding: utf-8\n" + _DOC
    assert _new(text).startswith(_SPDX)


@pytest.mark.parametrize(
    ("text", "want", "detail"),
    [
        (_SPDX + _DOC, _SPDX + _COPY + _DOC, "adds the copyright line"),
        (_SHEBANG + _COPY + _DOC, _SHEBANG + _SPDX + _COPY + _DOC, "adds the SPDX line"),
    ],
)
def test_a_partial_header_is_completed_in_place(text: str, want: str, detail: str) -> None:
    """⚑ One line present: the other goes beside it, not refused (rule 3; el-openglo's 152)."""
    result = plan(text, spdx="Apache-2.0", holder="Mike Mol", year=2026)
    assert (result.state, result.detail, result.text) == (PARTIAL, detail, want)


def test_without_a_holder_an_spdx_line_alone_is_complete() -> None:
    """No --holder: the header is SPDX only, el-openglo's current form (rule 1)."""
    assert plan(_SPDX + _DOC, spdx="Apache-2.0", holder=None, year=2026).state == COMPLETE
    assert _new(_DOC, holder=None) == _SPDX + _DOC


def test_a_wrong_id_is_reported_and_never_rewritten() -> None:
    """⚑ Relicensing is a decision, not a codemod: a wrong id leaves the text alone (rule 4)."""
    text = "# SPDX-License-Identifier: GPL-3.0\n" + _DOC
    result = plan(text, spdx="Apache-2.0", holder="Mike Mol", year=2026)
    assert (result.state, result.detail, result.text) == (
        WRONG,
        "declares GPL-3.0, not Apache-2.0",
        text,
    )


def test_crlf_files_keep_crlf() -> None:
    """The inserted lines use the file's own line ending."""
    assert (
        _new("x = 1\r\n")
        == "# SPDX-License-Identifier: Apache-2.0\r\n# Copyright (c) 2026 Mike Mol\r\nx = 1\r\n"
    )


def test_write_completes_files_refuses_a_wrong_id_and_names_the_shebangs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--write fixes missing and partial, refuses a wrong id (exit 1), lists shebangs (rule 7)."""
    script, wrong = tmp_path / "script.py", tmp_path / "wrong.py"
    script.write_text(_SHEBANG + _DOC, encoding="utf-8")
    wrong.write_text("# SPDX-License-Identifier: MIT\n" + _DOC, encoding="utf-8")
    argv = ["header", "--spdx", "Apache-2.0", "--holder", "Mike Mol", "--year", "2026"]
    assert cli.main([*argv, "--write", str(script), str(wrong)]) == 1
    out = capsys.readouterr().out
    assert f"shebang\t{script}" in out
    assert f"wrong\t{wrong}\tdeclares MIT, not Apache-2.0" in out
    assert script.read_text(encoding="utf-8") == _SHEBANG + _SPDX + _COPY + _DOC
    assert cli.main([*argv, str(script)]) == 0


def test_check_reports_a_missing_header_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --write nothing is written, and a missing header is a finding (exit 1)."""
    bare = tmp_path / "bare.py"
    bare.write_text(_DOC, encoding="utf-8")
    assert cli.main(["header", "--spdx", "Apache-2.0", "--year", "2026", str(bare)]) == 1
    assert capsys.readouterr().out == f"{MISSING}\t{bare}\tadds the SPDX line\n"
    assert bare.read_text(encoding="utf-8") == _DOC

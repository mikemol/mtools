# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `lint_bzl`: a .bzl shell string must invoke tools, not embed logic or JSON."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.gatecheck import lint_bzl

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_BARE_SCRIPT = '    cmd = "python3 tools/eval.py --x",'
_BARE_DASH_C = "    cmd = \"python3 -c 'print(1)'\","
_SANCTIONED = '    cmd = "$(command -v python3) tools/eval.py --x",'
_PRINTF_JSON = '    cmd = "printf \'{\\"verb\\": 1}\' > $@",'
_GREP_JSON = '    cmd = "grep \\"verdict\\": $<",'
_CLEAN = '    cmd = "export X=1 && [ -f $< ]",'


def _bzl(tmp_path: Path, *lines: str, name: str = "x.bzl") -> str:
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _names(path: str) -> list[tuple[int, str]]:
    return [(n, name) for _p, n, name, _text in lint_bzl.findings([path])]


def test_a_bare_python3_script_or_dash_c_is_found_with_its_line_number(tmp_path: Path) -> None:
    """`python3 <script>.py` and `python3 -c` are bare invocations, reported by 1-based line."""
    path = _bzl(tmp_path, _CLEAN, _BARE_SCRIPT, _BARE_DASH_C)
    assert _names(path) == [(2, "bare-python3"), (3, "bare-python3")]


def test_the_command_v_resolution_is_not_flagged(tmp_path: Path) -> None:
    """`python3` followed by `)` is the sanctioned form."""
    assert _names(_bzl(tmp_path, _SANCTIONED)) == []


def test_printf_building_json_is_found(tmp_path: Path) -> None:
    """A JSON record built with printf is the data-construction-in-shell defect."""
    assert _names(_bzl(tmp_path, _PRINTF_JSON)) == [(1, "printf-json")]


def test_grep_reading_a_json_field_is_found(tmp_path: Path) -> None:
    """A grep for a quoted JSON field name followed by a colon is fragile and is refused."""
    assert _names(_bzl(tmp_path, _GREP_JSON)) == [(1, "grep-json")]


def test_a_finding_carries_the_path_and_the_stripped_line(tmp_path: Path) -> None:
    """The record is `(path, line, pattern, stripped text)`."""
    path = _bzl(tmp_path, _CLEAN, _BARE_SCRIPT)
    assert lint_bzl.findings([path]) == [(path, 2, "bare-python3", _BARE_SCRIPT.strip())]


def test_several_files_are_scanned_in_argument_order(tmp_path: Path) -> None:
    """Findings come back file by file, in the order the paths were given."""
    first = _bzl(tmp_path, _CLEAN, _GREP_JSON, name="a.bzl")
    second = _bzl(tmp_path, _BARE_SCRIPT, name="b.bzl")
    got = [(p, n, name) for p, n, name, _t in lint_bzl.findings([second, first])]
    assert got == [(second, 1, "bare-python3"), (first, 2, "grep-json")]


def test_a_clean_file_exits_zero_and_says_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No pattern: exit 0, no output."""
    assert lint_bzl.main([_bzl(tmp_path, _CLEAN, _SANCTIONED)]) == 0
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


def test_a_dirty_file_exits_one_and_names_each_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each finding is `path:line: Ξ·lint [name] text`, then a count and the remedy."""
    path = _bzl(tmp_path, _BARE_SCRIPT, _PRINTF_JSON)
    assert lint_bzl.main([path]) == 1
    err = capsys.readouterr().err
    assert f"{path}:1: Ξ·lint [bare-python3] {_BARE_SCRIPT.strip()}\n" in err
    assert f"{path}:2: Ξ·lint [printf-json] " in err
    assert "Ξ·lint: 2 forbidden pattern(s)" in err
    assert "resolve python via `command -v`" in err


def test_main_reads_the_process_argv_when_given_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no argument the files come from `sys.argv[1:]`, as a console script runs."""
    monkeypatch.setattr(sys, "argv", ["mikemol-lint-bzl", _bzl(tmp_path, _BARE_SCRIPT)])
    assert lint_bzl.main() == 1

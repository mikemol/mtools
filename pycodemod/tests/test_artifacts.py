# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for artifact readers: verdict by vocabulary, prefix subtracted, prose excluded."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import artifacts as art

if TYPE_CHECKING:
    from pathlib import Path

_FAIL = (".agdai.log", "isolate_check", "error:")
_SUCC = (".agdai", ".agda-times.tsv", "maxrss")


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _rows(tmp_path: Path, text: str) -> list[tuple[tuple[str, ...], str]]:
    got = art.artifact_readers([_write(tmp_path, "m.py", text)], _FAIL, _SUCC)
    return [(r.artifacts, r.bearing) for r in got.rows]


def test_a_failure_artifact_read_is_failure(tmp_path: Path) -> None:
    """A file reading `.agdai.log` is FAILURE."""
    assert _rows(tmp_path, 'p = "x.agdai.log"\n') == [((".agdai.log",), "FAILURE")]


def test_a_core_read_is_success_not_failure(tmp_path: Path) -> None:
    """⚑⚑ `.agdai` is a prefix of `.agdai.log`; reading cores alone is SUCCESS."""
    assert _rows(tmp_path, 'p = "x.agdai"\n') == [((".agdai",), "SUCCESS")]


def test_a_failure_literal_is_subtracted_from_the_success_pass(tmp_path: Path) -> None:
    """⚑⚑ The `.agdai.log` literal contains `.agdai` but must not make the file BOTH."""
    assert _rows(tmp_path, 'p = "x.agdai.log"\n')[0][1] == "FAILURE"


def test_a_timings_read_is_success(tmp_path: Path) -> None:
    """A file reading `.agda-times.tsv` is SUCCESS."""
    assert _rows(tmp_path, 'p = "a.agda-times.tsv"\n') == [((".agda-times.tsv",), "SUCCESS")]


def test_reading_both_is_both_in_fail_then_succ_order(tmp_path: Path) -> None:
    """A file reading both names both artifacts, failure ones first."""
    text = 'a = "maxrss"\nb = "x.agdai.log"\n'
    assert _rows(tmp_path, text) == [((".agdai.log", "maxrss"), "BOTH")]


def test_a_file_reading_nothing_has_no_row(tmp_path: Path) -> None:
    """There is no third verdict: no artifact, no row."""
    assert _rows(tmp_path, 'p = "unrelated"\n') == []


def test_prose_is_not_a_read(tmp_path: Path) -> None:
    """⚑⚑ A docstring, a comment and a long or multi-line literal are not reads."""
    long = "z" * art.MAX_LITERAL + ".agdai.log"
    text = f'"""Reads .agdai.log."""\n# .agdai.log\nx = "{long}"\ny = "a\\n.agdai.log"\n'
    assert _rows(tmp_path, text) == []


def test_matching_is_exact_on_both_sides(tmp_path: Path) -> None:
    """⚑ The origin folded case for success only; both sides are exact here."""
    assert _rows(tmp_path, 'a = "X.AGDAI"\nb = "X.AGDAI.LOG"\n') == []


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe not utf-8", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑⚑ An unreadable or unparseable file is a Skip with its reason, never silently dropped."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = art.artifact_readers([str(path)], _FAIL, _SUCC)
    whys: list[str] = [s.why for s in got.skipped]
    assert (len(got.rows), whys) == (0, [why])


@pytest.mark.parametrize(
    ("failure", "success"),
    [((), _SUCC), (_FAIL, ()), ((), ())],
)
def test_an_empty_vocabulary_is_refused(
    tmp_path: Path, failure: tuple[str, ...], success: tuple[str, ...]
) -> None:
    """⚑ An empty vocabulary measures nothing and must not read as a clean census."""
    with pytest.raises(ValueError, match="non-empty"):
        art.artifact_readers([_write(tmp_path, "m.py", "x = 1\n")], failure, success)

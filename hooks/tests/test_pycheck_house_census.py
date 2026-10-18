# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The census can be asked to judge by the house mypy flags, and only the census (W1538)."""

from pathlib import Path

import pytest

from mikemol.hooks import pycheck, pycheck_census, pycheck_cli, pycheck_house
from mikemol.hooks.verdict import Verdict


def _nothing_tracked(root: Path) -> list[str]:
    del root
    return []


def test_without_the_flag_the_census_judges_by_the_gates_own_verdict() -> None:
    """The default is unchanged: the very function the edit gate runs."""
    assert pycheck_cli.analyzer(house=False) is pycheck.analyze


def test_with_the_flag_the_house_mypy_flags_reach_the_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wrapper hands `analyze` exactly the house flag set, whatever file it is given."""
    seen: list[tuple[str, ...]] = []

    def fake(content: str, path: str, *, mypy_flags: tuple[str, ...] = ()) -> Verdict:
        del content, path
        seen.append(tuple(mypy_flags))
        return True, ""

    monkeypatch.setattr(pycheck, "analyze", fake)
    assert pycheck_cli.analyzer(house=True)("x = 1\n", "a.py") == (True, "")
    assert seen == [pycheck_house.mypy_flags()]


def test_census_house_reads_the_tracked_files_and_prints_the_ledger(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """`--census ROOT --house` is accepted and ends in the same JSON ledger as `--census ROOT`."""
    monkeypatch.setattr(pycheck_census, "tracked_python", _nothing_tracked)
    assert pycheck_cli.main([pycheck_cli.CENSUS_FLAG, str(tmp_path), pycheck_cli.HOUSE_FLAG]) == 0
    assert capsys.readouterr().out.strip() == "{}"


def test_the_flag_belongs_to_the_census_alone(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The ledger the closure reads is the gate's verdict, so refresh and check refuse the flag."""
    for first in (pycheck_cli.REFRESH_FLAG, pycheck_cli.FLAG, pycheck_cli.CHANGED_FLAG):
        code = pycheck_cli.main([first, str(tmp_path), pycheck_cli.HOUSE_FLAG])
        assert code == pycheck_cli.EXIT_USAGE
    assert "--house" in capsys.readouterr().err

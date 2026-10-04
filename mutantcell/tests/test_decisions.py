# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `decisions`: reached-but-unasserted decisions, from single-site grid cells."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, cast

from mikemol.mutantcell import decisions

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_FILE = "m.py"


def _cell(site: str, *, flipped: bool) -> decisions.Record:
    """Build one cell record `{site, flipped}`.

    Returns:
        The record.

    """
    return {"site": f"{_FILE}::{site}", "flipped": flipped}


def _written(tmp_path: Path, name: str, record: decisions.Record) -> str:
    """Write one record as JSON.

    Returns:
        The path.

    """
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return str(path)


def _printed(capsys: pytest.CaptureFixture[str]) -> str:
    """Read what `main` printed.

    Returns:
        Stdout, whole.

    """
    return capsys.readouterr().out


def test_an_unflipped_condition_with_both_arms_reached_is_an_unasserted_decision() -> None:
    """Both `branch` arms run and inverting the condition flips nothing: indifferent."""
    flips = [_cell("flip:f#1", flipped=False)]
    reach = [_cell("branch:f#1", flipped=True), _cell("branch:f#2", flipped=True)]
    assert decisions.decisions_unasserted(flips, reach) == [f"{_FILE}::flip:f#1"]


def test_a_condition_the_check_asserts_on_is_not_a_gap() -> None:
    """When the inversion flips the check, the check asserts on that decision."""
    flips = [_cell("flip:f#1", flipped=True)]
    reach = [_cell("branch:f#1", flipped=True), _cell("branch:f#2", flipped=True)]
    assert decisions.decisions_unasserted(flips, reach) == []


def test_a_condition_with_only_one_arm_reached_is_not_reported() -> None:
    """One unreached arm (or only one arm known) rules out the one-path-fixture false positive."""
    flips = [_cell("flip:f#1", flipped=False)]
    unreached = [_cell("branch:f#1", flipped=True), _cell("branch:f#2", flipped=False)]
    single = [_cell("branch:f#1", flipped=True)]
    assert decisions.decisions_unasserted(flips, unreached) == []
    assert decisions.decisions_unasserted(flips, single) == []


def test_arms_of_another_function_do_not_vouch_for_a_condition() -> None:
    """The reach index is keyed by file, kind and qualname: a sibling's arms are not ours."""
    flips = [_cell("flip:f#1", flipped=False)]
    reach = [_cell("branch:g#1", flipped=True), _cell("branch:g#2", flipped=True)]
    assert decisions.decisions_unasserted(flips, reach) == []


def test_an_unperturbed_data_value_whose_key_is_read_is_unasserted() -> None:
    """The `data-` drop of the same (QN, n) is reached, yet the value perturb flips nothing."""
    flips = [_cell("dflip:TABLE#3", flipped=False)]
    reach = [_cell("data-:TABLE#3", flipped=True)]
    assert decisions.decisions_unasserted(flips, reach) == [f"{_FILE}::dflip:TABLE#3"]


def test_a_data_value_is_not_reported_when_its_key_is_unread() -> None:
    """A drop that is not reached, or reached at another index, leaves the value unjudged."""
    flips = [_cell("dflip:TABLE#3", flipped=False)]
    unread = [_cell("data-:TABLE#3", flipped=False)]
    other_index = [_cell("data-:TABLE#4", flipped=True)]
    assert decisions.decisions_unasserted(flips, unread) == []
    assert decisions.decisions_unasserted(flips, other_index) == []


def test_a_data_value_the_check_asserts_on_is_not_a_gap() -> None:
    """When the perturb flips the check, the value is asserted, however the key is read."""
    flips = [_cell("dflip:TABLE#3", flipped=True)]
    reach = [_cell("data-:TABLE#3", flipped=True)]
    assert decisions.decisions_unasserted(flips, reach) == []


def test_a_site_without_a_numeric_index_matches_no_sibling() -> None:
    """`#x` is not an index: the dflip has no sibling, so nothing is reported."""
    flips = [_cell("dflip:TABLE#x", flipped=False)]
    reach = [_cell("data-:TABLE#1", flipped=True)]
    assert decisions.decisions_unasserted(flips, reach) == []


def test_a_cell_of_an_unrelated_kind_is_never_reported() -> None:
    """Only `flip` and `dflip` cells can be unasserted decisions."""
    flips = [_cell("branch:f#1", flipped=False)]
    reach = [_cell("branch:f#1", flipped=True), _cell("branch:f#2", flipped=True)]
    assert decisions.decisions_unasserted(flips, reach) == []


def test_the_unasserted_labels_come_back_sorted() -> None:
    """Input order does not leak: the result is the sorted labels."""
    arms = [_cell("branch:f#1", flipped=True), _cell("branch:f#2", flipped=True)]
    arms_g = [_cell("branch:g#1", flipped=True), _cell("branch:g#2", flipped=True)]
    flips = [_cell("flip:g#1", flipped=False), _cell("flip:f#1", flipped=False)]
    got = decisions.decisions_unasserted(flips, [*arms, *arms_g])
    assert got == [f"{_FILE}::flip:f#1", f"{_FILE}::flip:g#1"]


def test_summarize_unions_dedupes_and_counts_without_failing_on_a_nonzero_count() -> None:
    """The union of every claim's labels, sorted and counted; `pass` means well-formed."""
    records: list[decisions.Record] = [
        {"decisions_unasserted": ["b", "a"]},
        {"decisions_unasserted": ["b", "c"]},
        {},
    ]
    assert decisions.summarize(records) == {
        "verdict": "pass",
        "decisions_unasserted": ["a", "b", "c"],
        "count": 3,
    }


def test_main_with_flips_and_reach_prints_the_unasserted_labels(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The record files are read and the labels printed as one JSON object."""
    flip = _written(tmp_path, "flip", _cell("flip:f#1", flipped=False))
    arm1 = _written(tmp_path, "a1", _cell("branch:f#1", flipped=True))
    arm2 = _written(tmp_path, "a2", _cell("branch:f#2", flipped=True))
    argv = ["--flips", flip, "--reach", arm1, arm2]
    assert decisions.main(argv) == 0
    assert _printed(capsys) == '{"decisions_unasserted": ["m.py::flip:f#1"]}\n'


def test_main_with_no_operands_prints_an_empty_list(capsys: pytest.CaptureFixture[str]) -> None:
    """Neither flag given: nothing to judge, said as an empty list."""
    assert decisions.main([]) == 0
    assert _printed(capsys) == '{"decisions_unasserted": []}\n'


def test_main_summary_prints_compact_json_the_grep_can_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--summary` prints with no spaces, so `"verdict":"pass"` matches byte for byte."""
    one = _written(tmp_path, "one", {"decisions_unasserted": ["x"]})
    two = _written(tmp_path, "two", {"decisions_unasserted": ["x", "y"]})
    assert decisions.main(["--summary", one, two]) == 0
    printed = _printed(capsys)
    assert printed == '{"verdict":"pass","decisions_unasserted":["x","y"],"count":2}\n'


def test_main_summary_with_no_records_is_an_empty_pass(capsys: pytest.CaptureFixture[str]) -> None:
    """A bare `--summary` folds zero records: a pass with count 0."""
    assert decisions.main(["--summary"]) == 0
    assert _printed(capsys) == '{"verdict":"pass","decisions_unasserted":[],"count":0}\n'


def test_main_reads_sys_argv_when_given_no_argument(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The `-m` path: `main()` takes its operands from `sys.argv[1:]`."""
    monkeypatch.setattr(sys, "argv", ["decisions", "--summary"])
    assert decisions.main() == 0
    got = cast("dict[str, object]", json.loads(_printed(capsys)))
    assert got["count"] == 0

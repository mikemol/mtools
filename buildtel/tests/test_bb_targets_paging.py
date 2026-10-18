# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bb_targets` paging: every group is followed, a part is no maximum (W1566)."""

from __future__ import annotations

import json
from typing import cast

import pytest

from mikemol.buildtel import bb_targets

_TOTAL = 4
_BUILT_TOTAL = 1324
_NEXT = "t2"


def _test(label: str, millis: str) -> dict[str, object]:
    return {
        "metadata": {"label": label},
        "status": "PASSED",
        "testSummary": {"totalRunDurationMillis": millis},
    }


def _first() -> dict[str, object]:
    # One target of four, with the key to the rest, as GetInvocation answers a paged group.
    return {
        "status": "PASSED",
        "targets": [_test("//a:one", "1")],
        "totalCount": str(_TOTAL),
        "nextPageToken": _NEXT,
    }


def _page(*groups: dict[str, object]) -> dict[str, object]:
    return {"invocation": [{"targetGroups": list(groups)}]}


def _paged(more: str, *targets: dict[str, object]) -> dict[str, object]:
    # The answer GetTarget gives for one page of a group: that group alone, with the next key.
    group: dict[str, object] = {"status": "PASSED", "targets": list(targets)}
    if more:
        group["nextPageToken"] = more
    return {"targetGroups": [group]}


def test_every_page_of_a_group_is_followed_with_the_groups_own_status_and_token() -> None:
    """Page one holds one target of four; the next two pages hold the rest: the report is whole."""
    answers = {
        _NEXT: _paged("t3", _test("//a:two", "2"), _test("//a:three", "3")),
        "t3": _paged("", _test("//a:four", "4")),
    }
    asked: list[tuple[str, str, str]] = []

    def more(invocation: str, status: str, token: str) -> object:
        asked.append((invocation, status, token))
        return answers[token]

    report = bb_targets.parse(_page(_first()), more, "inv")
    assert asked == [("inv", "PASSED", _NEXT), ("inv", "PASSED", "t3")]
    assert (report.listed, report.total, report.complete()) == (_TOTAL, _TOTAL, True)
    assert [t.label for t in report.tests] == ["//a:four", "//a:three", "//a:two", "//a:one"]


def test_a_token_seen_twice_ends_the_walk_as_unreadable_not_forever() -> None:
    """No progress is the witness, not a timer: the same token again stops that group."""
    calls: list[str] = []

    def again(_i: str, _s: str, token: str) -> object:
        # The token repeats once and then the pages end, so a walk without the guard also stops.
        calls.append(token)
        return _paged(_NEXT if len(calls) == 1 else "", _test("//a:two", "2"))

    report = bb_targets.parse(_page(_first()), again, "inv")
    assert (report.unreadable, report.complete()) == (1, False)


def test_a_page_that_cannot_be_fetched_or_read_is_unreadable_and_keeps_what_was_listed() -> None:
    """An OSError or an answer with no group stops that group, counted, with the tests so far."""

    def broken(_i: str, _s: str, _t: str) -> object:
        msg = "boom"
        raise OSError(msg)

    failed = bb_targets.parse(_page(_first()), broken, "inv")
    empty = bb_targets.parse(_page(_first()), lambda _i, _s, _t: {"targetGroups": []}, "inv")
    assert (failed.unreadable, [t.label for t in failed.tests]) == (1, ["//a:one"])
    assert empty.unreadable == 1


def test_a_group_with_no_status_is_listed_short_and_named_not_followed() -> None:
    """The service does not page it: only its first targets list, and the verdict names it."""
    bare: dict[str, object] = {
        "targets": [{"metadata": {"label": "//a:b"}, "status": "BUILT"}],
        "totalCount": str(_BUILT_TOTAL),
        "nextPageToken": _NEXT,
    }

    def never(_i: str, _s: str, _t: str) -> object:
        pytest.fail("a group with no status must not be asked for pages")

    whole: dict[str, object] = {
        "status": "PASSED",
        "targets": [_test("//a:two", "2")],
        "totalCount": "1",
    }
    report = bb_targets.parse(_page(bare, whole), never, "inv")
    assert report.complete() is False
    assert "(no status) 1 of 1324" in report.verdict()
    assert "PASSED" not in report.verdict()


def test_without_a_page_reader_a_paged_group_stays_incomplete() -> None:
    """Parsing the first response alone never claims the whole invocation."""
    assert bb_targets.parse(_page(_first())).verdict().startswith("INCOMPLETE: listed 1 of 4")


def test_an_incomplete_report_names_no_maximum_and_prints_its_rows_as_observed_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """github-8f's rule: a partial listing has no `tests` row to read as the slowest."""
    assert bb_targets.main(["inv"], lambda _i: _page(_first()), lambda _i, _s, _t: {}) == 0
    report = cast("dict[str, object]", json.loads(capsys.readouterr().out))
    rows = cast("list[dict[str, object]]", report["observed_only"])
    assert str(report["status"]).startswith("INCOMPLETE")
    assert "tests" not in report
    assert rows[0]["label"] == "//a:one"

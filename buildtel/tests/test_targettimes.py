# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `targettimes`: ids read from a log, one row per test, coverage on each (W1572)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.buildtel import bb_targets, targettimes

if TYPE_CHECKING:
    from pathlib import Path

_ONE = "83efeedc-ab75-4cd5-a1d4-8a667410852a"
_TWO = "9761e453-aeb8-47a9-ad60-16f86145de39"
_MILLIS = 1850
_USAGE_EXIT = 2
_UNREACHABLE_EXIT = 3
_EXTRA = 5


def _page(*labels: str, total: int | None = None) -> dict[str, object]:
    # An invocation whose one group holds the given tests, declaring `total` targets if given.
    targets = [
        {
            "metadata": {"label": label},
            "status": "PASSED",
            "testSummary": {"totalRunDurationMillis": str(_MILLIS)},
        }
        for label in labels
    ]
    group = {"status": "PASSED", "targets": targets, "totalCount": str(total or len(labels))}
    return {"invocation": [{"targetGroups": [group]}]}


def _none(_invocation: str, _status: str, _token: str) -> object:
    return {}


def test_invocation_ids_are_taken_in_order_once_and_a_near_miss_is_ignored() -> None:
    """Both spellings of the URL in a log name one id once; text that is not a uuid is skipped."""
    text = (
        f"Streaming build results to: http://h:8080/invocation/{_ONE}\n"
        f"see http://h/invocation/{_TWO}\n"
        f"again http://h:8080/invocation/{_ONE}\n"
        "http://h/invocation/not-a-uuid\n"
    )
    assert targettimes.invocation_ids(text) == [_ONE, _TWO]


def test_a_row_per_test_target_carries_the_invocation_and_its_coverage() -> None:
    """A complete invocation marks every row complete; a short one marks every row incomplete."""
    whole = targettimes.read(_ONE, lambda _i: _page("//a:t", "//b:t"), _none)
    short = targettimes.read(_TWO, lambda _i: _page("//a:t", total=2), _none)
    assert [(r.invocation, r.label, r.millis, r.complete) for r in whole] == [
        (_ONE, "//a:t", _MILLIS, True),
        (_ONE, "//b:t", _MILLIS, True),
    ]
    assert [(r.invocation, r.complete) for r in short] == [(_TWO, False)]


def test_rows_are_the_whole_listing_not_the_report_cut_to_thirty() -> None:
    """The table keeps every test, where the report prints only the longest thirty."""
    labels = [f"//t:t{n}" for n in range(bb_targets.TOP_TESTS + _EXTRA)]
    rows = targettimes.read(_ONE, lambda _i: _page(*labels), _none)
    assert len(rows) == bb_targets.TOP_TESTS + _EXTRA


def test_main_prints_one_json_line_per_row_for_every_invocation_the_log_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The log is read, each id is fetched, and the rows come out as JSON lines."""
    log = tmp_path / "mtools.log"
    log.write_text(f"/invocation/{_ONE} and /invocation/{_TWO}\n", encoding="utf-8")
    pages = {_ONE: _page("//a:t"), _TWO: _page("//b:t")}
    assert targettimes.main([str(log)], lambda invocation: pages[invocation], _none) == 0
    out = capsys.readouterr().out
    lines = [cast("dict[str, object]", json.loads(line)) for line in out.splitlines()]
    assert [(r["invocation"], r["label"], r["complete"]) for r in lines] == [
        (_ONE, "//a:t", True),
        (_TWO, "//b:t", True),
    ]


def test_an_unreachable_invocation_is_named_and_the_others_still_print(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One dead id exits 3 after the rest are printed, never a traceback."""
    log = tmp_path / "mtools.log"
    log.write_text(f"/invocation/{_ONE} /invocation/{_TWO}\n", encoding="utf-8")

    def fetch(invocation: str) -> object:
        if invocation == _ONE:
            msg = "boom"
            raise OSError(msg)
        return _page("//b:t")

    assert targettimes.main([str(log)], fetch, _none) == _UNREACHABLE_EXIT
    seen = capsys.readouterr()
    assert f"{_ONE} unreachable: boom" in seen.err
    assert "//b:t" in seen.out


def test_a_log_that_names_no_invocation_prints_nothing_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Silence would read as an empty table, so the log is named."""
    log = tmp_path / "mtools.log"
    log.write_text("no build here\n", encoding="utf-8")
    assert targettimes.main([str(log)], lambda _i: {}, _none) == 0
    seen = capsys.readouterr()
    assert not seen.out
    assert "names no invocation" in seen.err


def test_a_symlinked_log_is_refused_not_followed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A link is made only to prove the refusal, inside tmp_path (operator 2026-10-02)."""
    real = tmp_path / "real.log"
    real.write_text(f"/invocation/{_ONE}\n", encoding="utf-8")
    link = tmp_path / "link.log"
    link.symlink_to(real)
    assert targettimes.main([str(link)], lambda _i: _page("//a:t"), _none) == _USAGE_EXIT
    assert "is a symlink; refused" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [[], ["-h"], ["a", "b"]])
def test_main_refuses_anything_but_one_log(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """No operand, a flag, or two operands is a usage error: exit 2 and the usage line."""
    assert targettimes.main(argv, lambda _i: {}, _none) == _USAGE_EXIT
    assert capsys.readouterr().err == targettimes.USAGE + "\n"


_CPU = 72.5


def _sample(target: str | None, value: float) -> str:
    metric: dict[str, object] = {} if target is None else {"target": target}
    row: dict[str, object] = {"metric": metric, "value": [1.0, str(value)]}
    return json.dumps(row)


def test_cpu_samples_read_target_and_value_and_skip_a_line_that_is_not_one() -> None:
    """W1895: one JSON sample per line becomes target -> seconds; noise is skipped, not raised."""
    text = f"{_sample('//a:t', _CPU)}\nnot json\n{_sample(None, 1.0)}\n"
    assert targettimes.cpu_samples(text) == {"//a:t": _CPU}


def test_a_row_with_a_cpu_sample_gains_cpu_s_and_a_row_without_one_does_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The join: `--cpu FILE` adds the column only where the label was measured."""
    log = tmp_path / "mtools.log"
    log.write_text(f"/invocation/{_ONE}\n", encoding="utf-8")
    cpu = tmp_path / "cpu.jsonl"
    cpu.write_text(_sample("//a:t", _CPU) + "\n", encoding="utf-8")
    page = _page("//a:t", "//b:t")
    assert targettimes.main([str(log), "--cpu", str(cpu)], lambda _i: page, _none) == 0
    lines = capsys.readouterr().out.splitlines()
    rows = {
        str(r["label"]): r for r in (cast("dict[str, object]", json.loads(line)) for line in lines)
    }
    assert rows["//a:t"]["cpu_s"] == _CPU
    assert "cpu_s" not in rows["//b:t"]


def test_an_unreadable_cpu_file_is_a_usage_error_naming_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A samples file that does not exist exits 2 and says which, never a traceback."""
    log = tmp_path / "mtools.log"
    log.write_text(f"/invocation/{_ONE}\n", encoding="utf-8")
    missing = tmp_path / "no-such.jsonl"
    argv = [str(log), "--cpu", str(missing)]
    assert targettimes.main(argv, lambda _i: _page("//a:t"), _none) == _USAGE_EXIT
    assert f"targettimes: {missing}" in capsys.readouterr().err

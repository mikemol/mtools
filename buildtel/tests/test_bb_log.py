# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `bb_log`: chunks fold into one log, and a log not read is never an empty one."""

from __future__ import annotations

import io

from mikemol.buildtel import bb_log, bb_records

INVOCATION = "17ce7707-ce45-42af-9b37-923da143a152"
URL = f"http://buildbuddy-web.buildbuddy.svc.cluster.local:8080/invocation/{INVOCATION}"
THREE_LINES = "alpha\nbeta\ngamma\n"
TAIL_TWO = 2
BAD_COMMAND_LINES: tuple[tuple[str, ...], ...] = (
    (),
    ("--all",),
    (INVOCATION, "--tail"),
    (INVOCATION, "--tail", "x"),
    (INVOCATION, "x"),
)


def _pages(*chunks: str) -> bb_log.Fetch:
    """Build a fetch that serves `chunks` in order, then empty chunks.

    Returns:
        a fetch whose chunk ids are the index of the next chunk.

    """

    def fetch(invoked: str, chunk_id: str) -> tuple[str, str]:
        del invoked
        index = int(chunk_id or "0")
        if index >= len(chunks):
            return "", str(index)
        return chunks[index], str(index + 1)

    return fetch


def _refusing(invoked: str, chunk_id: str) -> tuple[str, str]:
    """Fail as an unknown invocation does.

    Raises:
        OSError: always, as the service's non-200 answer does.

    """
    del invoked, chunk_id
    msg = "HTTP 500: no such invocation"
    raise OSError(msg)


def _stuck(invoked: str, chunk_id: str) -> tuple[str, str]:
    """Answer a chunk whose next id never advances.

    Returns:
        one line and the id it was asked for.

    """
    del invoked
    return "again\n", chunk_id


def test_the_id_is_taken_from_a_url_or_given_bare() -> None:
    """The URL bazel prints and the bare id name the same invocation."""
    assert bb_log.invocation_id(URL) == INVOCATION
    assert bb_log.invocation_id(INVOCATION) == INVOCATION


def test_chunks_are_followed_in_order_until_one_is_empty() -> None:
    """Every chunk is read and joined, and the empty one ends it."""
    whole = bb_log.collect(INVOCATION, _pages("one\n", "two\n", "three\n"))
    assert whole == "one\ntwo\nthree\n"


def test_a_next_id_that_does_not_advance_ends_the_read() -> None:
    """A service that repeats its id cannot hold the reader: one chunk, then stop."""
    assert bb_log.collect(INVOCATION, _stuck) == "again\n"


def test_the_last_lines_are_kept_in_order() -> None:
    """Tail keeps the end of the log, a zero or negative count keeps nothing."""
    assert bb_log.last_lines(THREE_LINES, TAIL_TWO) == "beta\ngamma\n"
    assert not bb_log.last_lines(THREE_LINES, 0)
    assert not bb_log.last_lines("", TAIL_TWO)


def test_the_default_prints_the_tail_and_all_prints_everything() -> None:
    """No flag prints the last DEFAULT_TAIL lines; --all every line; --tail N the last N."""
    many = "".join(f"line {number}\n" for number in range(bb_log.DEFAULT_TAIL + 5))
    out, err = io.StringIO(), io.StringIO()
    assert bb_log.main([INVOCATION], _pages(many), out, err) == 0
    assert len(out.getvalue().splitlines()) == bb_log.DEFAULT_TAIL
    assert out.getvalue().endswith(f"line {bb_log.DEFAULT_TAIL + 4}\n")
    everything = io.StringIO()
    assert bb_log.main([INVOCATION, "--all"], _pages(many), everything, err) == 0
    assert everything.getvalue() == many
    last = io.StringIO()
    assert bb_log.main([URL, "--tail", "2"], _pages(many), last, err) == 0
    assert len(last.getvalue().splitlines()) == TAIL_TWO


FAILED_RUN = (
    "INFO: Analyzed target\n"
    "[1 / 9] progress noise\n"
    "==================== Test output for //hooks:suite:\n"
    "hooks/tests/test_x.py:11: resolves out of the runfiles tree\n"
    f"{'=' * 80}\n"
    "[2 / 9] more progress noise\n"
    "ERROR: build failed in //hooks:suite\n"
    "//hooks:suite                                      FAILED in 1.1s\n"
    "INFO: Build completed\n"
)


def test_failures_pick_the_test_output_block_and_the_failed_lines_only() -> None:
    """The framed block, the ERROR line and the FAILED target stay; progress lines do not."""
    picked = bb_log.failures(FAILED_RUN)
    assert "resolves out of the runfiles tree" in picked
    assert "ERROR: build failed" in picked
    assert "FAILED in 1.1s" in picked
    assert "progress noise" not in picked
    assert "Analyzed target" not in picked


def test_a_passing_log_has_no_failures_and_the_flag_prints_only_them() -> None:
    """A log with nothing failed yields nothing; --failures prints just the picked lines."""
    assert not bb_log.failures("INFO: all good\n[1 / 1] done\n")
    out, err = io.StringIO(), io.StringIO()
    assert bb_log.main([INVOCATION, "--failures"], _pages(FAILED_RUN), out, err) == 0
    assert out.getvalue() == bb_log.failures(FAILED_RUN)


def test_a_log_that_could_not_be_read_is_exit_three_and_never_empty() -> None:
    """An unknown invocation or a dead service exits 3 on stderr with nothing on stdout."""
    out, err = io.StringIO(), io.StringIO()
    code = bb_log.main([INVOCATION], _refusing, out, err)
    assert code == bb_records.EXIT_UNREACHABLE
    assert not out.getvalue()
    assert "could not be read" in err.getvalue()


def test_a_log_read_with_no_lines_says_so_and_exits_zero() -> None:
    """Reading nothing successfully is stated, so it cannot be mistaken for the failure above."""
    out, err = io.StringIO(), io.StringIO()
    assert bb_log.main([INVOCATION], _pages(), out, err) == 0
    assert not out.getvalue()
    assert "holds no lines" in err.getvalue()


def test_anything_but_an_id_with_one_known_flag_is_a_usage_error() -> None:
    """No id, a flag first, a bad count and extra words all exit 2 and name the usage."""
    for argv in BAD_COMMAND_LINES:
        out, err = io.StringIO(), io.StringIO()
        assert bb_log.main(list(argv), _pages("x\n"), out, err) == bb_records.EXIT_USAGE
        assert "usage: mikemol-buildlog" in err.getvalue()

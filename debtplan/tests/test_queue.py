# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The queue: one writer called in this process, its words captured, its cards read back."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mikemol.pathsforward.store import UnreadableStateError

from mikemol.debtplan.queue import EXIT_REFUSED, Card, Queue

THREE = 3


def _real(tmp_path: Path) -> Queue:
    """Initialise a state file with the real writer.

    Returns:
        A queue over it.

    """
    queue = Queue(tmp_path / "pf.json")
    code, _ = queue.run("--init")
    assert code == 0
    return queue


def test_the_state_file_comes_first_then_the_arguments() -> None:
    """The writer is handed `--state PATH` before whatever was asked."""
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        seen.append(argv)
        return 0

    result = Queue(Path("/s/pf.json"), runner).run("--add", "title")
    assert seen == [["--state", "/s/pf.json", "--add", "title"]]
    assert result == (0, "")


def test_the_writers_exit_code_is_returned() -> None:
    """A non-zero code comes back as it was."""

    def runner(_argv: list[str]) -> int:
        return THREE

    assert Queue(Path("/s/pf.json"), runner).run("--x")[0] == THREE


def test_standard_output_and_error_are_captured_together_in_order() -> None:
    """Nothing the writer says reaches the terminal; it all comes back as one string."""

    def runner(_argv: list[str]) -> int:
        sys.stdout.write("out\n")
        sys.stderr.write("err\n")
        return 0

    assert Queue(Path("/s/pf.json"), runner).run() == (0, "out\nerr\n")


@pytest.mark.parametrize("code", [0, 2, THREE])
def test_a_system_exit_with_an_integer_code_is_that_code(code: int) -> None:
    """A writer that exits through SystemExit(n) is read as n."""

    def runner(_argv: list[str]) -> int:
        raise SystemExit(code)

    assert Queue(Path("/s/pf.json"), runner).run()[0] == code


@pytest.mark.parametrize("code", [None, "words"])
def test_a_system_exit_without_an_integer_code_is_refused(code: str | None) -> None:
    """None or a message is not a success, so it reads as refused."""

    def runner(_argv: list[str]) -> int:
        raise SystemExit(code)

    assert Queue(Path("/s/pf.json"), runner).run()[0] == EXIT_REFUSED


def test_cards_are_keyed_by_the_file_between_the_prefix_and_the_count(tmp_path: Path) -> None:
    """A title `<prefix><file> (<n> findings)` keys its card by file; other titles are ignored."""
    queue = _real(tmp_path)
    queue.run("--add", "t: a.py (3 findings)")
    queue.run("--add", "an unrelated card")
    queue.run("--add", "t: dir/b.py (1 findings)")
    assert queue.cards("t: ") == {"a.py": Card("W1", "ready"), "dir/b.py": Card("W3", "ready")}


def test_a_title_with_no_count_keys_by_the_rest_of_the_title(tmp_path: Path) -> None:
    """With no ` (` the whole remainder is the file."""
    queue = _real(tmp_path)
    queue.run("--add", "t: c.py")
    assert queue.cards("t: ") == {"c.py": Card("W1", "ready")}


def test_a_card_reads_back_its_current_status(tmp_path: Path) -> None:
    """The card carries the status the queue holds now."""
    queue = _real(tmp_path)
    queue.run("--add", "t: a.py (1 findings)")
    queue.run("--update", "W1", "--status", "working")
    assert queue.cards("t: ")["a.py"] == Card("W1", "working")


def test_no_card_matches_a_prefix_nothing_starts_with(tmp_path: Path) -> None:
    """An unmatched prefix reads no cards."""
    queue = _real(tmp_path)
    queue.run("--add", "t: a.py (1 findings)")
    assert queue.cards("zzz: ") == {}


def test_an_unreadable_state_file_is_refused_not_read_as_no_cards(tmp_path: Path) -> None:
    """A missing queue is an error: no cards must not mean nothing to sync."""
    with pytest.raises(UnreadableStateError):
        Queue(tmp_path / "absent.json").cards("t: ")

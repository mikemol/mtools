# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A follower reads the verdict its leader left, once, and a torn or absent file is none (W1671)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import trainverdict
from mikemol.hooks.traindrive import Verdict

if TYPE_CHECKING:
    from pathlib import Path

KEY = "1792000000000000000"
REFUSED = 1


def test_a_written_verdict_reads_back_with_its_code_and_text(tmp_path: Path) -> None:
    """The text a stack would have printed, and its exit code, survive the file."""
    sent = Verdict(KEY, REFUSED, "REFUSED repo (rc=1): found bad\n")
    assert trainverdict.write(tmp_path / "ledger", sent)
    assert trainverdict.read(tmp_path / "ledger", KEY) == sent


def test_take_reads_once_and_clears_the_file(tmp_path: Path) -> None:
    """A process re-executed by the claim cannot print the same verdict twice."""
    ledger = tmp_path / "ledger"
    trainverdict.write(ledger, Verdict(KEY, 0, "COMMITTED repo abc1234 card [PUSHED]\n"))
    assert trainverdict.take(ledger, KEY) is not None
    assert trainverdict.take(ledger, KEY) is None
    assert not trainverdict.verdict_path(ledger, KEY).exists()


def test_a_missing_or_torn_file_is_no_verdict(tmp_path: Path) -> None:
    """Not an object, no integer code, no text, a boolean code and unreadable text all read none."""
    ledger = tmp_path / "ledger"
    assert trainverdict.read(ledger, KEY) is None
    ledger.mkdir()
    path = trainverdict.verdict_path(ledger, KEY)
    for torn in ("not json", "[]", '{"code": 1}', '{"text": "x"}', '{"code": true, "text": "x"}'):
        path.write_text(torn, encoding="utf-8")
        assert trainverdict.read(ledger, KEY) is None


def test_a_ledger_that_cannot_be_written_reports_false(tmp_path: Path) -> None:
    """The leader learns the follower will run on its own turn instead."""
    blocker = tmp_path / "ledger"
    blocker.write_text("a file where the directory should be", encoding="utf-8")
    assert not trainverdict.write(blocker, Verdict(KEY, 0, "x\n"))

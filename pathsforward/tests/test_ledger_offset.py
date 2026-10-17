# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ledger reader takes any RFC 3339 offset and reports UTC, while the writer keeps Z."""

import pytest

from mikemol.pathsforward import ledger

_TAIL = 'tick W7 advanced unblock "a note"'


def _parsed(stamp: str) -> ledger.Parsed:
    got = ledger.parse(f"{stamp}  {_TAIL}")
    assert isinstance(got, ledger.Parsed)
    return got


def test_a_plus_zero_offset_reads_as_the_z_form() -> None:
    """el-openglo's 162 lines: the same instant, spelled +00:00."""
    assert _parsed("2026-09-20T18:59:08+00:00").stamp == "2026-09-20T18:59:08Z"


def test_a_non_zero_offset_is_converted_to_utc() -> None:
    """Half past six in the evening at +05:30 is 13:00 UTC, not 18:30."""
    assert _parsed("2026-09-20T18:30:00+05:30").stamp == "2026-09-20T13:00:00Z"


def test_a_negative_offset_crossing_midnight_is_converted() -> None:
    """The date moves with the offset."""
    assert _parsed("2026-09-20T22:00:00-04:00").stamp == "2026-09-21T02:00:00Z"


def test_the_columns_after_the_stamp_are_unchanged() -> None:
    """Only the stamp is normalised."""
    entry = _parsed("2026-09-20T18:59:08+00:00").entry
    assert (entry.kind, entry.symbol, entry.outcome, entry.mechanism, entry.note) == (
        "tick",
        "W7",
        "advanced",
        "unblock",
        "a note",
    )


@pytest.mark.parametrize(
    "stamp",
    ["2026-09-20T18:59:08.5+00:00", "2026-09-20T18:59:08", "2026-09-20T", "yesterday"],
)
def test_a_fraction_a_naive_or_partial_stamp_is_still_unparsed(stamp: str) -> None:
    """Dropping a fraction would change the instant; the others name no instant at all."""
    assert isinstance(ledger.parse(f"{stamp}  {_TAIL}"), ledger.Unparsed)


def test_the_writer_still_refuses_an_offset_stamp() -> None:
    """The reader is wider than the writer, which keeps one spelling."""
    entry = ledger.Entry("tick", "W7", "advanced", "unblock", "a note")
    with pytest.raises(ledger.MalformedEntryError):
        ledger.line(entry, "2026-09-20T18:59:08+00:00")
    assert ledger.line(entry, "2026-09-20T18:59:08Z").startswith("2026-09-20T18:59:08Z")

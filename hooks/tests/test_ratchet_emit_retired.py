# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A retired ratchet is SENT, every run it is listed, never inferred from silence (W1964).

⚑ THE CONTROLS: a tombstone line becomes one `mikemol.ratchet.retired` row of value 1 with the
labels repo, ratchet and reason; a ratchet row, a comment and an UNREAD line are not tombstones;
the repo label is the NAME the caller gave, not the census directory's basename; and a run with
no tombstone sends no retired row.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.hooks import ratchet_emit

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_NOW = 5
_CENSUS = (
    "snap a.json baseline value=1 floor=0 guessed=0\n"
    "snap old.txt retired reason=paid-to-zero-and-removed sha=abc1234\n"
    "snap c.txt retired reason=renamed-to sha=abc1234 to=d.txt\n"
    "snap broken.json baseline value=UNREAD floor=0 guessed=1\n"
    "# 2 ratchet file(s), 1 unread\n"
)


def test_a_tombstone_line_is_read_and_a_ratchet_row_or_comment_is_not() -> None:
    """Both reasons are read, the rename's target is not part of the row, and nothing else is."""
    assert ratchet_emit.parse_tombstones(_CENSUS) == [
        ("snap", "old.txt", "paid-to-zero-and-removed"),
        ("snap", "c.txt", "renamed-to"),
    ]


def test_a_tombstone_becomes_a_retired_row_of_value_one_with_three_labels() -> None:
    """The series is `mikemol.ratchet.retired`, 1 per tombstone, labelled repo, ratchet, reason."""
    [row] = ratchet_emit.retired_rows([("mtools", "old.txt", "renamed-to")], _NOW)
    assert row["name"] == "mikemol.ratchet.retired"
    assert row["value"] == 1
    assert row["time_ns"] == _NOW
    assert row["fields"] == {"repo": "mtools", "ratchet": "old.txt", "reason": "renamed-to"}


def test_main_sends_each_tombstone_under_the_callers_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The census directory's basename (`snap`) is never the label; two retired rows are sent."""
    tool = tmp_path / "mikemol-ratchet"
    tool.write_text("", encoding="utf-8")
    monkeypatch.setenv("RATCHET_BIN", str(tool))
    monkeypatch.setenv("MIKEMOL_OTLP_BIN", "/bin/otlp")
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "x")
    sent: list[str] = []

    def run(_argv: Sequence[str]) -> tuple[int, str]:
        return 0, _CENSUS

    def spawn(_argv: Sequence[str], text: str) -> None:
        sent.append(text)

    assert ratchet_emit.main(["mtools", "/snapshot/tree"], spawn, run) == 0
    rows = [cast("dict[str, object]", json.loads(line)) for line in sent[0].splitlines()]
    retired = [row for row in rows if row["name"] == "mikemol.ratchet.retired"]
    assert [cast("dict[str, str]", row["fields"])["ratchet"] for row in retired] == [
        "old.txt",
        "c.txt",
    ]
    assert {cast("dict[str, str]", row["fields"])["repo"] for row in retired} == {"mtools"}


def test_a_census_with_no_tombstone_sends_no_retired_row() -> None:
    """Retired is present only while a declaration lists it."""
    assert ratchet_emit.parse_tombstones("snap a.json baseline value=1 floor=0\n") == []
    assert ratchet_emit.retired_rows([], _NOW) == []

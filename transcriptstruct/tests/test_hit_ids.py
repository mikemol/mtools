# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A search row carries the record's uuid and timestamp, so a ruling is warranted from one call."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_UUID = "7a5c9732-76b5-4e6b-b03e-6dc966b85e16"
_AT = "2026-10-17T22:24:58.725Z"


def _transcript(tmp_path: Path, *, ids: bool = True) -> Path:
    message: dict[str, object] = {"role": "user", "content": "ship the drain"}
    envelope: dict[str, object] = {"type": "user", "message": message}
    if ids:
        envelope.update({"uuid": _UUID, "timestamp": _AT})
    path = tmp_path / "t.jsonl"
    path.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
    return path


def _first_row(*argv: str) -> dict[str, object]:
    out = io.StringIO()
    assert main(list(argv), out=out) == 0
    return cast("dict[str, object]", json.loads(out.getvalue().splitlines()[0]))


def test_a_human_row_carries_the_uuid_and_the_timestamp(tmp_path: Path) -> None:
    """The row --warrant needs: the uuid, and when it was said."""
    row = _first_row(str(_transcript(tmp_path)), "--human", "drain")
    assert (row["uuid"], row["at"]) == (_UUID, _AT)


def test_a_grep_row_carries_them_too(tmp_path: Path) -> None:
    """--grep finds blocks, and its rows name the record the same way."""
    row = _first_row(str(_transcript(tmp_path)), "--grep", "drain")
    assert (row["uuid"], row["at"]) == (_UUID, _AT)


def test_a_record_without_ids_gives_empty_strings_not_a_missing_key(tmp_path: Path) -> None:
    """A consumer reads the keys unconditionally."""
    row = _first_row(str(_transcript(tmp_path, ids=False)), "--human", "drain")
    assert (row["uuid"], row["at"]) == ("", "")


def test_the_old_keys_are_unchanged(tmp_path: Path) -> None:
    """Adding keys breaks no reader of line, kind, text or span."""
    row = _first_row(str(_transcript(tmp_path)), "--human", "drain")
    assert [row[key] for key in ("line", "kind", "text")] == [1, "human", "ship the drain"]

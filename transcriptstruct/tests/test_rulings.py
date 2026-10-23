# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 9: the rulings ledger is append-only, incremental and walks a tree.

mtools:W1401 and W1402.

⚑ THE CONTROLS ARE WHAT MUST NOT HAPPEN: a second harvest of the same transcript adds a line, a
line already written is rewritten, an unchanged file is read again, and a link is followed. A
transcript that GREW adds exactly its new utterance, which proves the ledger can still take more.
Every fixture is SYNTHETIC.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.rulings import SEEN_SUFFIX, append, harvest_tree, known, transcripts

if TYPE_CHECKING:
    from pathlib import Path

STAMP = "2026-10-16T14:02:11.000Z"
_TWO = 2


def _line(uuid: str, text: str) -> str:
    message: dict[str, object] = {"role": "user", "content": text}
    envelope: dict[str, object] = {
        "type": "user",
        "message": message,
        "uuid": uuid,
        "timestamp": STAMP,
        "sessionId": "s",
    }
    return json.dumps(envelope)


def _transcript(root: Path, name: str, *lines: str) -> Path:
    path = root / "proj" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_a_ledger_line_with_a_line_separator_in_its_text_is_read_whole(tmp_path: Path) -> None:
    """What `append` wrote with a raw separator, `known` reads back as one IRI (W1864)."""
    ledger = tmp_path / "rulings.jsonl"
    entity: dict[str, object] = {"@id": "file:///t.jsonl#odd", "x": f"a{chr(0x2028)}b{chr(0x85)}c"}
    assert append(ledger, [entity]) == 1
    assert known(ledger) == {"file:///t.jsonl#odd"}


def test_a_second_harvest_of_the_same_tree_adds_nothing_and_reads_nothing(tmp_path: Path) -> None:
    """Idempotent twice over: the lines are not repeated and the unchanged file is spared."""
    _transcript(tmp_path, "a.jsonl", _line("u1", "first ruling"))
    ledger = tmp_path / "rulings.jsonl"
    first = harvest_tree(tmp_path / "proj", ledger)
    assert (first.read, first.spared, first.added) == (1, 0, 1)
    before = ledger.read_text(encoding="utf-8")
    second = harvest_tree(tmp_path / "proj", ledger)
    assert (second.read, second.spared, second.added) == (0, 1, 0)
    assert ledger.read_text(encoding="utf-8") == before


def test_a_transcript_that_grew_adds_only_its_new_utterance(tmp_path: Path) -> None:
    """The control that the ledger still takes more: one new line, the old line byte-identical."""
    path = _transcript(tmp_path, "a.jsonl", _line("u1", "first ruling"))
    ledger = tmp_path / "rulings.jsonl"
    harvest_tree(tmp_path / "proj", ledger)
    old = ledger.read_text(encoding="utf-8")
    path.write_text(path.read_text(encoding="utf-8") + _line("u2", "second ruling") + "\n", "utf-8")
    grown = harvest_tree(tmp_path / "proj", ledger)
    assert grown.added == 1
    assert ledger.read_text(encoding="utf-8").startswith(old)
    assert len(known(ledger)) == _TWO


def test_deleting_the_spare_record_costs_a_slow_run_and_loses_nothing(tmp_path: Path) -> None:
    """The speed-up is only that: without it the file is read again and no line repeats."""
    _transcript(tmp_path, "a.jsonl", _line("u1", "first ruling"))
    ledger = tmp_path / "rulings.jsonl"
    harvest_tree(tmp_path / "proj", ledger)
    ledger.with_name(ledger.name + SEEN_SUFFIX).unlink()
    again = harvest_tree(tmp_path / "proj", ledger)
    assert (again.read, again.added) == (1, 0)


def test_append_skips_a_known_iri_and_the_walk_lists_transcripts_in_path_order(
    tmp_path: Path,
) -> None:
    """Direct: a repeated entity is refused; the walk lists only `.jsonl` files, sorted."""
    ledger = tmp_path / "rulings.jsonl"
    entity: dict[str, object] = {"@id": "file:///x.jsonl#u1"}
    assert append(ledger, [entity]) == 1
    assert append(ledger, [entity]) == 0
    second = _transcript(tmp_path, "b.jsonl", _line("u1", "ruling"))
    first = _transcript(tmp_path, "a.jsonl", _line("u2", "ruling"))
    (tmp_path / "proj" / "notes.txt").write_text("not a transcript", encoding="utf-8")
    assert transcripts(tmp_path / "proj") == [first, second]


def test_the_cli_walks_a_tree_into_a_ledger_and_reports_its_counts(tmp_path: Path) -> None:
    """`--harvest-tree LEDGER` over a projects directory prints one `#` summary line."""
    _transcript(tmp_path, "a.jsonl", _line("u1", "first ruling"))
    ledger = tmp_path / "rulings.jsonl"
    out = io.StringIO()
    assert main([str(tmp_path / "proj"), "--harvest-tree", str(ledger)], out) == 0
    assert (
        out.getvalue()
        == "# read 1 file(s), spared 0, added 1 line(s), 0 human utterance(s) uncitable\n"
    )

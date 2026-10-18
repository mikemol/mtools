# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A memory directory is audited against its project's transcripts, read-only (W1545)."""

import io
import json
import os
from pathlib import Path

from mikemol.transcriptstruct import memaudit
from mikemol.transcriptstruct.cli import main

_SAID = "Never create a symlink anywhere, those are inherently unsafe."
_NOTE = f"""---
name: no-symlinks
description: "operator ruling 2026-10-02 - symlinks are unsafe"
---

**Why:** operator, 2026-10-02: "{_SAID}" Swarm drafts may need one.
**Why:** operator, 2026-10-02: "A quotation nobody ever said in this transcript." Stop.
"""
_LATER = "Swarm drafts: the symlinks ruling is that unsafe links are fine now."


def _record(text: str, uuid: str, at: str) -> str:
    message: dict[str, object] = {"role": "user", "content": text}
    envelope: dict[str, object] = {
        "type": "user",
        "message": message,
        "uuid": uuid,
        "timestamp": at,
    }
    return json.dumps(envelope)


def _project(tmp_path: Path) -> Path:
    memory = tmp_path / "proj" / "memory"
    memory.mkdir(parents=True)
    (memory / "no-symlinks.md").write_text(_NOTE, encoding="utf-8")
    index = "- [x](no-symlinks.md) - agents may swarm, so an audited index would show a row\n"
    (memory / "MEMORY.md").write_text(index, encoding="utf-8")
    lines = [
        _record(_SAID, "u-said", "2026-10-02T23:00:00Z"),
        _record(_LATER, "u-later", "2026-10-17T10:00:00Z"),
    ]
    (tmp_path / "proj" / "s.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return memory


def test_each_claimed_quote_is_warranted_by_its_record_or_reported_unwarranted(
    tmp_path: Path,
) -> None:
    """The quote that was said names its uuid; the invented one is UNWARRANTED."""
    rows = memaudit.audit(_project(tmp_path))
    by_status = {(r.status, r.detail.split("uuid=")[-1]) for r in rows if "uuid=" in r.detail}
    assert ("WARRANTED", "u-said") in by_status
    assert any(r.status == "UNWARRANTED" and "nobody ever said" in r.detail for r in rows)


def test_a_line_that_grants_is_flagged_and_the_index_is_skipped(tmp_path: Path) -> None:
    """The grant words come out as one row for the line, and MEMORY.md is never audited."""
    rows = memaudit.audit(_project(tmp_path))
    assert any(r.status == "GRANT" and "swarm" in r.detail and "may" in r.detail for r in rows)
    assert {r.note for r in rows} == {"no-symlinks.md"}


def test_a_later_utterance_on_the_same_subject_is_possibly_superseded(tmp_path: Path) -> None:
    """The newer record shares three or more of the note's terms, so it is shown, with its uuid."""
    rows = memaudit.audit(_project(tmp_path))
    later = [r for r in rows if r.status == memaudit.SUPERSEDED]
    assert len(later) == 1
    assert "u-later" in later[0].detail


def _linked_notes(tmp_path: Path) -> Path:
    """Write an older note linking a newer one on the same subject, and the newer linking back.

    Returns:
        the memory directory.

    """
    memory = tmp_path / "proj" / "memory"
    memory.mkdir(parents=True)
    head = 'description: "swarm drafts about symlinks and unsafe links"\nmetadata:\n  modified: '
    old = f"---\nname: old\n{head}2026-10-04T00:00:00Z\n---\n\nSee [[new]].\n"
    new = f"---\nname: new\n{head}2026-10-16T00:00:00Z\n---\n\nSee [[old]].\n"
    (memory / "old.md").write_text(old, encoding="utf-8")
    (memory / "new.md").write_text(new, encoding="utf-8")
    return memory


def test_a_newer_linked_note_that_shares_the_subject_is_reported_from_the_older(
    tmp_path: Path,
) -> None:
    """The author's own link names a note modified later on the same subject: LINKED-NEWER."""
    rows = memaudit.audit(_linked_notes(tmp_path))
    linked = [(r.note, r.detail) for r in rows if r.status == memaudit.LINKED_NEWER]
    assert linked == [("old.md", "new.md modified 2026-10-16T00:00:00Z")]


def test_a_quote_given_in_another_project_is_elsewhere_not_unwarranted(tmp_path: Path) -> None:
    """The ruling sits in a sibling project's transcript, so the row says where it is."""
    memory = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    gone = "A quotation nobody ever said in this transcript."
    line = _record(gone, "u-else", "2026-10-03T08:00:00Z")
    (other / "t.jsonl").write_text(line + "\n", encoding="utf-8")
    rows = memaudit.audit(memory)
    found = [r for r in rows if r.status == memaudit.ELSEWHERE]
    assert len(found) == 1
    assert "u-else" in found[0].detail
    assert str(other) in found[0].detail
    assert not any(r.status == "UNWARRANTED" for r in rows)


def test_a_quote_no_project_carries_stays_unwarranted(tmp_path: Path) -> None:
    """Searching the siblings is not a way to excuse a quote: a miss everywhere is still a miss."""
    rows = memaudit.audit(_project(tmp_path))
    assert any(r.status == "UNWARRANTED" and "nobody ever said" in r.detail for r in rows)


def _memory(tmp_path: Path, index: str | None, *names: str) -> Path:
    # A memory directory holding the named notes and, when given, an index text.
    memory = tmp_path / "proj" / "memory"
    memory.mkdir(parents=True)
    for name in names:
        (memory / name).write_text("---\nname: n\n---\n\nPlain text.\n", encoding="utf-8")
    if index is not None:
        (memory / "MEMORY.md").write_text(index, encoding="utf-8")
    return memory


def test_a_note_no_index_line_points_at_is_unindexed_and_an_indexed_one_is_not(
    tmp_path: Path,
) -> None:
    """The el-openglo shape: a note with no MEMORY.md line never loads, so it is reported."""
    memory = _memory(tmp_path, "- [Seen](seen.md) - indexed\n", "seen.md", "hidden.md")
    rows = [r for r in memaudit.audit(memory) if r.status == memaudit.UNINDEXED]
    assert [(r.note, r.line) for r in rows] == [("hidden.md", 0)]
    assert "MEMORY.md" in rows[0].detail


def test_an_index_line_whose_file_is_missing_is_dangling_on_the_index(tmp_path: Path) -> None:
    """A rule the author thinks is loaded and is not: the row sits on MEMORY.md at that line."""
    index = "- [Seen](seen.md) - indexed\n- [Gone](gone.md) - deleted\n"
    memory = _memory(tmp_path, index, "seen.md")
    rows = memaudit.audit(memory)
    dangling = [(r.note, r.line, r.detail) for r in rows if r.status == memaudit.DANGLING]
    assert dangling == [("MEMORY.md", 2, "gone.md is not in the directory")]
    assert not any(r.status == memaudit.UNINDEXED for r in rows)


def test_a_directory_with_no_index_has_every_note_unindexed(tmp_path: Path) -> None:
    """With no MEMORY.md nothing loads at all."""
    memory = _memory(tmp_path, None, "a.md", "b.md")
    rows = [r for r in memaudit.audit(memory) if r.status == memaudit.UNINDEXED]
    assert [r.note for r in rows] == ["a.md", "b.md"]


def test_the_index_reader_maps_each_target_to_its_first_line_and_reads_several_per_line() -> None:
    """A note linked twice reports the earlier line; two links on one line are both read."""
    text = "- [A](a.md) and [B](b.md)\n- [A again](a.md)\n- [not a note](page.html)\n"
    assert memaudit.indexed(text) == {"a.md": 1, "b.md": 1}


def _swarm_pair(tmp_path: Path, grant_at: str, ruling_at: str) -> Path:
    """Write an indexed grant note and an unindexed note on the same subject, and an unrelated one.

    Returns:
        the memory directory.

    """
    memory = tmp_path / "proj" / "memory"
    memory.mkdir(parents=True)
    head = '---\nname: {n}\ndescription: "{d}"\nmetadata:\n  modified: {m}\n---\n\n{b}\n'
    notes = {
        "grant.md": ("swarm anything actionable every tick", grant_at, "Agents may swarm."),
        "ruling.md": ("swarm withdrawn, anything actionable needs a card", ruling_at, "Stop."),
        "other.md": ("quiet unrelated gardening advice", ruling_at, "Water the plants."),
    }
    for name, (desc, stamp, body) in notes.items():
        text = head.format(n=name, d=desc, m=stamp, b=body)
        (memory / name).write_text(text, encoding="utf-8")
    (memory / "MEMORY.md").write_text("- [Grant](grant.md) - swarm\n", encoding="utf-8")
    return memory


def test_an_unindexed_note_newer_than_an_indexed_grant_on_its_subject_ranks_first(
    tmp_path: Path,
) -> None:
    """The el-openglo shape: the withdrawing ruling was never indexed, so it leads the report."""
    rows = memaudit.audit(_swarm_pair(tmp_path, "2026-10-03T00:00:00Z", "2026-10-18T00:00:00Z"))
    assert (rows[0].note, rows[0].status) == ("ruling.md", memaudit.UNINDEXED)
    assert "newer than grant.md (GRANT)" in rows[0].detail
    other = next(r for r in rows if r.note == "other.md" and r.status == memaudit.UNINDEXED)
    assert "may supersede" not in other.detail
    assert rows.index(other) > 0


def test_an_unindexed_note_older_than_the_grant_is_not_ranked_ahead(tmp_path: Path) -> None:
    """An older note cannot have withdrawn a newer grant: it is reported, in place."""
    rows = memaudit.audit(_swarm_pair(tmp_path, "2026-10-18T00:00:00Z", "2026-10-03T00:00:00Z"))
    ruling = next(r for r in rows if r.note == "ruling.md" and r.status == memaudit.UNINDEXED)
    assert "may supersede" not in ruling.detail


def test_without_modified_stamps_the_file_times_decide_which_note_is_newer(tmp_path: Path) -> None:
    """Notes with no `modified:` line fall back to when their files were last written."""
    memory = _swarm_pair(tmp_path, "", "")
    older, newer = 1_000_000_000_000_000_000, 2_000_000_000_000_000_000
    os.utime(memory / "grant.md", ns=(older, older))
    os.utime(memory / "ruling.md", ns=(newer, newer))
    rows = memaudit.audit(memory)
    assert (rows[0].note, rows[0].status) == ("ruling.md", memaudit.UNINDEXED)


def test_without_modified_stamps_an_older_file_is_not_ranked_ahead(tmp_path: Path) -> None:
    """The file-time fallback cuts both ways: the unindexed note written first is not newer."""
    memory = _swarm_pair(tmp_path, "", "")
    older, newer = 1_000_000_000_000_000_000, 2_000_000_000_000_000_000
    os.utime(memory / "grant.md", ns=(newer, newer))
    os.utime(memory / "ruling.md", ns=(older, older))
    ruling = next(r for r in memaudit.audit(memory) if r.note == "ruling.md")
    assert "may supersede" not in ruling.detail


def test_an_indexed_note_with_no_grant_row_does_not_make_an_unindexed_note_urgent(
    tmp_path: Path,
) -> None:
    """Only a GRANT note can be the stale rule a newer ruling withdrew."""
    memory = _swarm_pair(tmp_path, "2026-10-03T00:00:00Z", "2026-10-18T00:00:00Z")
    said = "Operator ruling 2026-10-01 - plain advice."
    plain = (memory / "grant.md").read_text(encoding="utf-8").replace("Agents may swarm.", said)
    (memory / "grant.md").write_text(plain, encoding="utf-8")
    rows = memaudit.audit(memory)
    ruling = next(r for r in rows if r.note == "ruling.md" and r.status == memaudit.UNINDEXED)
    assert "may supersede" not in ruling.detail


def test_the_mode_prints_one_row_per_line_and_writes_nothing(tmp_path: Path) -> None:
    """`--audit-memory DIR` is a dry run: rows on stdout, every note left as it was."""
    memory = _project(tmp_path)
    before = (memory / "no-symlinks.md").read_text(encoding="utf-8")
    out = io.StringIO()
    assert main(["--audit-memory", str(memory)], out=out) == 0
    assert out.getvalue().count("\n") == len(memaudit.audit(memory))
    assert (memory / "no-symlinks.md").read_text(encoding="utf-8") == before

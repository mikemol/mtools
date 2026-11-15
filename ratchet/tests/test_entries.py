# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`census --entries` lists the entries behind each ratchet value, and they always agree (W2306)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ratchet import cli, entries, kinds

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_BODIES = {
    "ruff-baseline.json": '{"a.py": {"D103": 3, "ANN001": 1}, "b.py": {"E501": 2}}',
    "debt-ledger.json": '{"x": "", "y": false, "z": ["k1", "k2"]}',
    "empty-baseline.json": "{}",
    "public_ratchet_baseline.txt": "# header\n\na::b\nc::d\n",
    "ratchet-preview.txt": "k1\nk2\nk3\n",
    "baseline.tsv": "letter\tmismatch\na\t1\nb\t2\n",
    "private_allowlist.txt": "one\n",
}


def test_the_entries_of_every_kind_equal_the_census_value(tmp_path: Path) -> None:
    """The contract: a list that disagreed with the value would pay down debt still counted."""
    for name, body in _BODIES.items():
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        listed = entries.entries_of(path)
        assert listed is not None, name
        assert len(listed) == kinds.value_of(path), name


def test_a_file_rule_count_baseline_gives_each_entry_its_file_and_rule(tmp_path: Path) -> None:
    """The first two keys of a `file -> rule -> count` baseline are the file and the rule."""
    path = tmp_path / "ruff-baseline.json"
    path.write_text(_BODIES["ruff-baseline.json"], encoding="utf-8")
    assert entries.entries_of(path) == [
        entries.Entry("a.py/D103", "a.py", "D103"),
        entries.Entry("a.py/ANN001", "a.py", "ANN001"),
        entries.Entry("b.py/E501", "b.py", "E501"),
    ]


def test_a_text_baseline_lists_its_lines_and_a_table_does_not_list_its_header(
    tmp_path: Path,
) -> None:
    """A line is its own key; blank lines, comments and a .tsv header are not entries."""
    text = tmp_path / "public_ratchet_baseline.txt"
    text.write_text(_BODIES["public_ratchet_baseline.txt"], encoding="utf-8")
    assert [e.key for e in entries.entries_of(text) or []] == ["a::b", "c::d"]
    table = tmp_path / "baseline.tsv"
    table.write_text(_BODIES["baseline.tsv"], encoding="utf-8")
    assert [e.key for e in entries.entries_of(table) or []] == ["a\t1", "b\t2"]


def test_an_unreadable_file_has_no_list_never_an_empty_one(tmp_path: Path) -> None:
    """None is the census's UNREAD: an empty list would read as debt paid."""
    broken = tmp_path / "ruff-baseline.json"
    broken.write_text("{nope", encoding="utf-8")
    assert entries.entries_of(broken) is None
    assert entries.entries_of(tmp_path / "gone-baseline.json") is None
    empty = tmp_path / "empty-baseline.json"
    empty.write_text("{}", encoding="utf-8")
    assert entries.entries_of(empty) == []


def test_census_entries_prints_one_json_line_per_entry_and_only_for_named_kinds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pyproject exemption row is not a file of lines, so it is left out, not mis-listed."""
    repo = tmp_path / "alpha"
    repo.mkdir()
    (repo / "ratchet-preview.txt").write_text("k1\nk2\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    assert cli.main(["census", "--entries", "--repo", str(repo)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        entries.as_json("ratchet-preview.txt", "preview", entries.Entry("k1", None, None)),
        entries.as_json("ratchet-preview.txt", "preview", entries.Entry("k2", None, None)),
    ]

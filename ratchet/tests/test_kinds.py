# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which files are ratchet state and how much debt each records (W1906)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.ratchet import kinds

if TYPE_CHECKING:
    import pytest

_RUFF_ENTRIES = 3


def _a_link(_path: Path) -> bool:
    return True


def test_a_file_name_is_a_ratchet_kind_or_nothing() -> None:
    """The four kinds by name; a README and a source file are not ratchet state."""
    assert kinds.kind_of("ratchet-preview.txt") == "preview"
    assert kinds.kind_of("ruff-baseline.json") == "baseline"
    assert kinds.kind_of("public_ratchet_baseline.txt") == "baseline"
    assert kinds.kind_of("debt-ledger.json") == "debt"
    assert kinds.kind_of("debtplan.json") is None
    assert kinds.kind_of("rebaselines.json") is None
    assert kinds.kind_of("private_symbol_import_allowlist.txt") == "allowlist"
    assert kinds.kind_of("README.md") is None
    assert kinds.kind_of("baseline.py") is None


def test_a_json_baseline_is_weighed_by_its_recorded_counts(tmp_path: Path) -> None:
    """Ruff's file -> rule -> count shape counts entries, not counts; empty is 0, not unread."""
    ruff = tmp_path / "ruff-baseline.json"
    ruff.write_text('{"a.py": {"ANN001": 3, "D103": 19}, "b.py": {"E501": 2}}', encoding="utf-8")
    empty = tmp_path / "debt-ledger.json"
    empty.write_text("{}", encoding="utf-8")
    listed = tmp_path / "exit-baseline.json"
    listed.write_text('["x", "y", "z"]', encoding="utf-8")
    assert kinds.value_of(ruff) == _RUFF_ENTRIES
    assert kinds.value_of(empty) == 0
    assert kinds.value_of(listed) == len(["x", "y", "z"])


def test_an_empty_string_or_false_leaf_counts_nothing_and_a_numeric_zero_still_counts(
    tmp_path: Path,
) -> None:
    """W1979: module -> first error or empty (empty means it compiles); false is no debt too."""
    codon = tmp_path / "codon-baseline.json"
    codon.write_text(
        '{"a": "", "b": "SyntaxError", "c": false, "d": true, "e": 0}', encoding="utf-8"
    )
    assert kinds.value_of(codon) == len(["SyntaxError", True, 0])


def test_a_text_baseline_counts_entries_not_blanks_or_comments(tmp_path: Path) -> None:
    """One entry per line; a blank line and a # comment record nothing."""
    text = tmp_path / "public_ratchet_baseline.txt"
    text.write_text("# header\n\na::b\nc::d\n", encoding="utf-8")
    assert kinds.value_of(text) == len(["a::b", "c::d"])
    (tmp_path / "ratchet-preview.txt").write_text("", encoding="utf-8")
    assert kinds.value_of(tmp_path / "ratchet-preview.txt") == 0


def test_a_file_that_cannot_be_read_is_unread_never_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken baseline must not read as paid-down debt; a link and a missing file are unread."""
    broken = tmp_path / "ruff-baseline.json"
    broken.write_text("{not json", encoding="utf-8")
    assert kinds.value_of(broken) is None
    assert kinds.value_of(tmp_path / "absent-baseline.json") is None
    fine = tmp_path / "fine-baseline.json"
    fine.write_text("{}", encoding="utf-8")
    assert kinds.value_of(fine) == 0
    monkeypatch.setattr(Path, "is_symlink", _a_link)
    assert kinds.value_of(fine) is None


_RUFF_SUM = 3 + 19 + 2


def test_only_a_file_rule_count_baseline_has_a_sum(tmp_path: Path) -> None:
    """W1922: ruff's shape sums its counts; line-number shapes, lists and empty files do not."""
    shaped = tmp_path / "ruff-baseline.json"
    shaped.write_text('{"a.py": {"ANN001": 3, "D103": 19}, "b.py": {"E501": 2}}', encoding="utf-8")
    assert kinds.sum_of(shaped) == _RUFF_SUM
    refused = {
        "flat-baseline.json": '{"a.py": 3}',
        "list-baseline.json": "[1, 2]",
        "negative-baseline.json": '{"a.py": {"X": -1}}',
        "boolean-baseline.json": '{"a.py": {"X": true}}',
        "text-baseline.json": '{"a.py": {"X": "3"}}',
        "empty-baseline.json": "{}",
        "hollow-baseline.json": '{"a.py": {}}',
        "broken-baseline.json": "{nope",
    }
    for name, body in refused.items():
        (tmp_path / name).write_text(body, encoding="utf-8")
        assert kinds.sum_of(tmp_path / name) is None, name
    plain = tmp_path / "public_ratchet_baseline.txt"
    plain.write_text("a::b\n", encoding="utf-8")
    assert kinds.sum_of(plain) is None

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A mypy baseline kept as one file per module reads as the one object (W2190, github:R212).

⚑ THE CONTROLS: a file key in two parts is refused, a part that is not an object or does not parse
reads as no baseline, and a directory with no part is no baseline either.
"""

from pathlib import Path

from mikemol.hooks import baselinedir

_A = '{"src/a.py": {"E1": 2}}'
_B = '{"src/b.py": {"E2": 1}}'
_BOTH = '{"src/a.py": {"E1": 2}, "src/b.py": {"E2": 1}}'


def test_parts_union_into_one_baseline_and_a_duplicate_key_or_a_bad_part_reads_as_none() -> None:
    """The merge is the union; two parts naming one file, or a non-object, or no part, is None."""
    assert baselinedir.merge([("a.json", _A), ("b.json", _B)]) == _BOTH
    assert baselinedir.merge([("a.json", _A), ("again.json", _A)]) is None
    assert baselinedir.merge([("a.json", "[1]")]) is None
    assert baselinedir.merge([("a.json", "not json")]) is None
    assert baselinedir.merge([]) is None


def test_a_directory_is_read_in_name_order_and_an_absent_or_empty_one_is_no_baseline(
    tmp_path: Path,
) -> None:
    """Parts are read by name and merged; no directory and no part both give None."""
    folder = tmp_path / baselinedir.DIR
    assert baselinedir.read(folder) is None
    folder.mkdir()
    assert baselinedir.read(folder) is None
    (folder / "b.json").write_text(_B, encoding="utf-8")
    (folder / "a.json").write_text(_A, encoding="utf-8")
    assert baselinedir.read(folder) == _BOTH

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Dead bytes mean what deleting a base returns: the exclusive bytes btrfs reports (W1664)."""

import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.buildtel import cachebytes

_NOW = "2026-10-19T00:00:00Z"
_BLOCKS = 100
_SMALL_EXCLUSIVE = 7
_BIG_EXCLUSIVE = 40
_DU = (
    "     Total   Exclusive  Set shared  Filename\n"
    "18357645312  4481032192  9620033536  /var/cache/bazel-mikemol/3efeb\n"
)
_EXCLUSIVE = 4481032192


def _run_du(_argv: object) -> tuple[int, str, str]:
    return 0, _DU, ""


def _run_failed(_argv: object) -> tuple[int, str, str]:
    return 1, "", "ERROR: not a btrfs filesystem"


def _run_missing(_argv: object) -> tuple[int, str, str]:
    msg = "btrfs"
    raise FileNotFoundError(msg)


def _run_header_only(_argv: object) -> tuple[int, str, str]:
    return 0, _DU.splitlines()[0] + "\n", ""


def _base(root: Path, name: str, workspace: str) -> None:
    (root / name / "execroot").mkdir(parents=True)
    (root / name / cachebytes.NAME_FILE).write_text(workspace + "\n", encoding="utf-8")


def test_the_exclusive_column_is_read_from_the_last_line() -> None:
    """Total, Exclusive, Set shared: the second figure is what no other file shares."""
    assert cachebytes.exclusive_bytes(Path("x"), _run_du) == _EXCLUSIVE


def test_a_failed_missing_or_empty_answer_is_unknown_not_zero() -> None:
    """A filesystem the tool cannot ask must read as None, never as nothing to free."""
    assert cachebytes.exclusive_bytes(Path("x"), _run_failed) is None
    assert cachebytes.exclusive_bytes(Path("x"), _run_missing) is None
    assert cachebytes.exclusive_bytes(Path("x"), _run_header_only) is None


def test_rows_sort_by_what_deletion_frees_not_by_blocks(tmp_path: Path) -> None:
    """The biggest block count is mostly shared, so the smaller base frees more."""
    _base(tmp_path, "shared", str(tmp_path / "gone1"))
    _base(tmp_path, "owned", str(tmp_path / "gone2"))

    def size(_path: Path) -> int:
        return _BLOCKS

    def exclusive(path: Path) -> int | None:
        return _SMALL_EXCLUSIVE if path.name == "shared" else _BIG_EXCLUSIVE

    names = [Path(r.path).name for r in cachebytes.output_rows(tmp_path, size, _NOW, exclusive)]
    assert names == ["owned", "shared"]


def test_a_row_without_exclusive_falls_back_to_blocks() -> None:
    """Where btrfs cannot answer, the block count stands in and the field says None."""
    row = cachebytes.Row("output_base", "p", "w", live=False, size=_BLOCKS, measured_at=_NOW)
    parsed = cast("dict[str, object]", json.loads(row.as_json()))
    assert row.freed() == _BLOCKS
    assert parsed["exclusive"] is None


def test_the_dead_summary_sums_what_deletion_frees(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both a blocks total and a freed total, the freed one over exclusive bytes only."""
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    root = tmp_path / "bases"
    _base(root, "dead", str(tmp_path / "gone"))
    _base(root, "live", str(tmp_path))
    (tmp_path / ".bazelrc").write_text(f"startup --output_user_root={root}\n", encoding="utf-8")

    def size(_path: Path) -> int:
        return _BLOCKS

    def exclusive(_path: Path) -> int | None:
        return _SMALL_EXCLUSIVE

    assert cachebytes.main([str(tmp_path)], size, exclusive) == 0
    lines = capsys.readouterr().out.splitlines()
    summary = cast("dict[str, object]", json.loads(lines[-1]))
    assert summary["bytes"] == _BLOCKS
    assert summary["freed"] == _SMALL_EXCLUSIVE

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cache measure reads where bazel writes, names each base's workspace, and deletes nothing."""

import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.buildtel import cachebytes

_NOW = "2026-10-18T00:00:00Z"
_TEN = 10
_FILE_BYTES = 5000
_CEILING = 100_000


def _fixed(_path: Path) -> int:
    return _TEN


def _base(root: Path, name: str, workspace: str | None) -> Path:
    base = root / name
    (base / "execroot").mkdir(parents=True)
    if workspace is not None:
        (base / cachebytes.NAME_FILE).write_text(workspace + "\n", encoding="utf-8")
    return base


def test_a_base_whose_workspace_is_gone_is_dead_and_one_that_exists_is_live(tmp_path: Path) -> None:
    """A removed worktree leaves its base behind: its recorded workspace no longer exists."""
    here = tmp_path / "ws"
    here.mkdir()
    _base(tmp_path, "aaa", str(here))
    _base(tmp_path, "bbb", str(tmp_path / "removed-worktree"))
    rows = {Path(r.path).name: r.live for r in cachebytes.output_rows(tmp_path, _fixed, _NOW)}
    assert rows == {"aaa": True, "bbb": False}


def test_a_base_that_names_no_workspace_is_unknown_never_dead(tmp_path: Path) -> None:
    """No name is no verdict: only a base that names a missing workspace is called dead."""
    _base(tmp_path, "ccc", None)
    (row,) = cachebytes.output_rows(tmp_path, _fixed, _NOW)
    assert row.live is None
    assert not row.workspace


def test_a_directory_without_an_execroot_is_not_a_base(tmp_path: Path) -> None:
    """The install dir bazel keeps beside the bases is not one of them."""
    (tmp_path / "install").mkdir()
    assert cachebytes.output_rows(tmp_path, _fixed, _NOW) == []


def test_rows_come_largest_first(tmp_path: Path) -> None:
    """The consumer that grew is the first line a reader sees."""
    _base(tmp_path, "small", None)
    _base(tmp_path, "big", None)

    def size(path: Path) -> int:
        return _TEN if path.name == "big" else 1

    names = [Path(r.path).name for r in cachebytes.output_rows(tmp_path, size, _NOW)]
    assert names == ["big", "small"]


def test_the_bazelrc_option_is_read_with_the_later_file_winning(tmp_path: Path) -> None:
    """The user's file is read last, as bazel resolves it, and a missing file is skipped."""
    repo = tmp_path / "repo.rc"
    user = tmp_path / "user.rc"
    repo.write_text("startup --output_user_root=/repo/root\nbuild --x=1\n", encoding="utf-8")
    user.write_text("startup --output_user_root=/user/root\n", encoding="utf-8")
    assert cachebytes.option([repo, user], "output_user_root") == Path("/user/root")
    assert cachebytes.option([repo, tmp_path / "none.rc"], "output_user_root") == Path("/repo/root")
    assert cachebytes.option([repo], "disk_cache") is None


def test_the_disk_walk_counts_blocks_under_the_root_only(tmp_path: Path) -> None:
    """A file counts by its blocks, a nested one is reached, a missing path is nothing."""
    inside = tmp_path / "tree" / "deep"
    inside.mkdir(parents=True)
    (inside / "f").write_bytes(b"x" * _FILE_BYTES)
    (tmp_path / "outside").write_bytes(b"y" * _CEILING * 5)
    assert _FILE_BYTES <= cachebytes.disk_bytes(tmp_path / "tree") < _CEILING
    assert cachebytes.disk_bytes(tmp_path / "missing") == 0


def test_main_prints_a_row_per_consumer_and_the_dead_total(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rows, then one summary whose bytes are the dead bases only."""
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    root = tmp_path / "bases"
    _base(root, "dead", str(tmp_path / "gone"))
    _base(root, "live", str(tmp_path))
    (tmp_path / ".bazelrc").write_text(f"startup --output_user_root={root}\n", encoding="utf-8")

    def unknown(_path: Path) -> int | None:
        return None

    assert cachebytes.main([str(tmp_path)], _fixed, unknown) == 0
    lines = capsys.readouterr().out.splitlines()
    rows = [cast("dict[str, object]", json.loads(line)) for line in lines]
    assert rows[-1]["kind"] == "dead_output_bases"
    assert rows[-1]["bytes"] == _TEN
    assert {r["live"] for r in rows[:-1]} == {True, False}
    assert cachebytes.main(["--x"]) == cachebytes.EXIT_USAGE

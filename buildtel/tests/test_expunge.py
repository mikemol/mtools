# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Only a dead base with no running server is removed, dry by default, largest first (W1656)."""

import os
from pathlib import Path

import pytest

from mikemol.buildtel import cachebytes, expunge

_NOW = "2026-10-19T00:00:00Z"
_SMALL = 5
_BIG = 50
_TWO = 2
_THREE = 3
_STALE_PID = 2**22 + 5


def _base(root: Path, name: str, workspace: str | None, *, pid: int | None = None) -> Path:
    base = root / name
    (base / "execroot").mkdir(parents=True)
    if workspace is not None:
        (base / cachebytes.NAME_FILE).write_text(workspace + "\n", encoding="utf-8")
    if pid is not None:
        (base / "server").mkdir()
        (base / expunge.PID_FILE).write_text(str(pid), encoding="utf-8")
    return base


def _rows(root: Path, sizes: dict[str, int] | None = None) -> list[cachebytes.Row]:
    wanted = sizes or {}

    def exclusive(path: Path) -> int | None:
        return wanted.get(path.name, _SMALL)

    def blocks(_path: Path) -> int:
        return 0

    return cachebytes.output_rows(root, blocks, _NOW, exclusive)


def _world(tmp_path: Path) -> Path:
    root = tmp_path / "bases"
    live = tmp_path / "live-workspace"
    live.mkdir()
    _base(root, "dead-big", str(tmp_path / "gone1"))
    _base(root, "dead-small", str(tmp_path / "gone2"))
    _base(root, "live", str(live))
    _base(root, "nameless", None)
    _base(root, "dead-running", str(tmp_path / "gone3"), pid=os.getpid())
    _base(root, "dead-stale", str(tmp_path / "gone4"), pid=_STALE_PID)
    return root


def test_only_dead_bases_with_no_running_server_are_removed_largest_first(tmp_path: Path) -> None:
    """Live, nameless and server-running bases are kept, each with its reason."""
    root = _world(tmp_path)
    steps = expunge.plan(_rows(root, {"dead-big": _BIG}))
    removed = [Path(s.row.path).name for s in steps if s.action == "remove"]
    assert removed == ["dead-big", "dead-small", "dead-stale"]
    kept = {Path(s.row.path).name: s.reason for s in steps if s.action == "keep"}
    assert kept["live"] == "its workspace exists"
    assert kept["nameless"] == "it names no workspace"
    assert "server" in kept["dead-running"]
    assert [s.action for s in steps] == ["remove"] * _THREE + ["keep"] * _THREE


def test_a_dry_run_names_what_would_go_and_removes_nothing(tmp_path: Path) -> None:
    """WOULD REMOVE lines and a total, every directory still there."""
    root = _world(tmp_path)
    lines = expunge.run(root, expunge.plan(_rows(root)), write=False)
    assert sum(line.startswith("WOULD REMOVE") for line in lines) == _THREE
    assert lines[-1].startswith("would remove 3 base(s)")
    assert all(p.is_dir() for p in root.iterdir())


def test_write_removes_read_only_trees_and_leaves_the_live_ones(tmp_path: Path) -> None:
    """A bazel-style read-only tree goes, the live base and the running one stay."""
    root = _world(tmp_path)
    deep = root / "dead-big" / "execroot" / "deep"
    deep.mkdir()
    (deep / "file").write_text("x", encoding="utf-8")
    deep.chmod(0o500)
    lines = expunge.run(root, expunge.plan(_rows(root)), write=True)
    assert not (root / "dead-big").exists()
    assert not (root / "dead-small").exists()
    assert (root / "live").is_dir()
    assert (root / "dead-running").is_dir()
    assert lines[-1].startswith("removed 3 base(s)")


def test_a_failed_removal_is_said_and_the_rest_go_on(tmp_path: Path) -> None:
    """One base that cannot be removed does not stop the others."""
    root = _world(tmp_path)
    steps = expunge.plan(_rows(root, {"dead-big": _BIG}))

    def remove(path: Path) -> None:
        if path.name == "dead-big":
            msg = "busy"
            raise OSError(msg)
        expunge.remove_tree(path)

    lines = expunge.run(root, steps, write=True, remove=remove)
    assert "FAILED dead-big: busy" in lines
    assert (root / "dead-big").is_dir()
    assert not (root / "dead-small").exists()
    assert lines[-1].startswith("removed 2 base(s)")


def test_a_row_that_is_not_a_base_under_the_root_is_never_removed(tmp_path: Path) -> None:
    """The guard re-checks the path under write, so a stray row cannot reach elsewhere."""
    root = tmp_path / "bases"
    root.mkdir()
    elsewhere = _base(tmp_path / "other", "dead", str(tmp_path / "gone"))
    stray = _rows(elsewhere.parent)
    lines = expunge.run(root, expunge.plan(stray), write=True)
    assert elsewhere.is_dir()
    assert any(line.startswith("KEEP dead: it is not a base directly under") for line in lines)


def test_main_reads_the_root_from_bazelrc_and_needs_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A usage error without a root or with a flag; a dry run prints the plan."""
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    assert expunge.main([str(tmp_path)]) == expunge.EXIT_USAGE
    assert expunge.main(["--x"]) == expunge.EXIT_USAGE
    root = _world(tmp_path)
    (tmp_path / ".bazelrc").write_text(f"startup --output_user_root={root}\n", encoding="utf-8")
    assert expunge.main([str(tmp_path)], lambda _p: _SMALL) == 0
    assert "would remove 3 base(s)" in capsys.readouterr().out

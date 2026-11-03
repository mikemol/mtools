# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The retired list only grows: a tombstone HEAD holds may not vanish or change (W1963).

⚑ `git` IS A HOST TOOL taken from PATH, and each case builds its own repository in `tmp_path` with
the caller's `GIT_*` environment removed, as `test_remap` does.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import pytest
from mikemol.procrun.proc import capture

from mikemol.ratchet import cli, declaration

if TYPE_CHECKING:
    from pathlib import Path

CLEAN = 0
REFUSED = 1
UNREADABLE = 2

_GONE: dict[str, str] = {"path": "old.json", "reason": "paid-to-zero-and-removed", "sha": "abc123"}
_MOVED: dict[str, str] = {
    "path": "was.json",
    "reason": declaration.RENAMED,
    "sha": "def456",
    "to": "now.json",
}
_NEW: dict[str, str] = {"path": "newer.json", "reason": "paid-to-zero-and-removed", "sha": "999999"}


@pytest.fixture()
def no_ambient_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every case blind to any git that is running THIS suite."""
    for key in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(key)


pytestmark = pytest.mark.usefixtures("no_ambient_git")


def _git(root: Path, *args: str) -> None:
    proc = capture(["git", "-C", str(root), *args])
    assert proc.returncode == 0, f"git {' '.join(args)} failed: {proc.stderr.strip()}"


def _declare(root: Path, retired: list[dict[str, str]]) -> None:
    body = {"ratchets": [], "retired": retired}
    (root / declaration.NAME).write_text(json.dumps(body), encoding="utf-8")


def _committed(root: Path, retired: list[dict[str, str]]) -> Path:
    _git(root, "init", "-q")
    _declare(root, retired)
    _git(root, "add", declaration.NAME)
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return root


def test_a_kept_or_extended_list_is_clean(tmp_path: Path) -> None:
    """The positive control: the same list, and the same list plus one, both pass."""
    repo = _committed(tmp_path, [_GONE, _MOVED])
    assert cli.main(["retired", str(repo)]) == CLEAN
    _declare(repo, [_MOVED, _GONE, _NEW])
    assert cli.main(["retired", str(repo)]) == CLEAN


def test_a_vanished_or_edited_tombstone_is_refused_and_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Dropping one, or rewriting its sha, refuses; the line names the path."""
    repo = _committed(tmp_path, [_GONE, _MOVED])
    _declare(repo, [_MOVED])
    assert cli.main(["retired", str(repo)]) == REFUSED
    assert "old.json" in capsys.readouterr().out
    _declare(repo, [_GONE, {**_MOVED, "sha": "000000"}])
    assert cli.main(["retired", str(repo)]) == REFUSED
    assert "was.json" in capsys.readouterr().out


def test_a_deleted_declaration_loses_every_tombstone(tmp_path: Path) -> None:
    """The file removed is the whole list removed."""
    repo = _committed(tmp_path, [_GONE])
    (repo / declaration.NAME).unlink()
    assert cli.main(["retired", str(repo)]) == REFUSED


def test_a_revision_with_no_declaration_holds_nothing_to_lose(tmp_path: Path) -> None:
    """Adding the first declaration is never a loss."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    _git(tmp_path, "add", "x.txt")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    _declare(tmp_path, [_GONE])
    assert cli.main(["retired", str(tmp_path)]) == CLEAN


def test_a_head_declaration_that_is_not_json_is_not_read_as_an_empty_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """HEAD's own copy broken is CANNOT-READ too: an empty list would let everything go."""
    _git(tmp_path, "init", "-q")
    (tmp_path / declaration.NAME).write_text("{nope", encoding="utf-8")
    _git(tmp_path, "add", declaration.NAME)
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    _declare(tmp_path, [_GONE])
    assert cli.main(["retired", str(tmp_path)]) == UNREADABLE
    assert "cannot be read" in capsys.readouterr().err


def test_an_unreadable_declaration_is_not_a_clean_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A working file that is not JSON is CANNOT-READ, never read as an empty list."""
    repo = _committed(tmp_path, [_GONE])
    (repo / declaration.NAME).write_text("{nope", encoding="utf-8")
    assert cli.main(["retired", str(repo)]) == UNREADABLE
    assert "cannot be read" in capsys.readouterr().err

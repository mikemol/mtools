# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `licenses` lists the dists that do not ship their license, and fixes them (W1206).

⚑ THE DRY RUN IS THE CONTROL: without `--write` nothing on disk changes, and the exit says a dist
needs it. ⚑ THE ALREADY-RIGHT DIST AND THE LINK ARE THE OTHER CONTROLS: a dist with the file, the
line and a new enough backend is reported `ok` and not touched, and a `LICENSE` that is a symlink
(or a directory that is) is never written through.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import licenses

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_TEXT = "Apache-2.0 text\n"
_PROJECT = (
    '[build-system]\nrequires = ["{backend}", "wheel"]\n'
    '[project]\nname = "{name}"\nlicense = "Apache-2.0"\n{extra}requires-python = ">=3.13"\n'
    "# also built with setuptools>=82 in CI\n"
)
_FILES = 'license-files = ["LICENSE"]\n'
_USAGE = 2
Row = dict[str, object]


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    (root / "LICENSE").write_text(_TEXT, encoding="utf-8")
    return root


def _dist(
    root: Path,
    name: str,
    *,
    text: str | None = None,
    files: bool = False,
    backend: str = "setuptools>=77",
) -> Path:
    dist = root / name
    dist.mkdir()
    extra = _FILES if files else ""
    project = _PROJECT.format(name=name, extra=extra, backend=backend)
    (dist / "pyproject.toml").write_text(project, encoding="utf-8")
    if text is not None:
        (dist / "LICENSE").write_text(text, encoding="utf-8")
    return dist


def _rows(capsys: pytest.CaptureFixture[str]) -> dict[str, Row]:
    lines = capsys.readouterr().out.splitlines()
    rows = [cast("Row", json.loads(line)) for line in lines]
    return {str(r["dist"]): r for r in rows}


def _states(row: Row) -> tuple[str, ...]:
    return tuple(str(row[key]) for key in ("license", "license-files", "backend"))


def test_a_dry_run_names_what_is_missing_changes_nothing_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bare dist and a stale copy are listed; the files on disk are as they were."""
    root = _root(tmp_path)
    bare = _dist(root, "bare", backend="setuptools>=68")
    stale = _dist(root, "stale", text="old\n", files=True)
    assert licenses.run([str(root)]) == 1
    rows = _rows(capsys)
    assert _states(rows["bare"]) == ("missing", "missing", "old")
    assert _states(rows["stale"]) == ("differs", "ok", "ok")
    assert not (bare / "LICENSE").exists()
    assert "license-files" not in (bare / "pyproject.toml").read_text(encoding="utf-8")
    assert "setuptools>=68" in (bare / "pyproject.toml").read_text(encoding="utf-8")
    assert (stale / "LICENSE").read_text(encoding="utf-8") == "old\n"


def test_write_copies_the_license_adds_the_line_and_raises_the_backend(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """After `--write` the bare dist is right, the line sits right after `license =`, exit 0."""
    root = _root(tmp_path)
    bare = _dist(root, "bare", backend="setuptools>=68")
    stale = _dist(root, "stale", text="old\n", files=True)
    assert licenses.run([str(root), "--write"]) == 0
    rows = _rows(capsys)
    assert rows["bare"]["written"] is True
    assert (bare / "LICENSE").read_text(encoding="utf-8") == _TEXT
    assert (stale / "LICENSE").read_text(encoding="utf-8") == _TEXT
    project = (bare / "pyproject.toml").read_text(encoding="utf-8")
    lines = project.splitlines()
    assert lines[lines.index('license = "Apache-2.0"') + 1] == _FILES.strip()
    assert 'requires = ["setuptools>=77", "wheel"]' in lines
    assert "# also built with setuptools>=82 in CI" in lines
    assert licenses.run([str(root)]) == 0


def test_a_backend_at_or_above_the_floor_is_left_alone(tmp_path: Path) -> None:
    """The control for the raise: `setuptools>=82` is not lowered to 77."""
    root = _root(tmp_path)
    dist = _dist(root, "newer", text=_TEXT, files=True, backend="setuptools>=82")
    assert licenses.run([str(root), "--write"]) == 0
    assert "setuptools>=82" in (dist / "pyproject.toml").read_text(encoding="utf-8")


def test_an_already_right_dist_is_ok_and_not_rewritten(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: the file, the line and the backend are right, so nothing is written."""
    root = _root(tmp_path)
    _dist(root, "fine", text=_TEXT, files=True)
    assert licenses.run([str(root), "--write"]) == 0
    row = _rows(capsys)["fine"]
    assert _states(row) == ("ok", "ok", "ok")
    assert row["written"] is False


def test_a_symlinked_license_is_reported_and_never_written_through(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No symlinks: a link is `link`, the target is untouched, and the run still exits 1."""
    root = _root(tmp_path)
    dist = _dist(root, "linked", files=True)
    target = tmp_path / "elsewhere"
    target.write_text("keep\n", encoding="utf-8")
    (dist / "LICENSE").symlink_to(target)
    assert licenses.run([str(root), "--write"]) == 1
    assert _rows(capsys)["linked"]["license"] == "link"
    assert target.read_text(encoding="utf-8") == "keep\n"


def test_a_symlinked_directory_is_not_a_dist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bazel's `bazel-<repo>` link holds a pyproject.toml and must not be listed or written."""
    root = _root(tmp_path)
    real = _dist(root, "real", text=_TEXT, files=True)
    (root / "bazel-root").symlink_to(real, target_is_directory=True)
    assert licenses.run([str(root), "--write"]) == 0
    assert list(_rows(capsys)) == ["real"]


def test_a_root_without_a_license_or_the_wrong_arguments_is_a_usage_error(tmp_path: Path) -> None:
    """Nothing to copy from, and no root at all, each exit 2."""
    assert licenses.run([str(tmp_path)]) == _USAGE
    assert licenses.run([]) == _USAGE

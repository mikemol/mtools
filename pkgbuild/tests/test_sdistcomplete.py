# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the files under tests/ missing from an sdist are named, and nothing else is.

W1230. ⚑ THE CONTROLS: a cache directory is not a tracked file, a file the sdist has beyond the tree
is not a finding, a dist with no tests/ passes, and a long list is cut at eight with a mark.
"""

from __future__ import annotations

import io
import tarfile
from typing import TYPE_CHECKING

from mikemol.pkgbuild import sdistcomplete

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_SHOWN = 8
_MANY = 10


def _tree(root: Path, files: Sequence[str]) -> Path:
    dist = root / "dist"
    for name in files:
        place = dist / name
        place.parent.mkdir(parents=True, exist_ok=True)
        place.write_text("x\n", encoding="utf-8")
    return dist


def _sdist(root: Path, members: Sequence[str]) -> Path:
    path = root / "pkg-0.1.0.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        for name in members:
            info = tarfile.TarInfo(f"pkg-0.1.0/{name}")
            info.size = 2
            archive.addfile(info, io.BytesIO(b"x\n"))
    return path


def test_tracked_test_files_exclude_caches_and_a_missing_directory_is_empty(tmp_path: Path) -> None:
    """Only real files under tests/, in name order; a pycache is not a file of a commit."""
    dist = _tree(
        tmp_path,
        ["tests/conftest.py", "tests/data/a.txt", "tests/__pycache__/x.pyc", "src/mod.py"],
    )
    assert sdistcomplete.tracked_tests(dist) == ["tests/conftest.py", "tests/data/a.txt"]
    assert sdistcomplete.tracked_tests(tmp_path / "nowhere") == []


def test_members_are_read_relative_to_the_single_top_directory(tmp_path: Path) -> None:
    """The leading name-version directory is removed from each member."""
    sdist = _sdist(tmp_path, ["pyproject.toml", "tests/test_a.py"])
    assert sdistcomplete.sdist_members(sdist) == {"pyproject.toml", "tests/test_a.py"}


def test_missing_names_the_tracked_test_files_the_sdist_lacks(tmp_path: Path) -> None:
    """conftest.py is absent from the sdist and named; an extra member is not a finding."""
    dist = _tree(tmp_path, ["tests/conftest.py", "tests/test_a.py"])
    sdist = _sdist(tmp_path, ["tests/test_a.py", "tests/extra.py"])
    assert sdistcomplete.missing(dist, sdist) == ["tests/conftest.py"]


def test_the_verdict_passes_when_nothing_is_missing_and_cuts_a_long_list(tmp_path: Path) -> None:
    """A complete sdist is ok with no detail; a bare one names a count, eight files and the fix."""
    names = [f"tests/data/{n:02d}.txt" for n in range(_MANY)]
    dist = _tree(tmp_path, names)
    assert sdistcomplete.verdict(dist, _sdist(tmp_path, names)) == ("ok", "")
    state, why = sdistcomplete.verdict(dist, _sdist(tmp_path, []))
    assert state == "failed"
    assert why.startswith(f"{_MANY} test file(s)")
    assert names[_SHOWN - 1] in why
    assert names[_SHOWN] not in why
    assert " ..." in why
    assert "graft tests" in why

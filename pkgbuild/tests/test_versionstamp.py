# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a release version is stamped into the [project] table and nowhere else.

W803. ⚑ THE CONTROLS: a `version` key in another table is not touched, a pyproject with no
static version (or no [project]) is reported and left as it was, and a version with a local part
or a letter is not a plain release segment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pkgbuild import versionstamp

if TYPE_CHECKING:
    from pathlib import Path

_TWO = 2
_TEXT = (
    '[build-system]\nrequires = ["setuptools"]\n[project]\nname = "x"\nversion = "0.1.0"\n'
    'description = "d"\n[tool.other]\nversion = "9.9.9"\n'
)


def test_only_a_plain_release_segment_is_a_valid_version() -> None:
    """Digits and dots pass; a local part, a suffix, an empty string and a letter do not."""
    assert versionstamp.valid("0.0.1234")
    assert versionstamp.valid("1")
    assert not versionstamp.valid("0.0.1+gabc")
    assert not versionstamp.valid("0.0.1rc1")
    assert not versionstamp.valid("")
    assert not versionstamp.valid("v1.2")


def test_the_project_version_is_replaced_and_another_tables_is_not() -> None:
    """The [project] line changes; the [tool.other] version keeps its value."""
    new = versionstamp.stamped(_TEXT, "0.0.7")
    assert new is not None
    assert 'version = "0.0.7"' in new
    assert 'version = "9.9.9"' in new
    assert 'version = "0.1.0"' not in new
    assert new.count("version =") == _TWO


def test_a_pyproject_without_a_static_project_version_is_left_alone() -> None:
    """No [project], or [project] with no version line (a dynamic one), gives None."""
    assert versionstamp.stamped('[tool.other]\nversion = "1"\n', "0.0.7") is None
    assert versionstamp.stamped('[project]\nname = "x"\ndynamic = ["version"]\n', "0.0.7") is None
    after_table = '[project]\nname = "x"\n[tool.other]\nversion = "1"\n'
    assert versionstamp.stamped(after_table, "0.0.7") is None


def test_a_tree_is_stamped_in_place_and_the_unstampable_are_named(tmp_path: Path) -> None:
    """Two dists take the version on disk; the one with a dynamic version is named and unchanged."""
    good, odd = tmp_path / "good", tmp_path / "odd"
    for folder, text in ((good, _TEXT), (odd, '[project]\nname = "o"\ndynamic = ["version"]\n')):
        folder.mkdir()
        (folder / "pyproject.toml").write_text(text, encoding="utf-8")
    assert versionstamp.stamp_tree([good, odd], "0.0.9") == ["odd"]
    assert 'version = "0.0.9"' in (good / "pyproject.toml").read_text(encoding="utf-8")
    assert "0.0.9" not in (odd / "pyproject.toml").read_text(encoding="utf-8")

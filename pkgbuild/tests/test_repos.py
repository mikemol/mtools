# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the dist-to-repository layout is read, defaulted and refused as stated (W1220).

⚑ THE CONTROLS: no file is the current layout; a dist not named gets the default; two owners in one
file stay two places; a malformed table is refused with its reason and never read as the default.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pkgbuild import repos

if TYPE_CHECKING:
    from pathlib import Path

_TWO_ORGS = """
[default]
owner = "mikemol"
repo = "mtools"

[dist.atomicwrite]
owner = "mikemol-tools"
repo = "atomicwrite"

[dist.fence]
owner = "other-org"
repo = "fence"
"""


def _layout(text: str) -> repos.Layout:
    parsed = repos.parse(text)
    assert isinstance(parsed, repos.Layout), parsed
    return parsed


def test_no_file_is_the_current_layout() -> None:
    """With no path every dist is in mikemol/mtools."""
    layout = repos.load(None)
    assert isinstance(layout, repos.Layout)
    assert layout.place("anything").slug() == "mikemol/mtools"


def test_a_dist_is_found_by_name_and_an_unnamed_one_gets_the_default() -> None:
    """Two orgs in one file: each named dist has its own place, the rest the default."""
    layout = _layout(_TWO_ORGS)
    assert layout.place("atomicwrite") == repos.Place("mikemol-tools", "atomicwrite")
    assert layout.place("fence").slug() == "other-org/fence"
    assert layout.place("grade").slug() == "mikemol/mtools"


def test_the_distinct_places_are_listed_once_in_first_seen_order() -> None:
    """Four dists, three repositories: the repeated default is listed once."""
    layout = _layout(_TWO_ORGS)
    got = layout.places(["grade", "atomicwrite", "bibparse", "fence"])
    assert [p.slug() for p in got] == [
        "mikemol/mtools",
        "mikemol-tools/atomicwrite",
        "other-org/fence",
    ]


def test_a_file_without_a_default_table_keeps_the_current_default() -> None:
    """Only exceptions listed: the default is still mikemol/mtools."""
    layout = _layout('[dist.fence]\nowner = "o"\nrepo = "r"\n')
    assert layout.place("grade") == repos.DEFAULT


def test_a_malformed_file_is_refused_with_its_reason() -> None:
    """Not TOML, a table without a repo, and a non-table dist or default are each refused."""
    assert "not TOML" in str(repos.parse("[[["))
    assert "needs a non-empty owner and repo" in str(repos.parse('[default]\nowner = "o"\n'))
    assert "[dist.x]" in str(repos.parse('[dist.x]\nowner = ""\nrepo = "r"\n'))
    assert "[dist] is not a table" in str(repos.parse("dist = 3\n"))
    assert "[default] is not a table" in str(repos.parse("default = 3\n"))


def test_an_unreadable_file_is_refused_not_defaulted(tmp_path: Path) -> None:
    """A path that does not exist is a reason, never the default layout."""
    got = repos.load(tmp_path / "absent.toml")
    assert isinstance(got, str)
    assert "cannot read" in got


def test_a_file_is_read_from_disk(tmp_path: Path) -> None:
    """The text of a real file is parsed."""
    source = tmp_path / "repos.toml"
    source.write_text(_TWO_ORGS, encoding="utf-8")
    got = repos.load(source)
    assert isinstance(got, repos.Layout)
    assert got.place("fence").owner == "other-org"

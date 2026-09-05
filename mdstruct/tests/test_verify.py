# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The self-asserting contract's own witnesses — both arms, and the contract's own F-arm.

⚑⚑ A SELFTEST THAT ONLY EVER PASSES IS THE DEFECT IT EXISTS TO CATCH. These cases assert that
the contract FIRES on known-defective shapes as well as staying silent on clean ones, and that
the shape table cannot lie in either direction without the selftest failing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import verify

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc


def _doc(tmp_path: Path, heading: str) -> Path:
    path = tmp_path / "fixture.md"
    path.write_text(f"# A\n\n## {heading}\n\nx\n", encoding="utf-8")
    return path


def test_a_plain_heading_reaches_the_section_list(tmp_path: Path) -> None:
    """The P-arm. Without it, a contract reporting EVERYTHING missing would also pass."""
    assert verify.missing_headings(_doc(tmp_path, "B leg")) == []


def test_an_apostrophe_heading_is_reported_swallowed(tmp_path: Path) -> None:
    """⚑ The defect four repos hit while writing possessive prose, as a standing witness."""
    missing = verify.missing_headings(_doc(tmp_path, "B's leg"))
    assert [m.text for m in missing] == ["B's leg"]


def test_a_link_heading_is_reported_swallowed(tmp_path: Path) -> None:
    """⚑ Found by ENUMERATING heading shapes rather than by being bitten — unknown until then."""
    missing = verify.missing_headings(_doc(tmp_path, "B [x](y) leg"))
    assert [m.text for m in missing] == ["B [x](y) leg"]


def test_a_heading_inside_a_fence_is_not_a_heading(tmp_path: Path) -> None:
    """⚑ The independent witness borrows exactly one fact from the parser, and this is it."""
    path = tmp_path / "fenced.md"
    path.write_text("# A\n\n```\n# not a heading\n```\n\nx\n", encoding="utf-8")
    assert verify.missing_headings(path) == []


def test_the_source_scan_does_not_use_this_tools_parser() -> None:
    """⚑ A checker sharing the defect it checks for cannot detect it. Raw text in, headings out."""
    found = verify.source_headings("# A\n\n## B's leg\n\nx\n")
    assert found == [(1, 1, "A"), (3, 2, "B's leg")]


def test_the_selftest_holds_both_arms_over_the_shape_space() -> None:
    """The contract, run as shipped."""
    assert verify.selftest() == []


@pytest.mark.parametrize(
    ("shape", "arm"),
    [(("apostrophe", "B's leg", True), "P-arm"),
     (("plain", "B leg", False), "F-arm")])
def test_the_selftest_fires_when_the_shape_table_lies(
        monkeypatch: pytest.MonkeyPatch,
        shape: tuple[str, str, bool], arm: str) -> None:
    """⚑⚑ THE CONTRACT'S OWN F-ARM. A shape table asserting the opposite of the truth must FAIL.

    Without this, the selftest could be green because it is aimed at the wrong predicate — the
    class this repo has now paid for twice in one day.
    """
    monkeypatch.setattr(verify, "_SHAPES", (shape,))
    failures = verify.selftest()
    assert len(failures) == 1
    assert failures[0].startswith(arm)

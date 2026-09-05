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

from mikemol.mdstruct import ast, verify

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


def test_an_apostrophe_heading_reaches_the_section_list(tmp_path: Path) -> None:
    """A heading carrying an ASCII apostrophe reaches the section list.

    ⚑ The defect four repos hit while writing possessive prose: pandoc smart-quotes `'` to
    U+2019, which the old hand-maintained markup model did not know, so the keys never matched.
    """
    assert verify.missing_headings(_doc(tmp_path, "B's leg")) == []


def test_a_link_heading_reaches_the_section_list(tmp_path: Path) -> None:
    """⚑ Found by ENUMERATING heading shapes rather than by being bitten — unknown until then."""
    assert verify.missing_headings(_doc(tmp_path, "B [x](y) leg")) == []


def test_a_hash_line_that_is_not_a_heading_does_not_shift_the_pairing(tmp_path: Path) -> None:
    """A `#` line that is not a heading must not shift the pairing.

    ⚑⚑ The regression the CONTRACT caught, not review. Rendering the candidate lines in one batch
    made the result positional, and `#no-space` is a paragraph rather than a heading — so a bare
    batch returned fewer headings than it was given and every later pairing shifted by one.
    """
    path = tmp_path / "shift.md"
    path.write_text("# A\n\n#not a heading\n\n## B leg\n\nx\n", encoding="utf-8")
    assert verify.missing_headings(path) == []


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


def test_the_selftest_fires_when_a_shape_row_claims_the_opposite(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑⚑ THE CONTRACT'S OWN F-ARM. A row asserting the opposite of the truth must FAIL.

    ⚑ THE P-ARM SIDE IS STUBBED, DELIBERATELY, AND THAT IS A RESULT RATHER THAN A SHORTCUT. It
    needs a shape the tool CANNOT reach, and after the anchor repair there is no such shape — the
    reconciliation asks pandoc instead of modelling it, so any line pandoc calls a heading is
    found. So the reachability answer is stubbed to exercise the ASSERTION, and the day a real
    unreachable shape exists it belongs in `_SHAPES` as a standing witness, not here.
    """
    monkeypatch.setattr(verify, "_SHAPES", (("plain", "B leg", False),))
    failures = verify.selftest()
    assert len(failures) == 1
    assert failures[0].startswith("F-arm")

    monkeypatch.setattr(verify, "_SHAPES", (("stubbed", "B leg", True),))
    def _always_missing(_path: Path) -> list[verify.Missing]:
        return [verify.Missing(line=3, level=2, text="B leg")]

    monkeypatch.setattr(verify, "missing_headings", _always_missing)
    failures = verify.selftest()
    assert len(failures) == 1
    assert failures[0].startswith("P-arm")


def test_a_source_line_renders_to_exactly_what_its_document_header_renders_to() -> None:
    """⚑⚑ THE REPAIR ITSELF: reconciliation asks pandoc rather than modelling it.

    The previous anchor key stripped a three-character tuple whose own comment warned against
    growing it "into a grammar the renderer does not share". It did not grow, and that was the
    defect — pandoc also smart-quotes and unwraps links. Rendering the raw line through the SAME
    pipeline cannot drift from that pipeline, by construction.
    """
    raw = ["## B's leg", "## C [l](u) leg", "## D ![i](u) leg", "## E `c` leg", "## F *em* leg"]
    assert ast.render_headings(raw) == [
        "B\u2019s leg", "C l leg", "D i leg", "E c leg", "F em leg"]


def test_render_headings_returns_one_entry_per_input() -> None:
    """Every input line gets exactly one entry back.

    ⚑ The positional contract `strict=True` in spans.py depends on. A non-heading holds its slot
    with an empty string rather than dropping out and shifting every later pairing.
    """
    assert ast.render_headings(["# A", "#not a heading", "## B leg"]) == ["A", "", "B leg"]

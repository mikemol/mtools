# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The self-asserting contract's own witnesses — both arms, and the contract's own F-arm.

⚑⚑ A SELFTEST THAT ONLY EVER PASSES IS THE DEFECT IT EXISTS TO CATCH. These cases assert that
the contract FIRES on known-defective shapes as well as staying silent on clean ones, and that
the shape table cannot lie in either direction without the selftest failing.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import ast, cli, verify

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


_RC_USAGE = 2


def _run_cli(*args: str) -> int:
    """Invoke the CLI's verify mode in-process.

    ⚑⚑ THE `sys.argv` MUTATION IS GONE. This helper used to assign the global, call `main()`, and
    restore in `finally` — a workaround for `main` reading `sys.argv` directly. It worked, and it
    put the correctness of every case in this module behind one `finally`: a case that forgot the
    restore would poison its neighbours, and nothing would catch that.

    Returns:
        the exit code `cli.main()` produced for this invocation.

    """
    return cli.main(["mdstruct", "verify", *args])


def test_verify_takes_many_paths_without_repeating_the_first(tmp_path: Path) -> None:
    """⚑⚑⚑ SLICING `argv[2:]` VERIFIED THE FIRST FILE TWICE, AND A DUPLICATE PASS IS INVISIBLE.

    `verify` grew a multi-path form so a caller pays one interpreter startup rather than one per
    file. The first implementation built its list as `[path, *argv[2:]]` — but `argv[2:]` already
    CONTAINS that path, so a single-path invocation checked the same document twice and printed the
    same green line twice. ⚑ MEASURED on the single-path arm, which is the only reason it was
    caught: in a green run a duplicate PASS looks exactly like a pass.
    """
    good = tmp_path / "good.md"
    good.write_text("# A\n\ntext\n\n## B plain\n\nmore\n", encoding="utf-8")

    out = io.StringIO()
    with redirect_stdout(out):
        rc = _run_cli(str(good))
    assert rc == 0
    assert out.getvalue().count(str(good)) == 1, "a single path must be verified exactly once"


def test_verify_reports_a_failure_that_a_later_success_would_mask(tmp_path: Path) -> None:
    """⚑⚑ A BATCHED CHECK THAT STOPS AT THE FIRST VERDICT IS A GATE THAT REPORTS ONE FILE.

    The multi-path form must verify EVERY path and return the worst verdict, in both orders — a
    failure first, and a failure last behind a success. ⚑ The second is the masking case: returning
    the LAST file's status would let one clean document certify a corrupt one.

    The defective fixture is a heading swallowed by an HTML block, chosen because the shape table
    carries no known-unreachable rows any more — an earlier fixture built from the apostrophe
    defect verified CLEAN, since that defect has been repaired, and would have passed these arms
    for the wrong reason.
    """
    good = tmp_path / "good.md"
    good.write_text("# A\n\ntext\n\n## B plain\n\nmore\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("# A\n\n<div>\n\n## B swallowed\n\n</div>\n\n## C plain\n", encoding="utf-8")

    out = io.StringIO()
    with redirect_stdout(out):
        assert _run_cli(str(bad), str(good)) == 1, "a failure first must survive a later success"
        assert _run_cli(str(good), str(bad)) == 1, "a failure LAST must not be masked by the first"
        assert _run_cli(str(good), str(tmp_path / "absent.md")) == _RC_USAGE, (
            "a missing path escalates")


def test_main_takes_its_arguments_rather_than_reading_the_global(tmp_path: Path) -> None:
    """⚑⚑⚑ A FUNCTION THAT READS `sys.argv` CANNOT BE VARIED BY A CASE.

    Its branches are then unreachable except through a workaround every caller must remember.
    cassian reported this shape in their own copies of a shared hook and named the real defect
    precisely: *the captivity is the defect and the raise is its symptom* — reading the global
    means no case can vary the input, so the branch a docstring describes has never been exercised.
    They checked their tree because mtools recorded the finding as owed, and mtools then carried it
    as owed a second time without looking. ⚑ A finding filed outward is not a finding fixed at home.

    ⚑⚑ MEASURED HERE BEFORE FIXING: the raise-shape (`sys.argv.index`) is ABSENT from all 36 source
    files across the four distributions — with a constructed positive control proving the searcher
    can see it — and the CAPTIVITY is present in exactly one place, `cli.main()`.

    ⚑ AND THE SUITE ALREADY CARRIED THE WORKAROUND: `_run_cli` assigns `sys.argv`, calls `main()`,
    and restores in `finally`. It works, and it is what this arm retires — a case that forgets the
    restore poisons its neighbours, and nothing would catch that.
    """
    doc = tmp_path / "clean.markdown"
    doc.write_text("# A\n\ntext\n", encoding="utf-8")

    # ⚑ THE ARGUMENT IS PASSED, NOT PLANTED. With `main` still reading the global, this runs under
    # pytest's own argv and returns the usage code rather than verifying anything.
    saved = sys.argv
    sys.argv = ["pytest", "--not-a-mode"]
    try:
        rc = cli.main(["mdstruct", "verify", str(doc)])
    finally:
        sys.argv = saved

    assert rc == 0, f"verify of a clean document returned {rc} — main did not receive its argv"


def test_main_still_defaults_to_the_global_for_the_console_script(tmp_path: Path) -> None:
    """⚑ THE DEFAULT MUST NOT MOVE, or the installed entry point stops working.

    `[project.scripts]` names `mikemol.mdstruct.cli:main`, and a console script calls it with NO
    arguments. Making `argv` a parameter is only safe if omitting it still reads the global — the
    same discipline as the grader's interpreter default, which was pinned for the same reason.
    """
    doc = tmp_path / "clean.markdown"
    doc.write_text("# A\n\ntext\n", encoding="utf-8")

    saved = sys.argv
    sys.argv = ["mdstruct", "verify", str(doc)]
    try:
        rc = cli.main()
    finally:
        sys.argv = saved

    assert rc == 0, f"main() with no argument returned {rc} — the global default was lost"

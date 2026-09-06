# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The span is the SECTION's, and the container is a chain.

⚑⚑⚑ THE SPAN-NOT-THE-LINE CASE IS THE WHOLE FEATURE. `grep -n` already gives a line number; what
it cannot give is the editable unit around it, which is why the pair was asked for. A version
returning the match's own line as its range would pass a naive reading and deliver nothing over
the tool a structural-query hook already refuses.

⚑⚑ AND THE INNERMOST CONTAINER IS THE EDITABLE ONE. A line inside a `###` is also inside its
`##`; reporting the parent's range would hand back a span far larger than the reader asked about,
and a section rewrite against it would take the sibling subsections too.

⚑ LITERAL BY DEFAULT IS A CORRECTNESS PROPERTY, NOT A CONVENIENCE. A staleness sweep is a
COMPLETENESS tool, and a regex default fails toward FALSE NEGATIVES — the wrong direction for
"did I catch every occurrence".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import grep

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

_FIXTURE = """preamble mentions NEEDLE early

# Top

## Parent

parent body

### Child

child body has NEEDLE here

## Sibling

sibling body has NEEDLE too
"""

# `### Child` runs from its heading to the line before `## Sibling`.
_CHILD_START, _CHILD_END = 9, 12

# The needle appears three times: preamble, child, sibling.
_HITS = 3


# ⚑ CALLED, NOT BARE: the overloaded decorator's bare form collapses this fixture to `Any`.
@pytest.fixture()
def document(doc: Path) -> Path:
    """Write the fixture document."""
    doc.write_text(_FIXTURE, encoding="utf-8")
    return doc


def test_every_occurrence_is_found(document: Path) -> None:
    """The sweep reports each match — what a staleness scan needs."""
    assert len(grep.search(document, "NEEDLE")) == _HITS


def test_the_span_is_the_sections_not_the_matching_line(document: Path) -> None:
    """A hit carries the containing section's range, not the match's own line.

    ⚑ THE FEATURE. Returning the match's line as its range would make this a slower `grep -n` —
    and it would pass any test that only counted hits.
    """
    hit = grep.search(document, "child body")[0]
    assert (hit.start, hit.end) == (_CHILD_START, _CHILD_END)
    assert hit.start < hit.line_no <= hit.end
    assert hit.start != hit.end, "the span collapsed onto one line"


def test_the_container_is_the_innermost_with_the_whole_chain(document: Path) -> None:
    """The container names the full path and ends at the deepest section."""
    container = grep.search(document, "child body")[0].container
    assert "Child" in container
    assert "Parent" in container
    assert container.rindex("Child") > container.rindex("Parent"), "chain is not outermost-first"


def test_a_preamble_match_is_named(document: Path) -> None:
    """A match above the first heading reports a named container.

    ⚑ AN EMPTY CONTAINER READS AS A MISSING MEASUREMENT, where "this is preamble" is a fact.
    """
    assert grep.search(document, "preamble mentions")[0].container == grep.PREAMBLE


def test_a_literal_pattern_is_not_a_regex(document: Path) -> None:
    """The default search treats the pattern literally.

    ⚑ PROSE CONTAINS `.`, `(`, `[` AND `*`. A regex default would make a search for a phrase
    either error or match something else — silently, toward a false negative.
    """
    assert grep.search(document, "NEEDLE.") == []


def test_regex_is_opt_in(document: Path) -> None:
    """A POSITIVE CONTROL for the literal default: `-E` genuinely enables matching."""
    assert grep.search(document, "NEEDLE.", regex=True)


def test_case_folding_is_opt_in(document: Path) -> None:
    """`-i` widens the search and the default does not."""
    assert grep.search(document, "needle") == []
    assert len(grep.search(document, "needle", ignore_case=True)) == _HITS

# --- the routed zero: a literal-mode misfire must not look like a true absence ----------------
#
# ⚑⚑ THE BEHAVIOUR ABOVE WAS ALREADY TESTED AND THE SILENCE WAS NOT. `test_regex_is_opt_in` has
# always passed, and `grep '7\\.0\\.0-'` still reported *no line matches* on a file containing
# `7.0.0-29.29` twice (linux-sources, 2026-09-06). The tests asserted what the mode DOES; nothing
# asserted that a zero produced by the mode is distinguishable from a zero produced by the file.


def test_an_escaped_dot_is_a_regex_tell() -> None:
    r"""`\\.` in a literal pattern is reported: it is what a version or path search looks like."""
    assert grep.regex_tell(r"7\.0\.0-") == "\\."


def test_a_char_class_is_a_regex_tell() -> None:
    """`[` in a literal pattern is reported."""
    assert grep.regex_tell("ver[0-9]") == "["


def test_a_star_quantifier_is_a_regex_tell() -> None:
    """`.*` in a literal pattern is reported."""
    assert grep.regex_tell("foo.*bar") == ".*"


def test_ordinary_prose_is_not_a_regex_tell() -> None:
    """A sentence ending in a full stop is NOT a tell.

    ⚑ THE NEGATIVE ARM IS WHAT KEEPS THE DEFAULT USABLE. A staleness sweep searches prose, prose
    ends in `.`, and a tell that fired on every sentence would train its reader to ignore it —
    which is the same disabling pressure a false-positive gate creates.
    """
    assert not grep.regex_tell("the pin is stale.")


def test_a_bare_dot_is_not_a_regex_tell() -> None:
    """A single `.` is not reported: in literal mode it matches a dot, which is what was meant."""
    assert not grep.regex_tell("7.0.0-29.29")


def test_the_escaped_pattern_still_finds_nothing_in_literal_mode(tmp_path: Path) -> None:
    r"""The defect itself, pinned: `\\.` in literal mode matches a backslash, so the zero is real.

    ⚑ THE REPAIR DOES NOT CHANGE THE DEFAULT and this case says so. `search` still returns [];
    what changed is that the CLI can now say why. A fix that flipped the default would break every
    prose sweep to repair one version search.
    """
    doc = tmp_path / "tell.md"
    doc.write_text("# H\n\nkernel 7.0.0-29.29 here\n", encoding="utf-8")
    assert grep.search(doc, r"7\.0\.0-") == []


def test_the_same_escaped_pattern_matches_under_dash_e(tmp_path: Path) -> None:
    """POSITIVE CONTROL for the case above: `-E` finds what literal mode could not.

    ⚑ Without this arm the case above passes against a `search` that finds nothing at all, which
    is the broken-shut gate one layer down.
    """
    doc = tmp_path / "tell.md"
    doc.write_text("# H\n\nkernel 7.0.0-29.29 here\n", encoding="utf-8")
    assert grep.search(doc, r"7\.0\.0-", regex=True)

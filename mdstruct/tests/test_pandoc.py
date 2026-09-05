# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The re-attach rule, in both directions.

⚑⚑⚑ BOTH DIRECTIONS ARE THE POINT, because getting either wrong was a real defect and they fail
oppositely. NOT re-attaching lost a document's identity through a markdown round-trip while two
gates reported success. Re-attaching UNCONDITIONALLY prepended a YAML head to JSON output, so the
AST parser read a document opening with `---` and died at char 0 — every structural mode blind to
frontmatter'd markdown, which is every governed document.

⚑ SO THE PREDICATE IS THE WRITER, AND ONE CASE EACH WAY IS WHAT PINS IT. A single case in either
direction passes while the other defect is live.
"""

from __future__ import annotations

import json

import pytest

from mikemol.mdstruct import pandoc

pytestmark = pytest.mark.needs_pandoc

# ⚑ THE HEAD CARRIES FIELDS WHOSE LOSS WAS THE RECORDED DEFECT — identity and provenance. A
# fixture with one anonymous key would pass on a converter that preserved a fence and dropped
# what was inside it.
_HEAD = "---\nname: probe\ntype: user\noriginSessionId: abc123\n---\n"
_BODY = "# A heading\n\nSome prose.\n"


@pytest.mark.parametrize("writer", ["markdown", "gfm", "commonmark"])
def test_a_markdown_writer_keeps_the_frontmatter_byte_for_byte(writer: str) -> None:
    """Check every markdown dialect gets the head back UNCHANGED.

    ⚑⚑ THE ASSERTION IS EQUALITY, NOT `startswith("---")`. A prefix check passes on a head that
    was re-attached and reformatted — which is the defect itself, since pandoc's YAML round-trip
    is its own normalization. The recorded loss was FIELDS, so the case must see fields.

    ⚑ THE PREDICATE IS A PREFIX TEST OVER WRITER NAMES, not an equality one: an equality check
    would silently stop preserving the first time someone asked for a dialect, and the failure
    would be a missing head rather than an error. Three dialects is what makes that testable.
    """
    got = pandoc.convert(_HEAD + _BODY, writer)
    assert got.startswith(_HEAD), "the frontmatter was altered, not merely preserved"
    for field in ("name: probe", "type: user", "originSessionId: abc123"):
        assert field in got, f"{field!r} was dropped"


def test_json_does_not_get_the_frontmatter() -> None:
    """Check a non-markdown writer's output is not prefixed with YAML.

    ⚑ THE MORE DAMAGING DEFECT: a JSON document prefixed with `---` fails to parse at char 0,
    which took out every AST-backed mode on every frontmatter'd file. The assertion is that the
    output PARSES as the format asked for, not merely that it lacks a fence.
    """
    got = pandoc.convert(_HEAD + _BODY, "json")
    assert not got.lstrip().startswith("---")
    json.loads(got)  # raises if the head leaked in — the actual failure mode

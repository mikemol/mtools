# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""What is metadata, and what only looks like it.

⚑⚑ THE PRESERVATION CASE HAS A RECORDED COST. A conversion once dropped a document's `name:`,
`type:`, `originSessionId:` and `modified:` while two gates reported success — its identity and
provenance, deleted by a prose writer that had no business reformatting metadata. The split
exists so the frontmatter never reaches that writer, and these cases keep the bytes exact rather
than merely present.
"""

from __future__ import annotations

import pytest

from mikemol.mdstruct import frontmatter

_HEAD = "---\nname: probe\ntype: user\n---\n"
_BODY = "# A heading\n\nSome prose.\n"


def test_frontmatter_is_split_exactly() -> None:
    """The head and body come back byte-for-byte."""
    head, body = frontmatter.split(_HEAD + _BODY)
    assert head == _HEAD
    assert body == _BODY


def test_a_document_without_frontmatter_is_untouched() -> None:
    """A plain document passes through whole."""
    head, body = frontmatter.split(_BODY)
    assert not head
    assert body == _BODY


@pytest.mark.parametrize("src", [
    "---\nnot really metadata\n\n# heading\n",
    "---\n",
])
def test_an_unterminated_fence_is_not_frontmatter(src: str) -> None:
    """An opening fence with no close reads as body.

    ⚑ A DOCUMENT MAY OPEN WITH A HORIZONTAL RULE. Reading that as metadata would consume the
    whole file and leave nothing for the writer — a silent truncation rather than an error.
    """
    head, body = frontmatter.split(src)
    assert not head
    assert body == src


def test_the_split_rejoins() -> None:
    """Head plus body reconstructs the input.

    ⚑ THE WHOLE POINT IS RE-ATTACHMENT, so the split must be lossless by construction. A split
    that dropped a byte would restore a document subtly unlike the one it read.
    """
    src = _HEAD + _BODY
    head, body = frontmatter.split(src)
    assert head + body == src


def test_a_rule_after_prose_is_not_frontmatter() -> None:
    """A `---` that is not at the start is left alone."""
    head, _body = frontmatter.split("# heading\n\n---\n\nmore prose\n")
    assert not head

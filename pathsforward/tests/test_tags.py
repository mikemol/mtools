# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the tag grammar: each grain parses, `!w` marks a write, artifact writes lease."""

from __future__ import annotations

from mikemol.pathsforward.tags import Tag, parse_tag


def test_an_unprefixed_tag_is_a_topic_read() -> None:
    """A tag written before the grammar keeps its meaning: a topic, read, never leasable."""
    tag = parse_tag("cleanroom")
    assert (tag.grain, tag.name, tag.write, tag.leasable) == ("topic", "cleanroom", False, False)


def test_a_file_tag_normalises_its_path_without_the_filesystem() -> None:
    """A `file:` tag drops a leading ./ and a trailing /, so two spellings compare equal."""
    assert parse_tag("file:./a/b.py").name == parse_tag("file:a/b.py/").name == "a/b.py"


def test_the_write_suffix_is_stripped_and_recorded() -> None:
    """`!w` is not part of the name; it sets `write`, and the raw text is kept as stored."""
    expected = Tag("mod:display_types!w", "mod", "display_types", write=True)
    assert parse_tag("mod:display_types!w") == expected


def test_only_an_artifact_write_is_leasable() -> None:
    """file: and mod: writes lease; a read, a party: tag and a topic never do (W120 point 3)."""
    raws = ("file:x!w", "mod:x!w", "file:x", "party:summit!w", "gate!w")
    assert [parse_tag(raw).leasable for raw in raws] == [True, True, False, False, False]


def test_an_unknown_prefix_is_unknown_not_a_topic() -> None:
    """`path:` is not a grain, so it parses as unknown for --check to report, never as a topic."""
    tag = parse_tag("path:a/b.py")
    assert (tag.grain, tag.name) == ("unknown", "path:a/b.py")


def test_a_party_tag_keeps_its_name() -> None:
    """`party:summit` is an external party named summit, byte-compared."""
    tag = parse_tag("party:summit")
    assert (tag.grain, tag.name) == ("party", "summit")

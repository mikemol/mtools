# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the MHTML reader, over archives built in the tests. W907.

⚑ THE WELL-FORMED ARCHIVE IS THE POSITIVE CONTROL for every refusal: a reader that refused
everything would pass each "is a Skip" test alone.
"""

from __future__ import annotations

import base64

from mikemol.htmlstruct import mhtml, outline, tree

_PNG = b"\x89PNG\r\n\x1a\n\x00\x01"
_PARTS = 2
_B64 = base64.b64encode(_PNG).decode("ascii")
_ARCHIVE = (
    "From: <saved>\n"
    "MIME-Version: 1.0\n"
    'Content-Type: multipart/related; type="text/html";\n'
    '\tboundary="BND"\n'
    "\n"
    "preamble that is not a part\n"
    "--BND\n"
    'Content-Type: text/html; charset="utf-8"\n'
    "Content-Location: https://x.example/a.html\n"
    "Content-Transfer-Encoding: quoted-printable\n"
    "\n"
    '<h1>caf=C3=A9</h1><img src="i.png">\n'
    "--BND\n"
    "Content-Type: image/png\n"
    "Content-Location: https://x.example/i.png\n"
    "Content-Transfer-Encoding: base64\n"
    "\n"
    f"{_B64}\n"
    "--BND--\n"
    "epilogue that is not a part\n"
)


def _archive(source: str) -> mhtml.Archive:
    parsed = mhtml.read(source.encode("utf-8"))
    assert isinstance(parsed, mhtml.Archive)
    return parsed


def test_parts_come_in_order_with_location_type_charset_and_decoded_payload() -> None:
    """The control: quoted-printable and base64 are undone, framing text is ignored."""
    archive = _archive(_ARCHIVE)
    page, image = archive.parts
    assert len(archive.parts) == _PARTS
    assert (page.location, page.content_type, page.charset) == (
        "https://x.example/a.html",
        "text/html",
        "utf-8",
    )
    assert page.payload == '<h1>café</h1><img src="i.png">'.encode()
    assert (image.content_type, image.charset, image.payload) == ("image/png", None, _PNG)


def test_the_root_part_answers_the_html_readers() -> None:
    """The first part, decoded in its charset, is a tree the HTML readers can use."""
    root = mhtml.root_tree(_archive(_ARCHIVE))
    assert isinstance(root, tree.Node)
    assert [h.text for h in outline.outline(root)] == ["café"]


def test_a_part_is_addressed_by_content_location_and_an_unknown_one_is_a_miss() -> None:
    """Exact match on the location; nothing else is guessed."""
    archive = _archive(_ARCHIVE)
    found = mhtml.part_at(archive, "https://x.example/i.png")
    assert isinstance(found, mhtml.Part)
    assert found.payload == _PNG
    assert mhtml.part_at(archive, "https://x.example/none") == mhtml.Miss("https://x.example/none")
    assert mhtml.part_at(archive, "i.png") == mhtml.Miss("i.png")


def test_crlf_line_endings_read_the_same_as_lf() -> None:
    """Files saved on Windows carry CRLF; the parts are identical."""
    assert _archive(_ARCHIVE.replace("\n", "\r\n")) == _archive(_ARCHIVE)


def test_a_file_that_is_not_multipart_related_is_a_skip_naming_what_it_is() -> None:
    """A plain HTML file is not an archive."""
    parsed = mhtml.read(b"Content-Type: text/html\n\n<p>x</p>\n")
    assert isinstance(parsed, tree.Skip)
    assert "text/html" in parsed.reason


def test_a_multipart_without_a_boundary_or_parts_is_a_skip() -> None:
    """No boundary, and a boundary with nothing between its delimiters, both refuse."""
    no_boundary = mhtml.read(b"Content-Type: multipart/related\n\n--x\n")
    assert isinstance(no_boundary, tree.Skip)
    assert "no boundary" in no_boundary.reason
    empty = mhtml.read(b'Content-Type: multipart/related; boundary="b"\n\n--b--\n')
    assert isinstance(empty, tree.Skip)
    assert "no parts" in empty.reason


def test_malformed_base64_is_a_skip() -> None:
    """An undecodable part is named, not silently dropped."""
    broken = _ARCHIVE.replace(_B64, "abc")
    parsed = mhtml.read(broken.encode("utf-8"))
    assert isinstance(parsed, tree.Skip)
    assert "base64" in parsed.reason


def test_a_root_that_is_not_html_or_not_decodable_is_a_skip() -> None:
    """The root verbs apply only to an HTML root in a charset Python knows."""
    image_root = _archive(_ARCHIVE.replace("text/html; charset", "image/gif; charset"))
    skipped = mhtml.root_tree(image_root)
    assert isinstance(skipped, tree.Skip)
    assert "not text/html" in skipped.reason
    odd = _archive(_ARCHIVE.replace('charset="utf-8"', 'charset="no-such-charset"'))
    undecodable = mhtml.root_tree(odd)
    assert isinstance(undecodable, tree.Skip)
    assert "no-such-charset" in undecodable.reason

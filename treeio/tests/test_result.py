# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `result`: truthiness, the repr, and the exceptions `require` converts to."""

from __future__ import annotations

import pytest

from mikemol.treeio.presence import Presence
from mikemol.treeio.result import Result
from mikemol.treeio.sources import WorkingTree

_NON_ASCII = "\U0001d7d9 ∷ \U0001d7d8"


def test_only_a_present_result_is_truthy() -> None:
    """An empty file is truthy as a read, and ABSENT and BROKEN are both falsy."""
    assert bool(Result(Presence.PRESENT, b""))
    assert not Result(Presence.ABSENT)
    assert not Result(Presence.BROKEN)


def test_the_repr_counts_bytes_and_dashes_when_there_is_no_data() -> None:
    """The repr names presence, size and path, with a dash standing for no data at all."""
    present = Result(Presence.PRESENT, b"hello", path="a.txt")
    assert repr(present) == "Result(PRESENT, 5 bytes, 'a.txt')"
    assert repr(Result(Presence.ABSENT, path="gone")) == "Result(ABSENT, - bytes, 'gone')"
    assert repr(Result(Presence.PRESENT, b"", path="e")) == "Result(PRESENT, 0 bytes, 'e')"


def test_require_returns_the_bytes_of_a_present_read() -> None:
    """A PRESENT read hands back its raw bytes untouched."""
    assert Result(Presence.PRESENT, b"\xff\x00").require() == b"\xff\x00"


def test_require_raises_file_not_found_for_absent_naming_path_and_source() -> None:
    """ABSENT raises FileNotFoundError whose message names the path and the source."""
    result = Result(Presence.ABSENT, path="gone.txt", source=WorkingTree("."))
    with pytest.raises(FileNotFoundError) as caught:
        result.require()
    assert str(caught.value) == "gone.txt: not present at working tree"


def test_require_raises_the_recorded_cause_for_broken() -> None:
    """BROKEN raises its own error, which is not a FileNotFoundError."""
    cause = ValueError("bad revision")
    with pytest.raises(ValueError, match="bad revision") as caught:
        Result(Presence.BROKEN, error=cause, path="x").require()
    assert caught.value is cause
    assert not isinstance(caught.value, FileNotFoundError)


def test_require_raises_a_runtime_error_for_broken_without_a_cause() -> None:
    """A BROKEN result that lost its cause still raises, and says so."""
    with pytest.raises(RuntimeError) as caught:
        Result(Presence.BROKEN, path="x").require()
    assert str(caught.value) == "x: broken with no recorded cause"


def test_require_refuses_a_present_result_with_no_data() -> None:
    """A PRESENT result without bytes is malformed and raises rather than returning None."""
    with pytest.raises(RuntimeError) as caught:
        Result(Presence.PRESENT, path="x").require()
    assert str(caught.value) == "x: a PRESENT result with no data"


def test_text_decodes_utf8_and_leaves_replacement_to_the_caller() -> None:
    """Strict decoding is the default; errors=replace is the caller's explicit choice."""
    assert Result(Presence.PRESENT, _NON_ASCII.encode()).text() == _NON_ASCII
    broken = Result(Presence.PRESENT, b"\xff\xfe not utf-8")
    with pytest.raises(UnicodeDecodeError):
        broken.text()
    assert broken.text(errors="replace").endswith(" not utf-8")


def test_text_of_a_non_present_read_raises_like_require() -> None:
    """Asking an ABSENT read for text raises FileNotFoundError instead of returning a value."""
    with pytest.raises(FileNotFoundError):
        Result(Presence.ABSENT, path="p").text()

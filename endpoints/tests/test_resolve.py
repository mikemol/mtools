# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a named endpoint resolves through the host's file and every fault is None (W1419).

⚑ THE CONTROL IS THE ANSWER: a well-formed file resolves its name to the URL it holds; every other
shape (unset, missing file, not JSON, not an object, unknown name, non-string value, a scheme that
is not http or https) is None and never an exception.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.endpoints import resolve

if TYPE_CHECKING:
    from pathlib import Path


def _env(tmp_path: Path, text: str) -> dict[str, str]:
    path = tmp_path / "endpoints.json"
    path.write_text(text, encoding="utf-8")
    return {resolve.ENV: str(path)}


def test_a_named_endpoint_resolves_to_the_url_the_file_holds(tmp_path: Path) -> None:
    """The positive control: http and https both resolve, and the URL is returned unchanged."""
    env = _env(tmp_path, '{"a": "http://h:1", "b": "https://h:2/x"}')
    assert resolve.base_url("a", env) == "http://h:1"
    assert resolve.base_url("b", env) == "https://h:2/x"


def test_an_unset_variable_and_a_missing_file_are_no_answer(tmp_path: Path) -> None:
    """Nothing to read is None, whether the variable is absent, empty or names no file."""
    assert resolve.base_url("a", {}) is None
    assert resolve.base_url("a", {resolve.ENV: ""}) is None
    assert resolve.base_url("a", {resolve.ENV: str(tmp_path / "absent.json")}) is None


def test_a_file_that_is_not_an_object_of_urls_is_no_answer(tmp_path: Path) -> None:
    """Malformed JSON, a top-level list, an unknown name and a non-string value are all None."""
    assert resolve.base_url("a", _env(tmp_path, "{not json")) is None
    assert resolve.base_url("a", _env(tmp_path, '["http://h"]')) is None
    assert resolve.base_url("zzz", _env(tmp_path, '{"a": "http://h"}')) is None
    assert resolve.base_url("a", _env(tmp_path, '{"a": 7}')) is None


def test_a_scheme_other_than_http_is_no_answer_so_no_local_file_is_read(tmp_path: Path) -> None:
    """A host-supplied file is still data: file and ftp URLs are refused as None."""
    env = _env(tmp_path, '{"f": "file:///etc/passwd", "g": "ftp://h", "h": "noscheme"}')
    assert resolve.base_url("f", env) is None
    assert resolve.base_url("g", env) is None
    assert resolve.base_url("h", env) is None

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for resolving a named endpoint through the host's file (W1418, luthen's request).

⚑ THE CONTROLS ARE EVERY WAY THE ANSWER IS "NONE": an unset variable, a missing file, a file that
is not a JSON object, an absent name and a value whose scheme is not http(s) all give None, never
an exception, and a `file:` value is never returned. The answered cases prove the resolver can say
yes, with the path joined to the base exactly once whatever the base ends with.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.otlp import endpoints

if TYPE_CHECKING:
    from pathlib import Path

NAME = "victorialogs-http"
PATH = "/insert/opentelemetry/v1/logs"


def _file(tmp_path: Path, doc: object) -> dict[str, str]:
    path = tmp_path / "endpoints.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return {endpoints.ENV: str(path)}


def test_a_named_endpoint_resolves_to_its_base_and_joins_the_path_once(tmp_path: Path) -> None:
    """The base comes back as written; a trailing slash on it does not double the path's."""
    plain = _file(tmp_path, {NAME: "http://logs:9428"})
    assert endpoints.base_url(NAME, plain) == "http://logs:9428"
    assert endpoints.url_for(NAME, PATH, plain) == "http://logs:9428" + PATH
    slashed = _file(tmp_path, {NAME: "http://logs:9428/"})
    assert endpoints.url_for(NAME, PATH, slashed) == "http://logs:9428" + PATH


def test_every_way_of_not_knowing_is_none_not_an_exception(tmp_path: Path) -> None:
    """Unset variable, missing file, non-object file, absent name: all None."""
    assert endpoints.base_url(NAME, {}) is None
    assert endpoints.base_url(NAME, {endpoints.ENV: str(tmp_path / "absent.json")}) is None
    assert endpoints.base_url(NAME, _file(tmp_path, ["not", "an", "object"])) is None
    assert endpoints.base_url(NAME, _file(tmp_path, {"other": "http://x"})) is None
    assert endpoints.url_for(NAME, PATH, {}) is None


def test_a_file_scheme_or_a_non_string_value_is_refused(tmp_path: Path) -> None:
    """The control: a host-supplied file is data, so file: and a number never become a URL."""
    assert endpoints.base_url(NAME, _file(tmp_path, {NAME: "file:///etc/passwd"})) is None
    assert endpoints.base_url(NAME, _file(tmp_path, {NAME: 9428})) is None

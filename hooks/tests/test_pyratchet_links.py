# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A finding's path is relativised as the tool reported it, so a tree of links does not raise."""

import json
from pathlib import Path

import pytest

from mikemol.hooks import pyratchet

type Row = dict[str, str | None]


def _follow_links_out(self: Path, *_rest: object) -> Path:
    """Stand in for `Path.resolve` on a tree whose every file is a link out to a checkout.

    Returns:
        a path outside any temp root, as a followed link would be.

    """
    return Path("/checkout") / self.name


def test_a_path_under_the_root_is_relativised_without_following_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Bazel sandbox reports /sandbox/src/x.py, whose resolved target is outside the root."""
    monkeypatch.setattr(Path, "resolve", _follow_links_out)
    rows: list[Row] = [{"filename": str(tmp_path / "src" / "x.py"), "code": "E501"}]
    got = pyratchet.ruff_counts(json.dumps(rows), tmp_path)
    assert got == {"src/x.py": {"E501": 1}}

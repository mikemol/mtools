# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that fence's own copy of the resolver answers exactly as the shared one (W1419).

⚑ WHY TWO COPIES STAND: `mikemol-fence` declares no runtime dependencies on purpose (MODULE.bazel),
so it cannot import `mikemol.endpoints`. Two implementations are two witnesses that could have
disagreed, and the only thing that keeps them one contract is running the same cases through both.
⚑ THE CONTROL IS THE CASE TABLE: it holds the answer that resolves and every fault that must not,
and each case is asserted equal across the two, so a divergence in either copy fails here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mikemol.fence import reading

from mikemol.endpoints import resolve

if TYPE_CHECKING:
    from pathlib import Path

FILES = [
    '{"a": "http://h:1", "b": "https://h:2/x"}',
    "{not json",
    '["http://h"]',
    '{"a": 7}',
    '{"a": "file:///etc/passwd", "b": "ftp://h", "c": "noscheme"}',
]
NAMES = ["a", "b", "c", "zzz"]


def test_both_copies_read_the_same_variable() -> None:
    """The variable name is part of the contract, so the two constants are one string."""
    assert reading.ENV == resolve.ENV


@pytest.mark.parametrize("text", FILES)
@pytest.mark.parametrize("name", NAMES)
def test_both_copies_answer_every_case_alike(tmp_path: Path, text: str, name: str) -> None:
    """Resolving the same name through the same file gives the same answer from both copies."""
    path = tmp_path / "endpoints.json"
    path.write_text(text, encoding="utf-8")
    env = {resolve.ENV: str(path)}
    assert reading.endpoint_url(name, env) == resolve.base_url(name, env)


def test_both_copies_answer_alike_when_there_is_nothing_to_read(tmp_path: Path) -> None:
    """An unset variable, an empty one and a missing file are no answer from both."""
    for env in ({}, {resolve.ENV: ""}, {resolve.ENV: str(tmp_path / "absent.json")}):
        assert reading.endpoint_url("a", env) == resolve.base_url("a", env)
        assert resolve.base_url("a", env) is None

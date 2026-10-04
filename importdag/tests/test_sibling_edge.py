# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The first dist-to-dist edge: importdag resolves mikemol-atomicwrite (mtools:W562, ruled A+B)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.atomicwrite.durable import write_atomic

from mikemol.importdag import dagderive

if TYPE_CHECKING:
    from pathlib import Path


def test_the_sibling_write_helper_is_importable_beside_this_distribution(tmp_path: Path) -> None:
    """Both namespace roots resolve and the sibling's helper writes a file atomically."""
    target = tmp_path / "out.txt"
    write_atomic(target, "payload")
    assert target.read_text(encoding="utf-8") == "payload"


def test_this_distribution_still_resolves_beside_its_sibling() -> None:
    """The namespace package merges: importing the sibling does not shadow mikemol.importdag."""
    assert dagderive.__name__ == "mikemol.importdag.dagderive"

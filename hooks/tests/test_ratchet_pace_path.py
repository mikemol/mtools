# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pace file is where MIKEMOL_PACE_FILE says, else in luthen's nemik-export tree (W1920)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import ratchet_pace

if TYPE_CHECKING:
    import pytest


def test_the_named_file_wins_and_the_default_is_the_export_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The variable names the file; unset, it is `ratchet-pace.json` under luthen's export tree."""
    named = tmp_path / "elsewhere.json"
    monkeypatch.setenv(ratchet_pace.ENV, str(named))
    assert ratchet_pace.pace_path() == named
    monkeypatch.delenv(ratchet_pace.ENV)
    assert ratchet_pace.pace_path() == (
        Path.home() / ".local/share/luthen/nemik-export/ratchet-pace.json"
    )

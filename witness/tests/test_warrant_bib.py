# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.witness.warrant_bib`: the engine-free arms of substrate's two suites.

From `warrant_bib_selftest`: the config reads and the exception shape. Its arms for the
ROOT-derived paths and for `speak()` retire with them. From `warrant_records_selftest`: the claim
and tag arms, now over records given rather than parsed here. Its engine arms go with the engine
half to paperkit.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.witness import warrant_bib

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_CONFIG = '[paper]\ntitle = "t"\nconsumer_fields = ["enables", "rests-on"]\n'

_RECORDS: dict[str, dict[str, str]] = {
    "ALPHA": {"claim": "the  bound\n holds  [cases=12] under load", "check": "item:ALPHA"},
    "NEG": {"claim": "a drift of [delta=-3] is the finding", "check": "item:NEG"},
    "PLAIN": {"claim": "a claim with no marker at all", "check": "item:PLAIN"},
    "NOCLAIM": {"check": "item:NOCLAIM"},
}


def _config(tmp_path: Path, text: str = _CONFIG) -> Path:
    """Write a fixture paper.toml.

    Returns:
        its path.

    """
    path = tmp_path / "paper.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_module_needs_no_engine() -> None:
    """Importing this module does not import the engine (substrate gate-G209).

    ⚑⚑ A module importing paperkit at module scope made a whole CLI unreachable without it.
    """
    assert "paperkit" not in sys.modules


def test_there_is_no_default_project() -> None:
    """No ROOT-derived location remains, and `consumer_fields` refuses a call without a config.

    ⚑⚑ substrate's PROJECT/BIB/CONFIG were derived from `corpus.ROOT`, which the no-ROOT ruling
    forbids: installed, they would name a path inside the venv.
    """
    assert not any(hasattr(warrant_bib, name) for name in ("PROJECT", "BIB", "CONFIG"))
    with pytest.raises(TypeError, match="config"):
        cast("Callable[[], object]", warrant_bib.consumer_fields)()


def test_the_consumer_fields_are_read_from_the_config(tmp_path: Path) -> None:
    """The declared fields come from the config, in order.

    ⚑ A declaration nothing reads is indistinguishable from one nobody made.
    """
    assert warrant_bib.consumer_fields(_config(tmp_path)) == ("enables", "rests-on")


def test_an_unreadable_config_yields_nothing(tmp_path: Path) -> None:
    """A missing config yields no fields rather than raising."""
    assert warrant_bib.consumer_fields(tmp_path / "no-such.toml") == ()


def test_a_malformed_config_yields_nothing(tmp_path: Path) -> None:
    """Invalid TOML, or a wrongly shaped declaration, yields no fields rather than raising."""
    assert warrant_bib.consumer_fields(_config(tmp_path, "not = [toml")) == ()
    shaped = _config(tmp_path, '[paper]\nconsumer_fields = "enables"\n')
    assert warrant_bib.consumer_fields(shaped) == ()


def test_refusals_are_exceptions_not_exits() -> None:
    """A missing warrant raises WarrantError, a KeyError, never SystemExit.

    ⚑ A library function cannot know whether its caller wanted to continue.
    """
    assert issubclass(warrant_bib.WarrantError, KeyError)
    with pytest.raises(warrant_bib.WarrantError, match="GONE"):
        warrant_bib.claim_of("GONE", _RECORDS)


def test_a_claim_is_read_whitespace_collapsed() -> None:
    """A warrant's claim is read from the records given, its whitespace collapsed."""
    assert warrant_bib.claim_of("ALPHA", _RECORDS) == "the bound holds [cases=12] under load"


def test_a_warrant_with_no_claim_is_refused() -> None:
    """A warrant present without a claim field is refused, not read as empty prose."""
    with pytest.raises(warrant_bib.WarrantError, match="no claim"):
        warrant_bib.claim_of("NOCLAIM", _RECORDS)


def test_a_tag_is_read_from_the_claim() -> None:
    """`[name=N]` in the claim is read as an integer, negative included."""
    assert warrant_bib.tag("ALPHA", "cases", _RECORDS) == int("12")
    assert warrant_bib.tag("NEG", "delta", _RECORDS) == int("-3")


def test_an_unanchored_claim_is_refused() -> None:
    """A claim with no `[name=N]` marker is refused, never defaulted to zero.

    ⚑ An unanchored figure is a number nobody can audit.
    """
    with pytest.raises(warrant_bib.WarrantError, match="UNANCHORED"):
        warrant_bib.tag("PLAIN", "cases", _RECORDS)

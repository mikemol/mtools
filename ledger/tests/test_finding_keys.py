# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_keys`: substrate's suite, and the no-default ruling.

⚑ THE LOAD-BEARING CASE IS THE UNSLUGGED KEY: a reader that skipped `gate-O12` would report a
TAKEN ordinal as FREE, handing a filer the collision the tool exists to prevent.

⚑⚑ THE CENSUS OVER-REPORTS BY CONSTRUCTION: a supersession pair (`-reframe`) shares its ordinal
on purpose, and is still reported, never called a defect, so a paydown cannot erase the ledger's
own correction record.

⚑ THE FIXTURE CARRIES KEYS AND NOTHING ELSE: the reader matches a quoted key and a colon, so a
witness body is decoration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

import pytest

from mikemol.ledger import finding_keys

if TYPE_CHECKING:
    from pathlib import Path

_KEYS = (
    "gate-F1-first-finding",
    "gate-F1-second-finding",
    "gate-F2-only-one",
    "gate-O12",
    "sql-F1-different-family",
    "swarm-F5-reframe",
    "swarm-F5-original",
)
_COLLIDED = 2
_SLUGS_ON_COLLIDED = 2


class _OrdinalsWithoutLedger(Protocol):
    """`ordinals` as a caller who forgot the ledger would call it."""

    def __call__(self) -> list[finding_keys.Ordinal]: ...


@pytest.fixture()
def ledger(tmp_path: Path) -> Path:
    """Write a ledger-shaped roster holding exactly `_KEYS`.

    Returns:
        its path.

    """
    lines = ["WITNESSES = {", *(f'    "{k}": lambda: _standing("x"),' for k in _KEYS), "}"]
    path = tmp_path / "findings.py"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_there_is_no_default_ledger() -> None:
    """No module root and no default path: a reader without a ledger is a TypeError."""
    assert not hasattr(finding_keys, "ROOT")
    assert not hasattr(finding_keys, "LEDGER")
    with pytest.raises(TypeError, match="ledger"):
        cast("_OrdinalsWithoutLedger", finding_keys.ordinals)()


def test_every_ordinal_is_indexed_by_family(ledger: Path) -> None:
    """Every ordinal is indexed, and a different family is kept apart."""
    labels = {o.label for o in finding_keys.ordinals(ledger)}
    assert {"gate-F1", "gate-F2", "sql-F1"} <= labels


def test_an_unslugged_key_still_holds_its_ordinal(ledger: Path) -> None:
    """A bare `gate-O12` is indexed and reads as taken: THE LOAD-BEARING ARM."""
    assert "gate-O12" in {o.label for o in finding_keys.ordinals(ledger)}
    assert finding_keys.taken("gate", "O", ledger) == {12}


def test_the_taken_set_is_per_series(ledger: Path) -> None:
    """The taken set covers one family-and-letter series and excludes another family's."""
    assert finding_keys.taken("gate", "F", ledger) == {1, 2}
    assert finding_keys.taken("sql", "F", ledger) == {1}


def test_a_shared_ordinal_is_a_collision_naming_every_slug(ledger: Path) -> None:
    """A shared ordinal is reported with all its slugs; a single occupant is not a collision."""
    collided = finding_keys.collisions(ledger)
    assert len(collided) == _COLLIDED
    both = next(o for o in collided if o.label == "gate-F1")
    assert len(both.slugs) == _SLUGS_ON_COLLIDED
    assert all(o.label != "gate-F2" for o in collided)


def test_a_deliberate_supersession_still_reports(ledger: Path) -> None:
    """A `-reframe` pair collides on purpose and is reported, never silently erased."""
    assert any(o.label == "swarm-F5" for o in finding_keys.collisions(ledger))


def test_the_render_states_its_own_scope(ledger: Path) -> None:
    """The render reports the count, refuses to suggest a next number, and says nothing broke."""
    text = finding_keys.render(ledger)
    assert "2 collided ordinal(s)" in text
    assert "NO NEXT NUMBER IS SUGGESTED" in text
    assert "nothing was overwritten" in text

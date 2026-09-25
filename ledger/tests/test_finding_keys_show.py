# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_keys_show` — written FRESH: substrate's copy had no suite.

⚑ EVERY EXIT CODE IS A CONTRACT a filer's script branches on (free 0, taken 1, usage 2), so each
is asserted with the output that justifies it, and each refusal is a code rather than a traceback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.ledger import finding_keys_show

if TYPE_CHECKING:
    from pathlib import Path

_KEYS = ("gate-F1-first-finding", "gate-F1-second-finding", "gate-F2-only-one", "gate-O12")
_TAKEN = finding_keys_show.EXIT_TAKEN
_USAGE = finding_keys_show.EXIT_USAGE


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


def test_the_census_names_the_collided_ordinal(
    ledger: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no ordinal, the census prints the collision and exits 0."""
    assert finding_keys_show.main(["--ledger", str(ledger)]) == 0
    out = capsys.readouterr().out
    assert "1 collided ordinal(s)" in out
    assert "gate-F1" in out


def test_a_free_ordinal_exits_zero(ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An ordinal nobody holds is FREE, exit 0 — safe to file."""
    assert finding_keys_show.main(["--ledger", str(ledger), "gate-F3"]) == 0
    assert capsys.readouterr().out == "gate-F3: FREE\n"


def test_a_taken_ordinal_exits_one_naming_its_holders(
    ledger: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A held ordinal is TAKEN, exit 1, listing every slug filed under it."""
    assert finding_keys_show.main(["--ledger", str(ledger), "gate-F1"]) == _TAKEN
    out = capsys.readouterr().out
    assert "TAKEN by 2 finding(s)" in out
    assert "first-finding" in out
    assert "second-finding" in out


def test_an_unslugged_holder_is_still_a_holder(
    ledger: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`gate-O12`, held by an unslugged key, is TAKEN — never reported FREE."""
    assert finding_keys_show.main(["--ledger", str(ledger), "gate-O12"]) == _TAKEN
    assert "(no slug)" in capsys.readouterr().out


def test_the_ledger_is_required_and_never_derived(capsys: pytest.CaptureFixture[str]) -> None:
    """No `--ledger`, or a dangling one, refuses with exit 2 and says why."""
    assert finding_keys_show.main(["gate-F1"]) == _USAGE
    assert "--ledger PATH is required" in capsys.readouterr().err
    assert finding_keys_show.main(["--ledger"]) == _USAGE


def test_a_ledger_that_is_not_a_file_refuses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing ledger refuses with exit 2 rather than tracing back."""
    assert finding_keys_show.main(["--ledger", str(tmp_path / "absent.py")]) == _USAGE
    assert "is not a file" in capsys.readouterr().err


def test_a_malformed_or_extra_ordinal_refuses(
    ledger: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed ordinal, and two ordinals at once, each refuse with exit 2."""
    assert finding_keys_show.main(["--ledger", str(ledger), "gate-f1"]) == _USAGE
    assert "is not <family>-<letter><n>" in capsys.readouterr().err
    assert finding_keys_show.main(["--ledger", str(ledger), "gate-F1", "gate-F2"]) == _USAGE


def test_help_prints_usage_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """`--help` prints the usage, which says no next number is offered."""
    assert finding_keys_show.main(["--help"]) == 0
    assert "NO NEXT NUMBER IS OFFERED" in capsys.readouterr().out

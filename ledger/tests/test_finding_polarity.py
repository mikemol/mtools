# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_polarity`: substrate's suite, ported case for case.

⚑ THE ACCEPT DIRECTION IS CASED AS HEAVILY AS THE REFUSE DIRECTION: a guard refusing everything
would satisfy every refusal case and make the ledger unwritable — a probe becoming a wall.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.ledger import finding_polarity

if TYPE_CHECKING:
    from pathlib import Path

_PASSES = [sys.executable, "-c", "pass"]
_FAILS = [sys.executable, "-c", "raise SystemExit(3)"]
_ABSENT = ["/nonexistent/binary/entirely"]


def test_a_refuses_command_exiting_zero_is_refused_naming_both_causes(tmp_path: Path) -> None:
    """A `refuses:` command exiting 0 is REFUSED: it would read GONE; both causes are named."""
    gone = finding_polarity.probe(_PASSES, "refuses", cwd=tmp_path)
    assert gone is not None
    assert "GONE" in gone
    assert "(a)" in gone
    assert "(b)" in gone
    assert "unwitnessed" in gone


def test_a_selftest_command_exiting_nonzero_is_refused(tmp_path: Path) -> None:
    """A `selftest:` command exiting non-zero is REFUSED: the witness would be born OPEN."""
    open_now = finding_polarity.probe(_FAILS, "selftest", cwd=tmp_path)
    assert open_now is not None
    assert "born" in open_now
    assert "OPEN" in open_now


def test_a_correct_registration_is_accepted(tmp_path: Path) -> None:
    """A refusal that DOES refuse and a selftest that DOES pass are accepted: A GATE, NOT A WALL."""
    assert finding_polarity.probe(_FAILS, "refuses", cwd=tmp_path) is None
    assert finding_polarity.probe(_PASSES, "selftest", cwd=tmp_path) is None


def test_the_commandless_kinds_are_never_probed(tmp_path: Path) -> None:
    """`standing` and `unwitnessed` run no command, so they are never refused."""
    assert finding_polarity.probe(_FAILS, "standing", cwd=tmp_path) is None
    assert finding_polarity.probe(_PASSES, "unwitnessed", cwd=tmp_path) is None
    assert set(finding_polarity.PROBED) == {"refuses", "selftest", "mode"}


def test_an_absent_instrument_is_refused_for_every_probed_kind(tmp_path: Path) -> None:
    """An unstartable command is refused for EVERY probed kind, saying it did not run and why."""
    for kind in finding_polarity.PROBED:
        refused = finding_polarity.probe(_ABSENT, kind, cwd=tmp_path)
        assert refused is not None
        assert "DID NOT RUN" in refused
        assert "absent instrument" in refused


def test_a_mode_witness_reporting_documented_is_refused(tmp_path: Path) -> None:
    """A `mode:` witness reporting DOCUMENTED is refused, saying why the arm is unambiguous."""
    refused = finding_polarity.probe(_PASSES, "mode", cwd=tmp_path)
    assert refused is not None
    assert "opposite" in refused
    assert "one zero-path" in refused.lower()
    assert "unwitnessed" in refused


def test_a_mode_witness_reporting_undocumented_is_accepted(tmp_path: Path) -> None:
    """A correct `mode:` filing still passes: the arm is a gate, not a wall."""
    assert finding_polarity.probe(_FAILS, "mode", cwd=tmp_path) is None

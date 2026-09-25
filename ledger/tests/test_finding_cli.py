# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_cli`: substrate's suite, driving the WHOLE dispatch.

⚑⚑⚑ THE CASES DRIVE `run`, NOT THE MODULES UNDER IT: each collaborator has its own suite, and a
defect in WIRING is invisible to a case that calls a collaborator directly.

⚑ AN UNKNOWN FLAG IS CASED IN BOTH DIRECTIONS: refused as a flag, and NOT as a missing key.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ledger import finding_cli, finding_kinds

if TYPE_CHECKING:
    from collections.abc import Callable

_Roster = dict[str, "Callable[[], tuple[int, str]]"]

# A caller's longer kind order, with a roster-only kind before the cut.
_CALLER_ORDER = ("selftest", "refuses", "excludes", "mode_undocumented", "unwitnessed", "standing")


def _roster() -> _Roster:
    """Build a three-key fixture roster covering two kinds.

    Returns:
        the roster.

    """
    return {
        "aa-F1-a-passing-thing": lambda: finding_kinds.standing("a measured fact"),
        "aa-F2-an-honest-gap": lambda: finding_kinds.unwitnessed("nothing can check this"),
        "bb-F1-another": lambda: finding_kinds.standing("a second fact"),
    }


def _classify(key: str) -> str:
    """Classify a fixture key by kind, standing in for a caller's classifier.

    Returns:
        the kind.

    """
    return "unwitnessed" if key.endswith("gap") else "standing"


def test_an_exact_key_runs_its_witness() -> None:
    """An exact key runs its witness; the line carries the note and the witness's own code."""
    lines, code = finding_cli.run(["aa-F1-a-passing-thing"], _roster(), _classify)
    assert code == finding_kinds.CLOSED
    assert "a measured fact" in lines[0]


def test_a_unique_prefix_returns_the_witness_verdict() -> None:
    """A unique prefix resolves to its full key and returns its KIND's code, not the router's."""
    lines, code = finding_cli.run(["aa-F2"], _roster(), _classify)
    assert code == finding_kinds.UNRUNNABLE
    assert "aa-F2-an-honest-gap" in lines[0]


def test_an_ambiguous_or_unknown_key_is_refused() -> None:
    """An ambiguous prefix and an unknown key are REFUSED, each saying which it is."""
    ambiguous, amb_code = finding_cli.run(["aa-"], _roster(), _classify)
    unknown, unknown_code = finding_cli.run(["zz-nothing"], _roster(), _classify)
    assert amb_code == finding_cli.REFUSED
    assert "AMBIGUOUS" in ambiguous[0]
    assert unknown_code == finding_cli.REFUSED
    assert "roster/record" in unknown[0]


def test_kinds_reports_the_zero_row_and_the_totals() -> None:
    """`--kinds` answers with a row for an unused kind, and the behavioural total."""
    lines, code = finding_cli.run(["--kinds"], _roster(), _classify)
    blob = "\n".join(lines)
    assert code == 0
    assert "refuses" in blob
    assert "BEHAVIOURAL" in blob
    assert "flip" in blob


def test_kinds_honours_the_callers_order() -> None:
    """A caller's own kind order reaches the census: its roster-only kind gets a zero row."""
    lines, _ = finding_cli.run(["--kinds"], _roster(), _classify, _CALLER_ORDER)
    assert any("excludes" in line for line in lines)


def test_a_bare_invocation_prints_usage() -> None:
    """No arguments print the usage, naming the modes, rather than guessing."""
    lines, code = finding_cli.run([], _roster(), _classify)
    assert code == finding_cli.REFUSED
    assert "--pairing" in lines[0]


def test_an_unknown_flag_is_refused_as_a_flag_not_a_key() -> None:
    """An unknown flag is refused naming the flag, and NOT as a roster/record disagreement."""
    lines, code = finding_cli.run(["--nonsense"], _roster(), _classify)
    assert code == finding_cli.REFUSED
    assert "unknown mode" in lines[0]
    assert "--nonsense" in lines[0]
    assert all("roster/record" not in line for line in lines)


def test_no_declared_mode_reaches_the_unknown_mode_refusal() -> None:
    """Every declared mode is reachable: none falls through to the unknown-mode refusal."""
    unreachable = [
        mode
        for mode in finding_cli.MODES
        if "unknown mode" in "\n".join(finding_cli.run([mode], _roster(), _classify)[0])
    ]
    assert not unreachable
    assert {"--kinds", "--pairing"} <= set(finding_cli.MODES)


def test_the_router_never_normalises_a_verdict() -> None:
    """CLOSED stays CLOSED and UNRUNNABLE stays UNRUNNABLE — never collapsed into OPEN."""
    _, closed = finding_cli.run(["aa-F1-a-passing-thing"], _roster(), _classify)
    _, unrunnable = finding_cli.run(["aa-F2-an-honest-gap"], _roster(), _classify)
    assert closed == finding_kinds.CLOSED
    assert unrunnable == finding_kinds.UNRUNNABLE
    assert finding_kinds.UNRUNNABLE != finding_kinds.OPEN

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The preflight lints every distribution's declared defects before a stack is submitted (W1531)."""

from pathlib import Path

_PREFLIGHT = Path(__file__).parent.parent.parent / "preflight.sh"
_CALL = "mikemol.mutation.lint"


def test_the_preflight_runs_the_mutation_lint_over_each_distribution() -> None:
    """The call names the lint module and the distribution, and a failure marks the run failed."""
    text = _PREFLIGHT.read_text(encoding="utf-8")
    at = text.index(_CALL)
    line = text[at : text.index("\n", at)]
    assert '"$root/$dist"' in line
    assert "fail=1" in text[at : at + 400]


def test_a_missing_lint_interpreter_refuses_before_the_call_and_never_skips() -> None:
    """The guard comes first and exits 1, the preflight's rule for every tool it relies on."""
    text = _PREFLIGHT.read_text(encoding="utf-8")
    guard = text.index('if [ ! -x "$_lint" ]')
    call = text.index(_CALL)
    assert guard < call
    assert "exit 1" in text[guard:call]

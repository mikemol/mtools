# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Implementation adapters: `--impl` picks which implementation fills each case's result.

⚑ The spec denies a `not (c)` result, as W196's else-body port did. The fake reference returns
the condition, the fake subject negates it, so one spec judges both implementations.
"""

import pytest

_LOAD = ("-p", "no:pytestspec", "-p", "mikemol.pytestspec.plugin")

# The stub evaluator denies exactly the port's defective else-body shape.
_CONFTEST = """
from mikemol.pytestspec.plugin import EVALUATOR
from mikemol.pytestspec.spec import Verdict

def _stub(spec, case):
    bad = case.get("result") == "not (" + case.get("fixture", "") + ")"
    return Verdict(deny=("else-body is negated",) if bad else ())

def pytest_configure(config):
    config.stash[EVALUATOR] = _stub

def pytest_spec_implementations():
    return {
        "reference": lambda fixture, operands: fixture,
        "subject": lambda fixture, operands: "not (" + fixture + ")",
    }
"""

_CASES = '[{"case": "else", "fixture": "c", "operands": []}]'


def _spec(pytester: pytest.Pytester) -> None:
    """Write the conftest, a spec, and its one fixture-carrying case."""
    pytester.makeconftest(_CONFTEST)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_CASES)


def test_reference_impl_is_admitted(pytester: pytest.Pytester) -> None:
    """`--impl reference` runs the origin on the fixture; its result is admitted."""
    _spec(pytester)
    pytester.runpytest(*_LOAD, "--impl", "reference").assert_outcomes(passed=1)


def test_subject_impl_is_denied(pytester: pytest.Pytester) -> None:
    """`--impl subject` runs the port on the same fixture; its negated result is denied."""
    _spec(pytester)
    result = pytester.runpytest(*_LOAD, "-rf", "--impl", "subject")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*else: DENIED: else-body is negated*"])


def test_unknown_impl_fails_as_unmeasured(pytester: pytest.Pytester) -> None:
    """An `--impl` no plugin offers FAILS each case as UNMEASURED and names what is offered."""
    _spec(pytester)
    result = pytester.runpytest(*_LOAD, "-rf", "--impl", "nope")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*UNMEASURED*offered: reference, subject*"])


def test_case_without_fixture_fails_under_impl(pytester: pytest.Pytester) -> None:
    """Under `--impl`, a case with no fixture has nothing to run, and FAILS as UNMEASURED."""
    pytester.makeconftest(_CONFTEST)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec='[{"case": "bare", "result": "c"}]')
    result = pytester.runpytest(*_LOAD, "-rf", "--impl", "reference")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*UNMEASURED*no `fixture` to run*"])


def test_precomputed_result_without_impl_still_works(pytester: pytest.Pytester) -> None:
    """Without `--impl`, a case is evaluated as written (W200 back-compat)."""
    pytester.makeconftest(_CONFTEST)
    pytester.makefile(".rego", spec="package s\n")
    cases = '[{"case": "ok", "fixture": "c", "result": "c"}]'
    pytester.makefile(".cases.json", spec=cases)
    pytester.runpytest(*_LOAD).assert_outcomes(passed=1)

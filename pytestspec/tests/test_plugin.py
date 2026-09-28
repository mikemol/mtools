# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The plugin: which files are specs, and how each case's verdict becomes a pytest outcome.

⚑ THE INNER SESSIONS LOAD THE PLUGIN BY MODULE, with its entry-point name blocked, so the run
is the same whether or not the distribution is installed (the local venv installs it; bazel
does not).
"""

from pathlib import Path

import pytest

from mikemol.pytestspec import plugin

_LOAD = ("-p", "no:pytestspec", "-p", "mikemol.pytestspec.plugin")

# The stub evaluator returns the verdict the case's own data names.
_STUB = """
from mikemol.pytestspec.plugin import EVALUATOR
from mikemol.pytestspec.spec import Verdict

def _stub(spec, case):
    return Verdict(deny=tuple(case.get("deny", ())), withheld=tuple(case.get("withheld", ())))

def pytest_configure(config):
    config.stash[EVALUATOR] = _stub
"""

_CASES = """[
  {"case": "good"},
  {"case": "bad", "deny": ["line 11 negated"]},
  {"case": "unknown", "withheld": ["no rule for case"]}
]"""

# A miniature of W196's `guarded` else-body rule, evaluated by the real opa.
_LIVE_SPEC = """package live
import rego.v1
deny contains "else-body is negated" if input.result == "not (c)"
"""

_LIVE_CASES = """[
  {"case": "origin", "result": "c"},
  {"case": "negated", "result": "not (c)"}
]"""


def test_a_rego_file_is_claimed() -> None:
    """A `.rego` file is a spec the plugin claims."""
    assert plugin.claims(Path("specs/guarded.rego"))


def test_opa_test_file_is_not_claimed() -> None:
    """A `_test.rego` file is opa's own unit test, run by `opa test`, not a spec."""
    assert not plugin.claims(Path("specs/guarded_test.rego"))


def test_python_file_is_not_claimed() -> None:
    """A `.py` file is left to pytest's own collector."""
    assert not plugin.claims(Path("tests/test_plugin.py"))


def test_each_verdict_maps_to_its_outcome(pytester: pytest.Pytester) -> None:
    """Admitted passes; a deny fails with its message; a withheld case fails as UNMEASURED."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_CASES)
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(passed=1, failed=2)
    result.stdout.fnmatch_lines(
        [
            "*bad: DENIED: line 11 negated*",
            "*unknown: UNMEASURED (withheld, not passed): no rule for case*",
        ]
    )


def test_absent_opa_fails_every_case(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no evaluator set and no opa on PATH, a case FAILS as UNMEASURED; it never skips."""
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec='[{"case": "good"}]')
    monkeypatch.setenv("PATH", str(pytester.path))
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*UNMEASURED (not evaluated, not passed): opa not found*"])


def test_pinned_opa_admits_and_denies(pytester: pytest.Pytester) -> None:
    """The default evaluator runs the host's pinned opa: a compliant case passes, a bad one fails.

    ⚑ This is the live P-arm, and it needs opa on the host. Absent, it FAILS, as every case does.
    """
    pytester.makefile(".rego", spec=_LIVE_SPEC)
    pytester.makefile(".cases.json", spec=_LIVE_CASES)
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["*negated: DENIED: else-body is negated*"])


def test_ruleless_spec_admits_nothing(pytester: pytest.Pytester) -> None:
    """A spec with no rules FAILS every case; it must not admit what it never judged.

    ⚑ MEASURED: before W200's fix, `package s` alone passed its case through the real opa.
    """
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec='[{"case": "good"}]')
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*UNMEASURED*no `deny` rule*"])


def test_spec_without_case_data_is_a_collection_error(pytester: pytest.Pytester) -> None:
    """A spec with no `.cases.json` ERRORS at collection; it never collects as zero cases."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    result = pytester.runpytest(*_LOAD)
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*no case data at spec.cases.json*"])


def test_opa_test_file_collects_nothing(pytester: pytest.Pytester) -> None:
    """A lone `_test.rego` (opa's own unit test) collects no items."""
    pytester.makefile(".rego", spec_test="package s_test\n")
    result = pytester.runpytest(*_LOAD)
    assert result.ret == pytest.ExitCode.NO_TESTS_COLLECTED


_DISPOSED = """[
  {"case": "good"},
  {"case": "dropped", "disposition": "do-not-port", "reason": "origin quirk", "deny": ["x"]},
  {"case": "pending", "disposition": "unmeasured", "reason": "no rule yet", "withheld": ["w"]},
  {"case": "origin-row", "deny": ["origin negates"]},
  {"case": "port-row", "disposition": "port-fix", "reason": "fixed", "pairs_with": "origin-row"}
]"""


def test_dispositions_map_to_their_outcomes(pytester: pytest.Pytester) -> None:
    """do-not-port is deselected and counted; declared unmeasured is xfail; port-fix runs."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_DISPOSED)
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(passed=2, failed=1, xfailed=1, deselected=1)
    result.stdout.fnmatch_lines(["*origin-row: DENIED: origin negates*"])


def test_declared_unmeasured_that_passes_fails(pytester: pytest.Pytester) -> None:
    """A declared unmeasured case that is admitted FAILS (strict): the declaration is stale."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    cases = '[{"case": "c", "disposition": "unmeasured", "reason": "r"}]'
    pytester.makefile(".cases.json", spec=cases)
    result = pytester.runpytest(*_LOAD)
    result.assert_outcomes(failed=1)


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ('{"case": "c", "disposition": "skip", "reason": "r"}', "*is not one of*"),
        ('{"case": "c", "disposition": "do-not-port"}', "*needs a `reason`*"),
        ('{"case": "c", "disposition": "port-fix", "reason": "r"}', "*`pairs_with` must name*"),
    ],
)
def test_malformed_disposition_is_a_collection_error(
    pytester: pytest.Pytester, case: str, message: str
) -> None:
    """An unknown kind, a missing reason, or an unpaired port-fix ERRORS at collection."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=f"[{case}]")
    result = pytester.runpytest(*_LOAD)
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines([message])

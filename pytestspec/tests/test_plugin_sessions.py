# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Session witnesses for the spec item and file machinery, each aimed at a declared defect.

W1014. ⚑ THE SESSIONS IN test_plugin DID NOT NOTICE these: a port-fix or an undeclared case spared
by `--skip-declared`, a cache entry that hid the refusal of a case with no fixture or of an
implementation nobody offers, a cached result dropped from the judgment, a cache directory made
when none was asked for, and bad case data that escaped collection as a raw traceback. The inner
sessions load the plugin by module, as in test_plugin.
"""

import pytest

from mikemol.pytestspec import cache

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

# An evaluator that denies a result named "bad", one adapter, and a cache key that is the case name.
_ADAPTING = """
from mikemol.pytestspec.plugin import EVALUATOR
from mikemol.pytestspec.spec import Verdict

def _judge(spec, case):
    bad = case.get("result") == "bad"
    return Verdict(deny=("R1: bad result",) if bad else ())

def pytest_configure(config):
    config.stash[EVALUATOR] = _judge

def pytest_spec_implementations():
    return {"reference": lambda fixture, operands: fixture}

def pytest_spec_cache_key(impl, case):
    return case["case"]
"""

_MIXED = """[
  {"case": "good"},
  {"case": "origin-row", "deny": ["origin negates"]},
  {"case": "port-row", "disposition": "port-fix", "reason": "fixed", "pairs_with": "origin-row"},
  {"case": "pending", "disposition": "unmeasured", "reason": "no rule yet", "withheld": ["w"]}
]"""

_PENDING = (
    '[{"case": "c", "disposition": "unmeasured", "reason": "no rule yet", "withheld": ["w"]}]'
)
_PLAIN = '[{"case": "p", "fixture": "c"}]'
_NO_FIXTURE = '[{"case": "nofix"}]'
_BAD = '[{"case": "bad", "deny": ["line 11 negated"]}]'


def _session(pytester: pytest.Pytester, conftest: str, cases: str) -> None:
    """Lay out a spec, its case data and a conftest in the inner session's directory."""
    pytester.makeconftest(conftest)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=cases)


def _planted_run(pytester: pytest.Pytester, impl: str, key: str, planted: str) -> pytest.RunResult:
    """Plant a cache entry for (impl, key), then run the session under that implementation.

    Returns:
        the run, with failures summarised.

    """
    root = pytester.path / "results"
    stored = cache.store(root, impl, key, planted)
    assert stored
    return pytester.runpytest(*_LOAD, "--impl", impl, "--result-cache", str(root), "-rf")


def test_skip_declared_spares_only_the_declared_unmeasured_case(pytester: pytest.Pytester) -> None:
    """A port-fix and an undeclared case are still evaluated under `--skip-declared`."""
    _session(pytester, _STUB, _MIXED)
    result = pytester.runpytest(*_LOAD, "--skip-declared")
    result.assert_outcomes(passed=2, failed=1, xfailed=1)


def test_a_skipped_case_says_why_it_was_not_evaluated(pytester: pytest.Pytester) -> None:
    """With the xfail lifted, the skipped case's failure names the flag that spared it."""
    _session(pytester, _STUB, _PENDING)
    result = pytester.runpytest(*_LOAD, "--skip-declared", "--runxfail", "-rf")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*c: DECLARED-SKIPPED (not evaluated): --skip-declared*"])


def test_a_declared_unmeasured_case_is_a_strict_xfail_with_its_reason(
    pytester: pytest.Pytester,
) -> None:
    """The reason the author gave is what the xfail summary prints."""
    _session(pytester, _STUB, _PENDING)
    result = pytester.runpytest(*_LOAD, "-rx")
    result.assert_outcomes(xfailed=1)
    result.stdout.fnmatch_lines(["*XFAIL*c*no rule yet*"])


def test_a_failing_case_is_headed_by_its_spec_and_case_name(pytester: pytest.Pytester) -> None:
    """The failure section names the case, from the item's own report info."""
    _session(pytester, _STUB, _BAD)
    result = pytester.runpytest(*_LOAD)
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*_ spec: bad _*"])


def test_no_cache_directory_is_made_when_none_was_asked_for(pytester: pytest.Pytester) -> None:
    """Without `--result-cache` nothing is stored, even under a vouched-for key."""
    _session(pytester, _ADAPTING, _PLAIN)
    result = pytester.runpytest(*_LOAD, "--impl", "reference")
    result.assert_outcomes(passed=1)
    assert not (pytester.path / "None").exists()


def test_a_cached_result_still_goes_to_the_judgment(pytester: pytest.Pytester) -> None:
    """A reused result is judged by the spec: a cached bad result is denied, not waved through."""
    _session(pytester, _ADAPTING, _PLAIN)
    result = _planted_run(pytester, "reference", "p", "bad")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*p: DENIED: R1: bad result*"])


def test_a_cache_hit_never_hides_a_case_with_no_fixture(pytester: pytest.Pytester) -> None:
    """The fixture check comes before the cache: a fixtureless case's entry does not pass it."""
    _session(pytester, _ADAPTING, _NO_FIXTURE)
    result = _planted_run(pytester, "reference", "nofix", "c")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*UNMEASURED (not evaluated, not passed)*no `fixture`*"])


def test_a_cache_hit_never_hides_an_implementation_nobody_offers(
    pytester: pytest.Pytester,
) -> None:
    """The implementation must be offered before the cache is read: a ghost's entry is unused."""
    _session(pytester, _ADAPTING, _PLAIN)
    result = _planted_run(pytester, "ghost", "p", "c")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*UNMEASURED (not evaluated, not passed)*ghost*"])


def test_bad_case_data_is_a_collection_error_and_not_a_traceback(
    pytester: pytest.Pytester,
) -> None:
    """The collection error is the message alone: no frame of the plugin's own code is shown."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    result = pytester.runpytest(*_LOAD)
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*spec.rego: no case data at spec.cases.json*"])
    assert "plugin.py" not in result.stdout.str()

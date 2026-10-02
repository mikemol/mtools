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

# W380: a spec importing a shared helper, the shape el-openglo's policies use.
_LIB = """package lib.truth
import rego.v1
negated(r) if r == "not (c)"
"""

_IMPORTING_SPEC = """package importing
import rego.v1
import data.lib.truth
deny contains "L1: else-body is negated" if truth.negated(input.result)
"""


def _importing(pytester: pytest.Pytester) -> None:
    pytester.makefile(".rego", spec=_IMPORTING_SPEC)
    pytester.makefile(".cases.json", spec=_LIVE_CASES)
    lib = pytester.path / "lib"
    lib.mkdir()
    (lib / "truth.rego").write_text(_LIB, encoding="utf-8")


def test_declared_data_lets_a_spec_import_a_shared_helper(pytester: pytest.Pytester) -> None:
    """With `pytestspec_data = lib`, the import compiles and the live opa judges both cases."""
    _importing(pytester)
    pytester.makeini("[pytest]\npytestspec_data = lib\n")
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["*negated: DENIED: L1: else-body is negated*"])


def test_undeclared_helper_is_an_error_not_guessed(pytester: pytest.Pytester) -> None:
    """Without the key, lib/ is neither loaded nor exempt: it errors as a spec with no cases."""
    _importing(pytester)
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*truth.rego: no case data at truth.cases.json*"])


def test_undeclared_helper_outside_the_tree_is_unmeasured(pytester: pytest.Pytester) -> None:
    """A spec whose import nothing loads fails UNMEASURED; no sibling directory is guessed."""
    pytester.makefile(".rego", spec=_IMPORTING_SPEC)
    pytester.makefile(".cases.json", spec=_LIVE_CASES)
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(
        ["*UNMEASURED (not evaluated, not passed): opa eval exit*rego_type_error*"]
    )


def test_declared_data_that_does_not_exist_is_a_collection_error(
    pytester: pytest.Pytester,
) -> None:
    """A declared path that is missing ERRORS at collection, naming the key."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec='[{"case": "c"}]')
    pytester.makeini("[pytest]\npytestspec_data = nowhere\n")
    result = pytester.runpytest(*_LOAD)
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*pytestspec_data names a path that does not exist*nowhere*"])


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


_EXPECTING = """[
  {"case": "refused", "deny": ["S0: must refuse"], "expect": {"deny": ["S0"]}},
  {"case": "wrong-rule", "deny": ["S1: other"], "expect": {"deny": ["S0"]}},
  {"case": "slipped", "expect": {"deny": ["S0"]}}
]"""


def test_expected_deny_maps_to_its_outcome(pytester: pytest.Pytester) -> None:
    """A refusing fixture passes on its expected rule; another rule, or none, fails (W372)."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_EXPECTING)
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(passed=1, failed=2)
    result.stdout.fnmatch_lines(
        [
            "*wrong-rule: DENY MISMATCH: missing S0; unexpected S1*",
            "*slipped: DENY MISMATCH: missing S0; unexpected none*",
            (
                "pytestspec: spec.rego impl=as-written admitted=0 denied=2 refused=1"
                " withheld-expected=0 unmeasured=0*"
            ),
        ]
    )


_WITHHOLDING = """[
  {"case": "null-lint", "withheld": ["W: qmllint is null"], "expect": {"withheld": ["W"]}},
  {"case": "also-denied", "deny": ["L2: x"], "withheld": ["W: y"],
   "expect": {"withheld": ["W"]}},
  {"case": "measured", "expect": {"withheld": ["W"]}}
]"""


def test_expected_withhold_maps_to_its_own_column(pytester: pytest.Pytester) -> None:
    """W381: an expected withhold passes and counts as withheld-expected, never as admitted."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_WITHHOLDING)
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(passed=1, failed=2)
    result.stdout.fnmatch_lines(
        [
            "*also-denied: DENY MISMATCH: missing none; unexpected L2*",
            "*measured: WITHHELD MISMATCH: missing W; unexpected none*",
            (
                "pytestspec: spec.rego impl=as-written admitted=0 denied=1 refused=0"
                " withheld-expected=1 unmeasured=1*"
            ),
        ]
    )


_TEXT_SAYS_DENIED = """[
  {"case": "withheld", "withheld": ["W: upstream DENIED access"]},
  {"case": "unmet", "withheld": ["W: DENY MISMATCH in log"], "expect": {"withheld": ["X"]}}
]"""


def test_a_failing_column_is_declared_not_read_from_the_text(pytester: pytest.Pytester) -> None:
    """W374: a withheld case whose message says DENIED is unmeasured; the text decides nothing."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_TEXT_SAYS_DENIED)
    result = pytester.runpytest(*_LOAD, "-rf")
    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(
        [
            (
                "pytestspec: spec.rego impl=as-written admitted=0 denied=0 refused=0"
                " withheld-expected=0 unmeasured=2*"
            ),
        ]
    )


def test_malformed_expect_is_a_collection_error(pytester: pytest.Pytester) -> None:
    """A bare `"expect": "denied"` ERRORS at collection rather than running admitted-only."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec='[{"case": "c", "expect": "denied"}]')
    result = pytester.runpytest(*_LOAD)
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*case c: expect must be*"])


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


def test_differential_line_counts_each_case_once(pytester: pytest.Pytester) -> None:
    """One row per spec states every column; `-rf` must not count a failure twice."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_DISPOSED)
    result = pytester.runpytest(*_LOAD, "-rfx")
    result.stdout.fnmatch_lines(
        [
            (
                "pytestspec: spec.rego impl=as-written admitted=2 denied=1 refused=0"
                " withheld-expected=0 unmeasured=1"
                " do-not-port=1 port-fix=1 declared-skipped=0 cached=0"
            )
        ]
    )


def test_differential_line_survives_a_parallel_run(pytester: pytest.Pytester) -> None:
    """⚑ Under `-n 2` the controller prints the SAME line as a serial run (W316, el-openglo:W139).

    Measured before the fix: outcomes were right, and the line was silently absent, because each
    spec's tally opened at collection, which only the workers do. Declarations are counted once
    (every worker collects them all); outcomes are summed (each case runs on one worker).
    """
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_DISPOSED)
    result = pytester.runpytest_subprocess(*_LOAD, "-n", "2", "-p", "xdist")
    result.stdout.fnmatch_lines(
        [
            (
                "pytestspec: spec.rego impl=as-written admitted=2 denied=1 refused=0"
                " withheld-expected=0 unmeasured=1"
                " do-not-port=1 port-fix=1 declared-skipped=0 cached=0"
            )
        ]
    )


def test_skip_declared_spares_a_stale_declaration(pytester: pytest.Pytester) -> None:
    """Under --skip-declared a declared unmeasured case is not evaluated, and is counted so."""
    pytester.makeconftest(_STUB)
    pytester.makefile(".rego", spec="package s\n")
    cases = '[{"case": "c", "disposition": "unmeasured", "reason": "r"}]'
    pytester.makefile(".cases.json", spec=cases)
    result = pytester.runpytest(*_LOAD, "--skip-declared")
    result.assert_outcomes(xfailed=1)
    result.stdout.fnmatch_lines(
        ["*unmeasured=1 do-not-port=0 port-fix=0 declared-skipped=1 cached=0"]
    )


# The adapter leaves a mark in the run's directory, so a test can see whether it ran at all.
_MARKING = """
from pathlib import Path

from mikemol.pytestspec.plugin import EVALUATOR
from mikemol.pytestspec.spec import Verdict

def _mark(fixture, operands):
    Path("adapter-ran").touch()
    return fixture

def pytest_configure(config):
    config.stash[EVALUATOR] = lambda spec, case: Verdict()

def pytest_spec_implementations():
    return {"reference": _mark}
"""

_DECLARED = '[{"case": "d", "fixture": "c", "disposition": "unmeasured", "reason": "r"}]'


def _marked(pytester: pytest.Pytester, *flags: str) -> bool:
    """Run a declared unmeasured case under `--impl reference` plus `flags`.

    Returns:
        whether the adapter ran.

    """
    pytester.makeconftest(_MARKING)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_DECLARED)
    pytester.runpytest(*_LOAD, "--impl", "reference", *flags)
    return (pytester.path / "adapter-ran").exists()


def test_declared_case_runs_its_adapter_by_default(pytester: pytest.Pytester) -> None:
    """By default a declared unmeasured case is evaluated, so its adapter runs (W227 (a))."""
    assert _marked(pytester)


def test_skip_declared_never_runs_the_adapter(pytester: pytest.Pytester) -> None:
    """Under --skip-declared a declared unmeasured case never reaches its adapter."""
    assert not _marked(pytester, "--skip-declared")


# Both an origin and a port, each leaving its own mark.
_BOTH = """
from pathlib import Path

from mikemol.pytestspec.plugin import EVALUATOR
from mikemol.pytestspec.spec import Verdict

def _mark(name):
    def run(fixture, operands):
        Path(f"{name}-ran").touch()
        return fixture
    return run

def pytest_configure(config):
    config.stash[EVALUATOR] = lambda spec, case: Verdict()

def pytest_spec_implementations():
    return {"reference": _mark("reference"), "subject": _mark("subject")}
"""

_NOT_PORTED = '[{"case": "d", "fixture": "c", "disposition": "do-not-port", "reason": "r"}]'


def _not_ported_under(pytester: pytest.Pytester, impl: str) -> tuple[bool, pytest.RunResult]:
    """Run a do-not-port case under `--impl impl`.

    Returns:
        whether that implementation's adapter ran, and the run.

    """
    pytester.makeconftest(_BOTH)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_NOT_PORTED)
    result = pytester.runpytest(*_LOAD, "--impl", impl)
    return (pytester.path / f"{impl}-ran").exists(), result


def test_do_not_port_still_measures_the_origin(pytester: pytest.Pytester) -> None:
    """A do-not-port case is a decision about the PORT: the origin is still run (W459)."""
    ran, result = _not_ported_under(pytester, "reference")
    assert ran
    result.assert_outcomes(passed=1)


def test_do_not_port_is_deselected_for_a_port(pytester: pytest.Pytester) -> None:
    """Under any implementation but the origin, a do-not-port case is deselected and counted."""
    ran, result = _not_ported_under(pytester, "subject")
    assert not ran
    result.assert_outcomes(deselected=1)


# The conftest vouches that a case's name is everything the adapter reads.
_KEYED = (
    _MARKING
    + """
def pytest_spec_cache_key(impl, case):
    return case["case"]
"""
)

_PLAIN = '[{"case": "p", "fixture": "c"}]'


def _run_twice(pytester: pytest.Pytester, conftest: str) -> tuple[bool, pytest.RunResult]:
    """Run one case under `--impl reference --result-cache`, clear the mark, then run it again.

    Returns:
        whether the adapter ran the second time, and the second run's result.

    """
    pytester.makeconftest(conftest)
    pytester.makefile(".rego", spec="package s\n")
    pytester.makefile(".cases.json", spec=_PLAIN)
    flags = ("--impl", "reference", "--result-cache", str(pytester.path / "results"))
    pytester.runpytest(*_LOAD, *flags)
    (pytester.path / "adapter-ran").unlink()
    result = pytester.runpytest(*_LOAD, *flags)
    return (pytester.path / "adapter-ran").exists(), result


def test_a_keyed_result_is_reused_and_counted(pytester: pytest.Pytester) -> None:
    """Under a conftest's key the second run reuses the result, and says so as `cached=1`."""
    ran, result = _run_twice(pytester, _KEYED)
    assert not ran
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*admitted=1 *cached=1"])


def test_an_unkeyed_result_is_never_reused(pytester: pytest.Pytester) -> None:
    """With no conftest key, `--result-cache` caches nothing: the adapter runs every time."""
    ran, result = _run_twice(pytester, _MARKING)
    assert ran
    result.stdout.fnmatch_lines(["*cached=0"])

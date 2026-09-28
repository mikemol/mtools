# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pytest11 entry point: a `.rego` spec collects one item per case in its case data.

⚑ THE EVALUATOR IS READ FROM `config.stash[EVALUATOR]`; when nothing set it, the pinned opa
evaluator (W200) is installed on first use. A case that could not be evaluated — opa absent,
the wrong version, or an eval error — FAILS as UNMEASURED: it measured nothing, and that must
not read as a pass or a skip.

⚑ A case's declared disposition (W201, see `spec.DISPOSITIONS`) changes its outcome: a
do-not-port case is DESELECTED, and pytest counts it in the run's summary line; a declared
unmeasured case is xfail(strict), so it can never read as a pass.
"""

from pathlib import Path
from typing import cast

import pytest

from mikemol.pytestspec import adapters, opa
from mikemol.pytestspec.spec import (
    DO_NOT_PORT,
    PORT_FIX,
    UNMEASURED,
    Case,
    Disposition,
    Evaluator,
    SpecDataError,
    disposition_of,
    judge,
    load_cases,
)

SPEC_SUFFIX = ".rego"
# ⚑ A `_test.rego` FILE IS OPA'S OWN UNIT TEST OF A SPEC, run by `opa test`; it is not a spec.
OPA_TEST_SUFFIX = "_test.rego"

EVALUATOR = pytest.StashKey[Evaluator]()


def claims(path: Path) -> bool:
    """Decide whether `path` is a spec this plugin collects.

    Returns:
        True for a `.rego` file, False for opa's own `_test.rego` and for anything else.

    """
    return path.name.endswith(SPEC_SUFFIX) and not path.name.endswith(OPA_TEST_SUFFIX)


class SpecFailedError(Exception):
    """One case was denied, withheld, or could not be evaluated."""


class SpecItem(pytest.Item):
    """One case of one spec."""

    def __init__(
        self,
        *,
        name: str,
        parent: pytest.Collector,
        case: Case,
        disposition: Disposition | None,
    ) -> None:
        """Hold the case this item evaluates, and mark a declared unmeasured case xfail."""
        super().__init__(name=name, parent=parent)
        self.case = case
        self.disposition = disposition
        if disposition is not None and disposition.kind == UNMEASURED:
            self.add_marker(pytest.mark.xfail(reason=disposition.reason, strict=True))

    def _evaluator(self) -> Evaluator:
        """Return the configured evaluator, installing the pinned opa one if none is set.

        Returns:
            the session's evaluator.

        """
        found = self.config.stash.get(EVALUATOR, None)
        if found is None:
            found = opa.evaluator()
            self.config.stash[EVALUATOR] = found
        return found

    def _filled(self) -> Case:
        """Fill the case's `result` from the `--impl` implementation, if one was chosen.

        Returns:
            the case as written without `--impl`; otherwise a copy carrying the chosen
            implementation's result.

        """
        name = cast("object", self.config.getoption("impl"))
        if not isinstance(name, str):
            return self.case
        return adapters.fill(self.case, name, adapters.registered(self.config))

    def runtest(self) -> None:
        """Evaluate the case and fail unless it is admitted.

        Raises:
            SpecFailedError: the case could not be evaluated, or its verdict is not admitted.

        """
        try:
            verdict = self._evaluator()(self.path, self._filled())
        except (opa.OpaUnavailableError, SpecDataError) as exc:
            msg = f"UNMEASURED (not evaluated, not passed): {exc}"
            raise SpecFailedError(msg) from exc
        failure = judge(verdict)
        if failure is not None:
            raise SpecFailedError(failure)

    def repr_failure(
        self,
        excinfo: pytest.ExceptionInfo[BaseException],
        style: object = None,
    ) -> str:
        """Report a spec failure as its message; anything else in pytest's default style.

        ⚑ `style` is accepted and NOT forwarded: its type is private to pytest, and a spec item
        has no traceback worth styling.

        Returns:
            the failure text.

        """
        del style
        if isinstance(excinfo.value, SpecFailedError):
            return f"{self.name}: {excinfo.value}"
        return str(super().repr_failure(excinfo))

    def reportinfo(self) -> tuple[Path, int, str]:
        """Locate the item as its spec file and case name.

        Returns:
            (spec path, 0, "spec: <case>").

        """
        return self.path, 0, f"spec: {self.name}"


class SpecFile(pytest.File):
    """A `.rego` spec; its items are the cases in its `.cases.json`."""

    def collect(self) -> list[SpecItem]:
        """Yield one item per case.

        ⚑ Absent or malformed case data — including a malformed disposition — is a collection
        ERROR, not zero items, so a spec with bad data is never a clean run.

        Returns:
            the items, in case-data order.

        """
        try:
            cases = load_cases(self.path)
            names = frozenset(name for name, _ in cases)
            declared = [(name, case, disposition_of(name, case, names)) for name, case in cases]
        except SpecDataError as exc:
            raise self.CollectError(str(exc)) from exc
        return [
            SpecItem.from_parent(self, name=name, case=case, disposition=disposition)
            for name, case, disposition in declared
        ]


def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> SpecFile | None:
    """Claim a `.rego` spec for collection.

    Returns:
        a SpecFile for a claimed path, else None (pytest's own collectors decide).

    """
    if claims(file_path):
        return SpecFile.from_parent(parent, path=file_path)
    return None


def _not_ported(item: pytest.Item) -> bool:
    """Decide whether an item is a declared do-not-port case.

    Returns:
        True for a SpecItem whose disposition is do-not-port.

    """
    return (
        isinstance(item, SpecItem)
        and item.disposition is not None
        and item.disposition.kind == DO_NOT_PORT
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Deselect every do-not-port case; pytest's `deselected` count reports them."""
    _count_declarations(config, items)
    dropped = [item for item in items if _not_ported(item)]
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = [item for item in items if not _not_ported(item)]


def pytest_addhooks(pluginmanager: pytest.PytestPluginManager) -> None:
    """Declare `pytest_spec_implementations`, so a conftest can offer adapters (W202)."""
    pluginmanager.add_hookspecs(adapters)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add `--impl NAME`: which offered implementation fills each case's `result`."""
    parser.addoption(
        "--impl",
        default=None,
        help="fill each case's result by running this implementation on its fixture",
    )


# ⚑ THE HOOKSPEC IS ALSO THIS PLUGIN'S OWN IMPLEMENTATION: it offers no adapters, so the hook
# always answers, and its body is exercised on every `--impl` run rather than never called.
pytest_spec_implementations = adapters.pytest_spec_implementations


# ⚑ THE DIFFERENTIAL LINE (W203): one row per spec, every column always printed, so a run's
# differential is a single greppable line and a zero is stated rather than implied.
COLUMNS = ("admitted", "denied", "unmeasured", DO_NOT_PORT, PORT_FIX)
TALLY = pytest.StashKey[dict[str, dict[str, int]]]()


def _tally(config: pytest.Config, nodeid: str) -> dict[str, int] | None:
    """Find the counts of the spec a node belongs to.

    Returns:
        the spec's counts, or None for a node that is not a spec case.

    """
    return config.stash.get(TALLY, {}).get(nodeid.split("::", 1)[0])


def _count_declarations(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Open a tally for every collected spec and count its declared dispositions."""
    tallies = config.stash.setdefault(TALLY, {})
    for item in items:
        if not isinstance(item, SpecItem):
            continue
        counts = tallies.setdefault(item.nodeid.split("::", 1)[0], dict.fromkeys(COLUMNS, 0))
        kind = item.disposition.kind if item.disposition is not None else None
        if kind in {DO_NOT_PORT, PORT_FIX}:
            counts[kind] += 1


def _outcome(report: pytest.TestReport) -> str | None:
    """Classify one report of a spec case.

    Returns:
        admitted, denied or unmeasured; None for a phase that decides nothing.

    """
    if report.when != "call" and report.passed:
        return None
    if report.passed:
        return "admitted"
    if report.skipped:
        # A declared unmeasured case reports as xfail, which pytest files under skipped.
        return "unmeasured"
    return "denied" if "DENIED" in report.longreprtext else "unmeasured"


class _Differential:
    """Count each spec case's outcome, then print one differential line per spec.

    ⚑ A PLUGIN OBJECT, NOT A MODULE HOOK: `pytest_runtest_logreport` is not handed the config,
    and `pytest_report_teststatus` (which is) runs again for each `-r` summary line, so counting
    there would count a failure twice.
    """

    def __init__(self, config: pytest.Config) -> None:
        """Hold the session config, whose stash carries the tallies."""
        self.config = config

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Count one report into its spec's tally."""
        counts = _tally(self.config, report.nodeid)
        outcome = _outcome(report)
        if counts is not None and outcome is not None:
            counts[outcome] += 1

    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Print the differential line for every spec that collected a case."""
        impl = cast("object", self.config.getoption("impl"))
        shown = impl if isinstance(impl, str) else "as-written"
        for spec, counts in sorted(self.config.stash.get(TALLY, {}).items()):
            cells = " ".join(f"{column}={counts[column]}" for column in COLUMNS)
            terminalreporter.write_line(f"pytestspec: {spec} impl={shown} {cells}")


def pytest_configure(config: pytest.Config) -> None:
    """Register the differential counter for this session."""
    config.pluginmanager.register(_Differential(config), "pytestspec-differential")

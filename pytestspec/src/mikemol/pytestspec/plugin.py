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

⚑ A DECLARED UNMEASURED CASE IS STILL EVALUATED BY DEFAULT (W227, operator ruling (a)): strict
xfail over a real evaluation is the only thing that notices a declaration gone stale. The opt-in
`--skip-declared` skips the evaluation, and with it any `--impl` run, for a fast pass, and the
differential line counts each skipped case as `declared-skipped` so a declaration that was not
re-checked is never read as one that was.

⚑ `--result-cache DIR` REUSES AN `--impl` RESULT ONLY UNDER A KEY A CONFTEST VOUCHES FOR (W228,
see `cache`). A reused result is still judged by the spec, and the differential line counts it
as `cached`, so a result that was not recomputed is never read as one that was.
"""

from pathlib import Path
from typing import cast

import pytest

from mikemol.pytestspec import adapters, cache, opa
from mikemol.pytestspec.spec import (
    DO_NOT_PORT,
    PORT_FIX,
    UNMEASURED,
    Case,
    Disposition,
    Evaluator,
    SpecDataError,
    disposition_of,
    expectation,
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


def _skips(config: pytest.Config, disposition: Disposition | None) -> bool:
    """Decide whether `--skip-declared` spares this case its evaluation.

    Returns:
        True for a declared unmeasured case under `--skip-declared`.

    """
    chosen = cast("object", config.getoption("skip_declared")) is True
    return chosen and disposition is not None and disposition.kind == UNMEASURED


def _cache_root(config: pytest.Config) -> Path | None:
    """Read `--result-cache`.

    Returns:
        the cache directory, or None when caching was not asked for.

    """
    root = cast("object", config.getoption("result_cache"))
    return Path(root) if isinstance(root, str) else None


DATA_INI = "pytestspec_data"


def _declared_data(config: pytest.Config) -> tuple[Path, ...]:
    """Read the `pytestspec_data` ini key as declared, without checking the paths exist.

    Returns:
        the declared paths, resolved against the ini file's directory by pytest.

    """
    raw = cast("object", config.getini(DATA_INI))
    if not isinstance(raw, list):
        return ()
    return tuple(p for p in cast("list[object]", raw) if isinstance(p, Path))


def data_paths(config: pytest.Config) -> tuple[Path, ...]:
    """Read the `pytestspec_data` ini key: extra rego paths loaded beside every spec (W380).

    ⚑ EXPLICIT ONLY. A spec importing a shared helper (`data.el.truth`) fails to compile unless
    the helper is loaded too, and guessing at sibling directories would load whatever happens to
    sit there. A declared path that does not exist is an error, never a silent skip: a missing
    library would otherwise surface as every case failing to compile, far from its cause.

    Returns:
        the declared paths, resolved against the ini file's directory by pytest.

    Raises:
        SpecDataError: a declared path does not exist.

    """
    paths = _declared_data(config)
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        msg = f"{DATA_INI} names a path that does not exist: {', '.join(missing)}"
        raise SpecDataError(msg)
    return paths


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
            found = opa.evaluator(data=data_paths(self.config))
            self.config.stash[EVALUATOR] = found
        return found

    def _filled(self) -> Case:
        """Fill the case's `result` from the `--impl` implementation, if one was chosen.

        ⚑ The cache is consulted only after the impl and the fixture are known to exist, so a
        hit never hides the errors `adapters.fill` would have raised.

        Returns:
            the case as written without `--impl`; otherwise a copy carrying the chosen
            implementation's result, recomputed or (under a vouched-for key) reused.

        """
        name = cast("object", self.config.getoption("impl"))
        if not isinstance(name, str):
            return self.case
        offered = adapters.registered(self.config)
        root = _cache_root(self.config)
        key = None
        if root is not None and name in offered and "fixture" in self.case:
            key = cache.key_for(self.config, name, self.case)
        if root is not None and key is not None:
            hit, result = cache.load(root, name, key)
            if hit:
                counts = _tally(self.config, self.nodeid)
                if counts is not None:
                    counts[CACHED] += 1
                return {**self.case, "result": result}
        filled = adapters.fill(self.case, name, offered)
        if root is not None and key is not None:
            cache.store(root, name, key, filled["result"])
        return filled

    def runtest(self) -> None:
        """Evaluate the case and fail unless it is admitted.

        Raises:
            SpecFailedError: the case could not be evaluated, or its verdict is not admitted,
                or `--skip-declared` skipped a declared unmeasured case.

        """
        if _skips(self.config, self.disposition):
            msg = "DECLARED-SKIPPED (not evaluated): --skip-declared"
            raise SpecFailedError(msg)
        try:
            verdict = self._evaluator()(self.path, self._filled())
        except (opa.OpaUnavailableError, SpecDataError) as exc:
            msg = f"UNMEASURED (not evaluated, not passed): {exc}"
            raise SpecFailedError(msg) from exc
        expect = expectation(self.name, self.case)
        failure = judge(verdict, expect)
        if failure is not None:
            raise SpecFailedError(failure)
        if expect is not None:
            # ⚑ A PASS THAT RESTED ON AN EXPECTATION IS NOT AN ADMISSION, and which kind it
            # was is recorded so the differential line can say so (W372, W381).
            column = REFUSED if expect.deny else WITHHELD_EXPECTED
            self.user_properties.append((OUTCOME, column))

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
            data_paths(self.config)
            cases = load_cases(self.path)
            names = frozenset(name for name, _ in cases)
            declared = [(name, case, disposition_of(name, case, names)) for name, case in cases]
            for name, case in cases:
                expectation(name, case)
        except SpecDataError as exc:
            raise self.CollectError(str(exc)) from exc
        return [
            SpecItem.from_parent(self, name=name, case=case, disposition=disposition)
            for name, case, disposition in declared
        ]


def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> SpecFile | None:
    """Claim a `.rego` spec for collection.

    ⚑ A FILE UNDER A DECLARED `pytestspec_data` PATH IS A LIBRARY, NOT A SPEC (W380). Measured:
    without this, a helper package under the collected tree was claimed and ERRORED for having no
    case data, so declaring the library broke the run it was declared to fix.

    Returns:
        a SpecFile for a claimed path, else None (pytest's own collectors decide).

    """
    library = any(file_path.is_relative_to(p) for p in _declared_data(parent.config))
    if claims(file_path) and not library:
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
    """Declare the adapter (W202) and cache-key (W228) hooks a conftest may implement."""
    pluginmanager.add_hookspecs(adapters)
    pluginmanager.add_hookspecs(cache)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add `--impl NAME`, `--skip-declared`, and `--result-cache DIR`."""
    parser.addoption(
        "--impl",
        default=None,
        help="fill each case's result by running this implementation on its fixture",
    )
    parser.addoption(
        "--skip-declared",
        action="store_true",
        help="do not evaluate a declared unmeasured case (counted as declared-skipped)",
    )
    parser.addoption(
        "--result-cache",
        default=None,
        help="reuse --impl results stored here under a conftest's key (counted as cached)",
    )
    # ⚑ NO `default=`: an empty list literal reads as list[Any] under strict mypy, and the
    # `paths` type already defaults to an empty list.
    parser.addini(
        DATA_INI,
        type="paths",
        help="extra rego paths loaded beside every spec, for shared helper packages (W380)",
    )


# ⚑ THE HOOKSPECS ARE ALSO THIS PLUGIN'S OWN IMPLEMENTATIONS: it offers no adapters and vouches
# for no key, so each hook always answers, and its body runs on every session that asks.
pytest_spec_implementations = adapters.pytest_spec_implementations
pytest_spec_cache_key = cache.pytest_spec_cache_key


# ⚑ THE DIFFERENTIAL LINE (W203): one row per spec, every column always printed, so a run's
# differential is a single greppable line and a zero is stated rather than implied.
DECLARED_SKIPPED = "declared-skipped"
CACHED = "cached"
# ⚑ `refused` (W372): a case whose `expect` named exactly the rules that denied it. It passed, but
# it was not admitted, and folding it into `admitted` would hide the refusing half of the record.
REFUSED = "refused"
# ⚑ `withheld-expected` (W381): a case whose `expect` named exactly the rules that withheld it,
# and no deny. A could-not-measure arm that held, so neither an admission nor a refusal.
WITHHELD_EXPECTED = "withheld-expected"
# The user_properties key under which a passing expectation records its column.
OUTCOME = "pytestspec-outcome"
COLUMNS = (
    "admitted",
    "denied",
    REFUSED,
    WITHHELD_EXPECTED,
    "unmeasured",
    DO_NOT_PORT,
    PORT_FIX,
    DECLARED_SKIPPED,
    CACHED,
)
TALLY = pytest.StashKey[dict[str, dict[str, int]]]()
# ⚑ UNDER pytest-xdist (W316), every worker collects EVERY case, so a declaration is counted on
# each worker alike and is taken ONCE; a case runs on ONE worker, so outcomes are SUMMED.
_DECLARED = frozenset({DO_NOT_PORT, PORT_FIX, DECLARED_SKIPPED})
_WORKER_OUTPUT = "pytestspec-tally"


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
        if _skips(config, item.disposition):
            counts[DECLARED_SKIPPED] += 1


def _outcome(report: pytest.TestReport) -> str | None:
    """Classify one report of a spec case.

    Returns:
        admitted, denied or unmeasured; None for a phase that decides nothing.

    """
    if report.when != "call" and report.passed:
        return None
    if report.passed:
        recorded = dict(report.user_properties)
        column = recorded.get(OUTCOME)
        return column if isinstance(column, str) else "admitted"
    if report.skipped:
        # A declared unmeasured case reports as xfail, which pytest files under skipped.
        return "unmeasured"
    text = report.longreprtext
    return "denied" if "DENIED" in text or "DENY MISMATCH" in text else "unmeasured"


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
        """Count one report into its spec's tally, where the case ran.

        ⚑ A report a worker FORWARDED to the xdist controller carries `node`. The worker counted
        it already and hands its tally over at `pytest_testnodedown`, so the controller counting
        it too would double it once the first worker's tally has opened that spec's row.
        """
        counts = _tally(self.config, report.nodeid)
        outcome = _outcome(report)
        forwarded = cast("object", getattr(report, "node", None)) is not None
        if counts is not None and outcome is not None and not forwarded:
            counts[outcome] += 1

    def pytest_sessionfinish(self) -> None:
        """On an xdist worker, hand this worker's tallies to the controller."""
        output = cast("object", getattr(self.config, "workeroutput", None))
        if isinstance(output, dict):
            tallies = self.config.stash.get(TALLY, {})
            cast("dict[str, object]", output)[_WORKER_OUTPUT] = {
                spec: dict(counts) for spec, counts in tallies.items()
            }

    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Print the differential line for every spec that collected a case."""
        impl = cast("object", self.config.getoption("impl"))
        shown = impl if isinstance(impl, str) else "as-written"
        for spec, counts in sorted(self.config.stash.get(TALLY, {}).items()):
            cells = " ".join(f"{column}={counts[column]}" for column in COLUMNS)
            terminalreporter.write_line(f"pytestspec: {spec} impl={shown} {cells}")


class _XdistMerge:
    """Merge each finished worker's tallies on the xdist controller (W316).

    ⚑ ITS OWN PLUGIN, REGISTERED ONLY WHEN xdist IS LOADED: `pytest_testnodedown` is xdist's
    hook, and a plugin implementing a hook with no spec is a pytest error without it.
    """

    def __init__(self, config: pytest.Config) -> None:
        """Hold the controller's config, whose stash the merged tallies go into."""
        self.config = config

    def pytest_testnodedown(self, node: object) -> None:
        """Merge one worker: declarations taken once (each worker saw them all), outcomes summed."""
        output = cast("object", getattr(node, "workeroutput", None))
        received = (
            cast("dict[str, object]", output).get(_WORKER_OUTPUT)
            if isinstance(output, dict)
            else None
        )
        if not isinstance(received, dict):
            return
        tallies = self.config.stash.setdefault(TALLY, {})
        for spec, counts in cast("dict[str, dict[str, int]]", received).items():
            mine = tallies.setdefault(spec, dict.fromkeys(COLUMNS, 0))
            for column in COLUMNS:
                if column in _DECLARED:
                    mine[column] = max(mine[column], counts.get(column, 0))
                else:
                    mine[column] += counts.get(column, 0)


def pytest_configure(config: pytest.Config) -> None:
    """Register the differential counter, and the worker merge when xdist runs this session."""
    config.pluginmanager.register(_Differential(config), "pytestspec-differential")
    if config.pluginmanager.hasplugin("xdist"):
        config.pluginmanager.register(_XdistMerge(config), "pytestspec-xdist-merge")

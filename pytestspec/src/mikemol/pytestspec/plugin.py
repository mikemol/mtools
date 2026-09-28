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

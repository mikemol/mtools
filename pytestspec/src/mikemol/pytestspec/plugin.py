# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pytest11 entry point: a `.rego` spec collects one item per case in its case data.

⚑ THE EVALUATOR IS READ FROM `config.stash[EVALUATOR]` (W199). With none configured, every item
FAILS: a spec that cannot be evaluated has measured nothing, and that must not read as a pass or
a skip. W200 installs the pinned opa evaluator as the default.
"""

from pathlib import Path

import pytest

from mikemol.pytestspec.spec import Case, Evaluator, SpecDataError, judge, load_cases

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

    def __init__(self, *, name: str, parent: pytest.Collector, case: Case) -> None:
        """Hold the case this item evaluates."""
        super().__init__(name=name, parent=parent)
        self.case = case

    def runtest(self) -> None:
        """Evaluate the case and fail unless it is admitted.

        Raises:
            SpecFailedError: no evaluator is configured, or the verdict is not admitted.

        """
        evaluator = self.config.stash.get(EVALUATOR, None)
        if evaluator is None:
            msg = "NO EVALUATOR configured: the case was not evaluated, so it is not passed"
            raise SpecFailedError(msg)
        failure = judge(evaluator(self.path, self.case))
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

        ⚑ Absent or malformed case data is a collection ERROR, not zero items, so a spec with no
        data is never a clean run.

        Returns:
            the items, in case-data order.

        """
        try:
            cases = load_cases(self.path)
        except SpecDataError as exc:
            raise self.CollectError(str(exc)) from exc
        return [SpecItem.from_parent(self, name=name, case=case) for name, case in cases]


def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> SpecFile | None:
    """Claim a `.rego` spec for collection.

    Returns:
        a SpecFile for a claimed path, else None (pytest's own collectors decide).

    """
    if claims(file_path):
        return SpecFile.from_parent(parent, path=file_path)
    return None

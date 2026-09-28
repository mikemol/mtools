# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Implementation adapters (W202): the subject or the reference fills a case's `result`.

⚑ CASE DATA KEEPS THE FIXTURE AND OPERANDS, NOT A FROZEN RESULT. A frozen result pins what one
implementation said once; an adapter re-runs an implementation on every session, so the same
spec can judge the origin (`--impl reference`) and the port (`--impl subject`) alike.

With no `--impl`, a case is evaluated as written, so a case carrying a precomputed `result`
still works (W200).
"""

from collections.abc import Callable
from typing import cast

import pluggy
import pytest

from mikemol.pytestspec.spec import Case, SpecDataError

hookspec = pluggy.HookspecMarker("pytest")

# Run one implementation on a case's fixture and operands; its output becomes the `result`.
type Adapter = Callable[[object, object], object]


@hookspec
def pytest_spec_implementations() -> dict[str, Adapter]:
    """Name the implementations a plugin or conftest offers, as {name: adapter}.

    Returns:
        the offered adapters. The plugin registers this function as its own hookimpl, so
        every session offers at least this empty table.

    """
    return {}


def registered(config: pytest.Config) -> dict[str, Adapter]:
    """Collect every offered adapter by name.

    Returns:
        {name: adapter} across all plugins and conftests.

    Raises:
        SpecDataError: two plugins offer the same name, so which one ran would be an accident.

    """
    found: dict[str, Adapter] = {}
    for table in cast("list[object]", config.hook.pytest_spec_implementations()):
        if not isinstance(table, dict):
            continue
        for name, impl in cast("dict[object, object]", table).items():
            if not isinstance(name, str) or not callable(impl):
                continue
            if name in found:
                msg = f"two plugins offer an implementation named {name!r}"
                raise SpecDataError(msg)
            found[name] = cast("Adapter", impl)
    return found


def fill(case: Case, name: str, adapters: dict[str, Adapter]) -> Case:
    """Run the named implementation on the case and put its output in `result`.

    Returns:
        a copy of the case whose `result` is the implementation's output.

    Raises:
        SpecDataError: no implementation has that name, or the case has no `fixture`.

    """
    adapter = adapters.get(name)
    if adapter is None:
        offered = ", ".join(sorted(adapters)) or "none"
        msg = f"--impl {name}: no implementation by that name (offered: {offered})"
        raise SpecDataError(msg)
    if "fixture" not in case:
        msg = f"--impl {name}: the case carries no `fixture` to run"
        raise SpecDataError(msg)
    return {**case, "result": adapter(case["fixture"], case.get("operands"))}

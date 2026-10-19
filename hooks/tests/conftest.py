# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Test-suite configuration for `mikemol-hooks`.

⚑ IT MARKS `tests/` AS A COLLECTION ROOT rather than a stray namespace directory, which is the half
of the `INP001` answer that belongs in the tree; the other half is the `namespace-packages` entry
in `pyproject.toml`.

⚑ IT SKIPS THE CHECKOUT-TIED MODULES IN AN UNPACKED SDIST (W1239): there is no repository above the
distribution there, and `mikemol.hooks.hosttied` names the modules that test the checkout's own
hooks and scripts. They are skipped with a stated reason in an sdist (which carries `PKG-INFO` at
its top) and run everywhere else, so the gate and the mutation sandbox lose nothing.

⚑ IT RUNS EVERY IN-PROCESS `main` AS THE HOLDER OF THE FENCE LEASE (W1696). A commit that cannot
take the lease refuses, and one that can `execve`s into the fence, which would replace the test
process. The tests of `main` are about what it does once it holds the lease; the claim itself is
tested with an explicit environment in `test_commit_claim`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import hosttied

if TYPE_CHECKING:
    from collections.abc import Sequence

IN_SDIST = (Path(__file__).parents[1] / hosttied.SDIST_MARKER).is_file()
HELD_ENV = "MIKEMOL_COMMIT_LOCK_HELD"


def pytest_configure(config: pytest.Config) -> None:
    """Mark the test process as already holding the commit lease."""
    del config
    os.environ.setdefault(HELD_ENV, "1")


def pytest_collection_modifyitems(items: Sequence[pytest.Item]) -> None:
    """Skip each host-tied module's tests when this is an unpacked sdist."""
    for item in items:
        reason = hosttied.skip_reason(item.path.stem, in_sdist=IN_SDIST)
        if reason is not None:
            item.add_marker(pytest.mark.skip(reason=reason))

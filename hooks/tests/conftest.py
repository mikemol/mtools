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
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import hosttied

if TYPE_CHECKING:
    from collections.abc import Sequence

IN_SDIST = (Path(__file__).parents[1] / hosttied.SDIST_MARKER).is_file()


def pytest_collection_modifyitems(items: Sequence[pytest.Item]) -> None:
    """Skip each host-tied module's tests when this is an unpacked sdist."""
    for item in items:
        reason = hosttied.skip_reason(item.path.stem, in_sdist=IN_SDIST)
        if reason is not None:
            item.add_marker(pytest.mark.skip(reason=reason))

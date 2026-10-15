# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that host-tied hooks tests are skipped only in an unpacked sdist, and with a reason.

W1239. ⚑ THE CONTROLS: outside an sdist (the checkout, bazel, the mutation sandbox) nothing is
skipped, so no module can be quietly dropped from the gate; in one, only a named module is skipped
and an unnamed one still runs; every named module is a real test file in this directory, so a
rename cannot leave a stale name that skips nothing. (Whether THIS run skipped anything is read
from the gate's pass counts, not asserted here: the same file runs inside an sdist, where
skipping is the point.)
"""

from __future__ import annotations

from pathlib import Path

from mikemol.hooks import hosttied

_TESTS = Path(__file__).parent


def test_outside_an_sdist_no_module_is_skipped() -> None:
    """Every named module still runs when this is not an unpacked sdist."""
    for module in hosttied.HOST_TIED:
        assert hosttied.skip_reason(module, in_sdist=False) is None


def test_in_an_sdist_a_named_module_is_skipped_with_the_reason() -> None:
    """A host-tied module gets the stated reason; an unnamed one gets none."""
    assert hosttied.skip_reason("test_bar_fires", in_sdist=True) == hosttied.REASON
    assert hosttied.skip_reason("test_hosttied", in_sdist=True) is None
    assert hosttied.skip_reason("test_vlogship", in_sdist=True) is None


def test_every_named_module_is_a_test_file_here() -> None:
    """A stale name would skip nothing and hide a rename."""
    missing = sorted(m for m in hosttied.HOST_TIED if not (_TESTS / f"{m}.py").is_file())
    assert missing == []

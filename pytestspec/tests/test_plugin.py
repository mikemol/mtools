# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The plugin's claim: which files are specs."""

from pathlib import Path

from mikemol.pytestspec import plugin


def test_a_rego_file_is_claimed() -> None:
    """A `.rego` file is a spec the plugin claims."""
    assert plugin.claims(Path("specs/guarded.rego"))


def test_opa_test_file_is_not_claimed() -> None:
    """A `_test.rego` file is opa's own unit test, run by `opa test`, not a spec."""
    assert not plugin.claims(Path("specs/guarded_test.rego"))


def test_python_file_is_not_claimed() -> None:
    """A `.py` file is left to pytest's own collector."""
    assert not plugin.claims(Path("tests/test_plugin.py"))

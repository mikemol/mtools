# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.corpus.suite_pragmas`: substrate's suite cases, ported.

substrate's tenant set (`sandbox`, `live`) is now the caller's `admitted` argument; these cases
pass it explicitly, and one arm shows a different caller's set is honoured instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.corpus import suite_pragmas

if TYPE_CHECKING:
    from pathlib import Path

_SUBSTRATE_TENANTS = ("sandbox", "live")


def _write(tmp_path: Path, src: str) -> str:
    """Write a fixture suite.

    Returns:
        its path.

    """
    path = tmp_path / "suite.py"
    path.write_text(src, encoding="utf-8")
    return str(path)


def test_the_dependency_pragma_is_read_wherever_it_sits(tmp_path: Path) -> None:
    """One or several comma-separated deps are read, trimmed, even below code.

    ⚑ The pragma is a comment anywhere in the file, not a header: a suite that grew one later
    should not have to move it.
    """
    cases = (
        ("# selftest-requires: numpy\n", ("numpy",)),
        ("# selftest-requires: numpy, scipy\n", ("numpy", "scipy")),
        ("# selftest-requires:   numpy ,  scipy  \n", ("numpy", "scipy")),
        ("x = 1\n# selftest-requires: panflute\n", ("panflute",)),
    )
    for src, want in cases:
        assert suite_pragmas.requires(_write(tmp_path, src)) == want


def test_no_dependency_pragma_is_empty_not_an_error(tmp_path: Path) -> None:
    """A suite that declares no dependency yields an empty tuple."""
    assert suite_pragmas.requires(_write(tmp_path, "print('hi')\n")) == ()


def test_an_admitted_tenant_becomes_its_flag(tmp_path: Path) -> None:
    """`sandbox` and `live`, admitted, declare `--sandbox` and `--live`."""
    for name in _SUBSTRATE_TENANTS:
        path = _write(tmp_path, f"# selftest-tenant: {name}\n")
        assert suite_pragmas.tenant(path, admitted=_SUBSTRATE_TENANTS) == f"--{name}"


def test_a_typo_or_unadmitted_tenant_declares_nothing(tmp_path: Path) -> None:
    """A misspelled or unknown tenant, no pragma, or an env-var tenant all declare nothing.

    ⚑⚑ The load-bearing arm: a misspelled tenant must declare NOTHING, so the runner never
    invents a tenant from a typo and reads plausible rows from a store nobody chose.
    """
    for src in (
        "# selftest-tenant: sandbxo\n",
        "# selftest-tenant: production\n",
        "print('hi')\n",
        "import os\nos.environ['SUBSTRATE_STORE'] = 'sandbox'\n",
    ):
        assert suite_pragmas.tenant(_write(tmp_path, src), admitted=_SUBSTRATE_TENANTS) is None


def test_the_admitted_tenants_are_the_callers(tmp_path: Path) -> None:
    """Another caller's set is honoured, and substrate's names are not built in.

    ⚑ substrate's `sandbox`/`live` is its store policy; a shared reader that hard-coded it would
    refuse every other repo's tenants and accept substrate's everywhere.
    """
    path = _write(tmp_path, "# selftest-tenant: staging\n")
    assert suite_pragmas.tenant(path, admitted=("staging",)) == "--staging"
    live = _write(tmp_path, "# selftest-tenant: live\n")
    assert suite_pragmas.tenant(live, admitted=("staging",)) is None


def test_an_unreadable_file_declares_nothing(tmp_path: Path) -> None:
    """A vanished file declares no deps and no tenant, rather than raising.

    ⚑ The runner asks every discovered file; the failure surfaces when the suite is RUN.
    """
    missing = str(tmp_path / "gone.py")
    assert suite_pragmas.requires(missing) == ()
    assert suite_pragmas.tenant(missing, admitted=_SUBSTRATE_TENANTS) is None

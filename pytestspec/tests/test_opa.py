# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pinned opa evaluator: its output parsing, and its refusal of an absent or wrong opa."""

from pathlib import Path

import pytest

from mikemol.pytestspec import opa
from mikemol.pytestspec.spec import SpecDataError, Verdict

_ADMITTED = '{"result": [{"expressions": [{"value": {"deny": [], "withheld": []}}]}]}'


def _fake_opa(tmp_path: Path, version: str) -> None:
    """Put an `opa` on PATH whose `version` prints the given version and nothing else."""
    script = tmp_path / "opa"
    script.write_text(f"#!/bin/sh\necho 'Version: {version}'\n", encoding="utf-8")
    script.chmod(0o700)


def test_an_admitted_result_carries_no_deny_or_withheld() -> None:
    """Empty `deny` and `withheld` sets parse to the admitted verdict."""
    assert opa.verdict_from(_ADMITTED) == Verdict()


def test_deny_messages_parse_sorted() -> None:
    """A Rego set has no order, so its messages are sorted before comparison."""
    out = '{"result": [{"expressions": [{"value": {"deny": ["b", "a"]}}]}]}'
    assert opa.verdict_from(out) == Verdict(deny=("a", "b"))


def test_empty_result_is_withheld_not_admitted() -> None:
    """An empty result object (the package is undefined) is WITHHELD: nothing was measured."""
    verdict = opa.verdict_from("{}")
    assert verdict.withheld
    assert not verdict.deny


def test_a_package_without_deny_is_withheld() -> None:
    """A package document with no `deny` key (no rule could deny) is WITHHELD, not admitted."""
    verdict = opa.verdict_from('{"result": [{"expressions": [{"value": {}}]}]}')
    assert verdict.withheld
    assert not verdict.deny


def test_package_is_read_from_the_spec(tmp_path: Path) -> None:
    """The query path is the spec's own `package` line."""
    spec = tmp_path / "s.rego"
    spec.write_text("# c\npackage pycodemod.guarded\n", encoding="utf-8")
    assert opa.package_of(spec) == "pycodemod.guarded"


def test_spec_without_package_is_refused(tmp_path: Path) -> None:
    """A spec with no `package` line cannot be queried, and says so."""
    spec = tmp_path / "s.rego"
    spec.write_text("deny contains 1 if true\n", encoding="utf-8")
    with pytest.raises(SpecDataError, match="no `package` line"):
        opa.package_of(spec)


def test_absent_opa_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With no opa on PATH, resolution FAILS; it never falls through to a skip."""
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(opa.OpaUnavailableError, match="not found on PATH"):
        opa.resolve()


def test_wrong_version_opa_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An opa that is not the pinned version is a different checker, and is refused."""
    _fake_opa(tmp_path, "0.0.1")
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(opa.OpaUnavailableError, match="not the pinned"):
        opa.resolve()


def test_pinned_version_opa_is_accepted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The pinned version resolves to its absolute path (the P-arm of the version check)."""
    _fake_opa(tmp_path, opa.PINNED)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert opa.resolve() == str(tmp_path / "opa")

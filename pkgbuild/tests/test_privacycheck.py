# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the three states of `privacycheck.check` (W1199).

⚑ THE JUDGE IS A PARAMETER (or `MIKEMOL_PRIVACY_SHIPPED`), so each state is reached by a stub that
stands in for `mikemol-privacy-shipped`. The real judge over real artifacts is in the hooks dist's
own tests; this module only proves how its exit status becomes a state.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.pkgbuild import privacycheck

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_OWNER_ONLY = 0o700
_USAGE = 2


def _stub(tmp_path: Path, body: str) -> str:
    """Write an executable Python script that stands in for the judge.

    Returns:
        its path.

    """
    script = tmp_path / "judge"
    script.write_text(f"#!{sys.executable}\nimport sys\n{body}\n", encoding="utf-8")
    script.chmod(_OWNER_ONLY)
    return str(script)


def test_a_judge_that_passes_is_ok_and_is_given_every_artifact_in_order(tmp_path: Path) -> None:
    """Exit 0 is `ok`, and the arguments are the artifact paths, sdist first."""
    stub = _stub(tmp_path, "print(' '.join(sys.argv[1:]))")
    state, text = privacycheck.check([tmp_path / "a.tar.gz", tmp_path / "b.whl"], tool=stub)
    assert state == "ok"
    assert text == f"{tmp_path / 'a.tar.gz'} {tmp_path / 'b.whl'}"


def test_a_judge_that_finds_something_is_failed_with_its_output(tmp_path: Path) -> None:
    """Exit 1 is `failed` and the finding lines reach the row."""
    body = 'print(\'{"rule": "env-file"}\')\nsys.exit(1)'
    state, text = privacycheck.check([tmp_path / "a.whl"], tool=_stub(tmp_path, body))
    assert state == "failed"
    assert "env-file" in text


def test_a_judge_that_has_no_opa_is_unavailable_not_failed_and_not_ok(tmp_path: Path) -> None:
    """The control: exit 2 is the judge saying it could not judge, which is not a verdict."""
    stub = _stub(tmp_path, f"sys.stderr.write('usage\\n')\nsys.exit({_USAGE})")
    state, text = privacycheck.check([tmp_path / "a.whl"], tool=stub)
    assert state == "unavailable"
    assert "usage" in text


def test_no_tool_named_and_a_missing_tool_are_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The environment names nothing, or names a path that is no program."""
    monkeypatch.delenv(privacycheck.TOOL_ENV, raising=False)
    state, text = privacycheck.check([tmp_path / "a.whl"])
    assert state == "unavailable"
    assert privacycheck.TOOL_ENV in text
    state, text = privacycheck.check([tmp_path / "a.whl"], tool=str(tmp_path / "absent"))
    assert state == "unavailable"
    assert "absent" in text


def test_the_tool_is_read_from_the_environment_when_not_passed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`MIKEMOL_PRIVACY_SHIPPED` is the tool when no parameter is given."""
    monkeypatch.setenv(privacycheck.TOOL_ENV, _stub(tmp_path, "print('seen')"))
    assert privacycheck.check([tmp_path / "a.whl"]) == ("ok", "seen")

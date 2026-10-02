# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""reqs_check against hand-built distributions: agreement passes, and each drift is named."""

from __future__ import annotations

from typing import TYPE_CHECKING

import reqs_check

if TYPE_CHECKING:
    from pathlib import Path

_LOCK = (
    'version = 1\n\n[[package]]\nname = "ast-serialize"\nversion = "0.11.1"\n\n'
    '[[package]]\nname = "Typing_Extensions"\nversion = "4.16.0"\n'
)
_AGREE = "# header\nast_serialize==0.11.1 \\\n    --hash=sha256:00\ntyping-extensions==4.16.0\n"


def _dist(root: Path, req: str | None, lock: str | None) -> Path:
    if req is not None:
        (root / "requirements.txt").write_text(req, encoding="utf-8")
    if lock is not None:
        (root / "uv.lock").write_text(lock, encoding="utf-8")
    return root


def test_agreeing_pins_have_no_findings(tmp_path: Path) -> None:
    """The positive control: every pin matches the lock, with names compared PEP 503 normalized."""
    assert reqs_check.check(_dist(tmp_path, _AGREE, _LOCK)) == []


def test_a_header_only_requirements_file_agrees(tmp_path: Path) -> None:
    """A distribution with no runtime pins has nothing to disagree about, given a non-empty lock."""
    assert reqs_check.check(_dist(tmp_path, "# no runtime deps\n", _LOCK)) == []


def test_a_disagreeing_pin_is_named_with_both_versions(tmp_path: Path) -> None:
    """The W234 drift: a requirements pin behind the lock is one finding naming both versions."""
    [finding] = reqs_check.check(_dist(tmp_path, "ast-serialize==0.9.0\n", _LOCK))
    assert finding.endswith("ast-serialize==0.9.0 but uv.lock has 0.11.1")


def test_a_pin_the_lock_lacks_is_named(tmp_path: Path) -> None:
    """A pin with no package of that name in the lock is a finding, not skipped as unknown."""
    [finding] = reqs_check.check(_dist(tmp_path, "ruff==0.16.6\n", _LOCK))
    assert finding.endswith("ruff==0.16.6 is absent from uv.lock")


def test_a_missing_file_is_named(tmp_path: Path) -> None:
    """A distribution lacking either file is a finding per file, never a silent pass."""
    findings = reqs_check.check(_dist(tmp_path, None, None))
    names = [f.split(":", 1)[0].rsplit("/", 1)[-1] for f in findings]
    assert names == ["requirements.txt", "uv.lock"]


def test_an_empty_lock_is_refused_as_vacuous(tmp_path: Path) -> None:
    """A lock recording no package means the comparison never ran, so it is a finding."""
    [finding] = reqs_check.check(_dist(tmp_path, _AGREE, "version = 1\n"))
    assert "vacuous" in finding


def test_main_reports_exit_codes(tmp_path: Path) -> None:
    """0 on agreement, 1 on drift, 2 on a usage error."""
    good = tmp_path / "good"
    good.mkdir()
    bad = tmp_path / "bad"
    bad.mkdir()
    _dist(good, _AGREE, _LOCK)
    _dist(bad, "ast-serialize==0.9.0\n", _LOCK)
    codes = [reqs_check.main([str(good)]), reqs_check.main([str(bad)]), reqs_check.main([])]
    assert codes == [0, 1, 2]

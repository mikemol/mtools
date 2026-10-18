# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A venv whose copy of mikemol.endpoints is not the checkout's says so once on stderr (W1532)."""

from pathlib import Path

from mikemol.otlp import staleness

_REL = Path("endpoints") / "src" / "mikemol" / "endpoints" / "resolve.py"


def _checkout(tmp_path: Path, text: str) -> Path:
    source = tmp_path / "repo" / _REL
    source.parent.mkdir(parents=True)
    source.write_text(text, encoding="utf-8")
    here = tmp_path / "repo" / "otlp" / "src" / "mikemol" / "otlp" / "staleness.py"
    here.parent.mkdir(parents=True)
    here.write_text("", encoding="utf-8")
    return here


def _installed(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "venv" / "site-packages" / "mikemol" / "endpoints" / "resolve.py"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_copy_that_differs_from_the_checkouts_is_named_with_the_fix(tmp_path: Path) -> None:
    """The 2026-10-18 failure: the child kept the old resolver and nothing said so."""
    here = _checkout(tmp_path, "new resolver\n")
    got = staleness.stale(_installed(tmp_path, "old resolver\n"), here)
    assert got is not None
    assert "differs from the checkout's" in got
    assert "--reinstall-package mikemol-endpoints" in got


def test_an_identical_copy_says_nothing(tmp_path: Path) -> None:
    """The refreshed venv is silent."""
    here = _checkout(tmp_path, "same\n")
    assert staleness.stale(_installed(tmp_path, "same\n"), here) is None


def test_no_checkout_above_or_no_installed_file_says_nothing(tmp_path: Path) -> None:
    """A wheel installed elsewhere has no endpoints source above it, so nothing is compared."""
    lone = tmp_path / "elsewhere" / "staleness.py"
    lone.parent.mkdir()
    lone.write_text("", encoding="utf-8")
    assert staleness.checkout_copy(lone) is None
    assert staleness.stale(_installed(tmp_path, "x\n"), lone) is None
    here = _checkout(tmp_path / "other", "y\n")
    assert staleness.stale(tmp_path / "missing.py", here) is None

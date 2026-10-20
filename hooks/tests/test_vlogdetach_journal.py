# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A detached telemetry child that cannot deliver is heard in the journal, not lost (W1744)."""

import pytest

from mikemol.hooks import vlogdetach

_ARGV = ["/bin/otlp", "metric", "--service", "mikemol-gate"]
_CAT = "/usr/bin/systemd-cat"


def _with_cat(_name: str) -> str:
    return _CAT


def _without_cat(_name: str) -> None:
    return None


def test_with_systemd_cat_the_child_runs_under_it_so_its_output_reaches_the_journal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wrapper names the journal tag and a warning level, then the child's own argv."""
    monkeypatch.setattr("shutil.which", _with_cat)
    assert vlogdetach.journaled(_ARGV) == [_CAT, "-t", vlogdetach.TAG, "-p", "warning", *_ARGV]


def test_without_systemd_cat_the_child_runs_bare_as_before(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No journal tool to wrap with: the argv is unchanged and nothing is guessed."""
    monkeypatch.setattr("shutil.which", _without_cat)
    assert vlogdetach.journaled(_ARGV) == _ARGV

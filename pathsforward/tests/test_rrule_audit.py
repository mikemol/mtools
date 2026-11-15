# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The RRULE dry run reads every queue under a root and names the disagreements (W1259)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import rrule_audit

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_GOOD = "FREQ=MONTHLY;BYMONTHDAY=1"
_ONLY_OURS = "FREQ=DAILY;BYSECOND=60"


def _repo(root: Path, name: str, rules: dict[str, str]) -> None:
    waypoints = [{"symbol": symbol, "rrule": rule} for symbol, rule in rules.items()]
    path = root / name / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    body: dict[str, object] = {"waypoints": waypoints}
    path.write_text(json.dumps(body), encoding="utf-8")


def _oracle(accepted: set[str]) -> Callable[[str], bool]:
    def reference(rule: str) -> bool:
        return rule in accepted

    return reference


def test_agreement_is_silent_and_each_disagreement_is_named_with_its_repo_and_card(
    tmp_path: Path,
) -> None:
    """The control passes; a rule only we accept is one line, repos in name order."""
    _repo(tmp_path, "b", {"W2": _ONLY_OURS})
    _repo(tmp_path, "a", {"W1": _GOOD})
    got = rrule_audit.audit(tmp_path, _oracle({_GOOD}))
    assert got == [f"b:W2 {_ONLY_OURS!r}: we accept, the reference rejects"]


def test_a_missing_or_torn_queue_adds_nothing_and_the_audit_writes_nothing(tmp_path: Path) -> None:
    """Unreadable is not a finding; a directory with no queue is skipped; the tree is untouched."""
    (tmp_path / "empty").mkdir()
    torn = tmp_path / "torn" / ".claude"
    torn.mkdir(parents=True)
    (torn / "paths-forward.json").write_text("{", encoding="utf-8")
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    assert rrule_audit.audit(tmp_path, _oracle(set())) == []
    assert sorted(str(p) for p in tmp_path.rglob("*")) == before

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A waiter on a held claim is told WHO holds it, not how much capacity is free (W885)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from mikemol.fence import admit

if TYPE_CHECKING:
    from pathlib import Path

_TOTAL = 8
_AGE_S = 30
_PARENT_VAR = "MEMBUDGET_PARENT"
_CLAIM = "claim:path:/repo/.git/mtools/commit"


@pytest.fixture()
def top_level(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every arm as a top-level request, whatever membudget the suite runs under."""
    monkeypatch.delenv(_PARENT_VAR, raising=False)


pytestmark = pytest.mark.usefixtures("top_level")


def _held(label: str = _CLAIM, *, epoch: int = 0, owner: str = "42:777") -> admit.Ledger:
    """Return a snapshot in which `owner` holds `label` since `epoch`.

    Returns:
        the snapshot.

    """
    lease = admit.Lease("abc123", 0, owner, epoch, admit.NO_PARENT, label)
    return admit.Ledger(_TOTAL, (lease,), total_lines=1)


def test_the_note_names_the_owner_the_lease_and_the_age() -> None:
    """The sentence a person waiting on a commit can act on: who, which lease, how long."""
    note = admit.holder_note(_held(epoch=100), admit.Request(0, _CLAIM), 100 + _AGE_S)
    assert note is not None
    assert "42:777" in note
    assert "abc123" in note
    assert f"for {_AGE_S} s" in note


def test_a_request_with_no_claim_gets_no_note() -> None:
    """A capacity wait keeps its capacity line: only a claim names a holder."""
    assert admit.holder_note(_held(), admit.Request(1, "run"), 0) is None


def test_an_unheld_claim_gets_no_note() -> None:
    """Nothing to name: a claim another label does not hold."""
    other = admit.Request(0, "claim:path:/elsewhere")
    assert admit.holder_note(_held(), other, 0) is None


def test_the_age_never_reads_negative() -> None:
    """A holder stamped after the waiter's clock (skew) reads as zero seconds, not a minus."""
    note = admit.holder_note(_held(epoch=500), admit.Request(0, _CLAIM), 100)
    assert note is not None
    assert "for 0 s" in note


def test_a_blocked_claim_announces_its_holder(tmp_path: Path) -> None:
    """The real wait: B asks for A's claim, is told A holds it, and is admitted once A releases."""
    store = admit.Store(tmp_path / "ledger")
    admit.init(store, _TOTAL)
    quiet = admit.Host(loadavg=lambda: (0.0, 0.0, 0.0))
    holder = admit.acquire(store, admit.Request(0, _CLAIM), host=quiet)
    heard: list[str] = []

    def release_then_sleep(_seconds: float) -> None:
        admit.release(store, holder)

    host = admit.Host(
        loadavg=quiet.loadavg, sleep=release_then_sleep, announce=heard.append, clock=time.monotonic
    )
    waiter = admit.acquire(store, admit.Request(0, _CLAIM), host=host)
    assert len(heard) == 1
    assert holder.owner in heard[0]
    assert holder.lease_id in heard[0]
    assert [item.lease_id for item in store.read().leases] == [waiter.lease_id]

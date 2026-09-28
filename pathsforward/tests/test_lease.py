# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for W177's leases: artifact writes only, all or nothing, renewed, lapse reported."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mikemol.pathsforward import lease
from mikemol.pathsforward.lock import stamp
from mikemol.pathsforward.model import State, validate

_NOW = datetime(2026, 9, 28, 12, 0, 0, tzinfo=UTC)
_LATER = _NOW + timedelta(minutes=10)
_PAST_TTL = _NOW + timedelta(seconds=lease.LEASE_TTL_S + 1)
_OPS = "file:pathsforward/src/mikemol/pathsforward/ops.py!w"
_TWO = 2


def _state() -> State:
    """Build an empty state.

    Returns:
        the state.

    """
    return validate({"counter": 0, "waypoints": [], "residue": []})


def test_only_artifact_writes_are_leased() -> None:
    """A read, a topic and a party tag lease nothing; the `!w` artifact tag is leased."""
    state = _state()
    touches = [_OPS, "file:README.md", "gate", "party:summit", "mod:display_types!w"]
    assert lease.take(state, "W1", touches, lease.Claimant("tick-a", "abc", _NOW)) == []
    assert [x["tag"] for x in lease.leases(state)] == [_OPS, "mod:display_types!w"]


def test_a_second_waypoint_writing_the_same_artifact_is_refused_whole() -> None:
    """W2 wants ops.py (held) and a free tag: it gets neither, and the conflict names W1.

    ⚑ BOTH ARMS: W1's lease is taken first (the control), and W2's refusal writes nothing.
    """
    state = _state()
    assert lease.take(state, "W1", [_OPS], lease.Claimant("tick-a", "abc", _NOW)) == []
    before = list(lease.leases(state))
    got = lease.take(
        state, "W2", [f"file:./{_OPS[5:]}", "mod:x!w"], lease.Claimant("tick-b", "abc", _LATER)
    )
    assert got == [lease.Conflict(f"file:./{_OPS[5:]}", "W1", "tick-a")]
    assert lease.leases(state) == before


def test_a_read_of_a_leased_artifact_is_not_refused() -> None:
    """Two reads never collide, and a read never meets a write in the lease table."""
    state = _state()
    lease.take(state, "W1", [_OPS], lease.Claimant("tick-a", "abc", _NOW))
    assert lease.take(state, "W2", [_OPS[:-2]], lease.Claimant("tick-b", "abc", _NOW)) == []


def test_an_expired_lease_never_blocks() -> None:
    """Past its TTL, W1's lease no longer excludes W2."""
    state = _state()
    lease.take(state, "W1", [_OPS], lease.Claimant("tick-a", "abc", _NOW))
    assert lease.take(state, "W2", [_OPS], lease.Claimant("tick-b", "abc", _PAST_TTL)) == []


def test_retaking_renews_rather_than_duplicating() -> None:
    """The same waypoint taking again holds one lease per tag, stamped anew."""
    state = _state()
    lease.take(state, "W1", [_OPS], lease.Claimant("tick-a", "abc", _NOW))
    lease.take(state, "W1", [_OPS], lease.Claimant("tick-a", "abc", _LATER))
    held = lease.leases(state)
    assert [x["taken_at"] for x in held] == [stamp(_LATER)]


def test_release_drops_only_that_waypoints_leases() -> None:
    """Leaving `working` releases W1's leases and leaves W2's standing."""
    state = _state()
    lease.take(state, "W1", [_OPS, "mod:a!w"], lease.Claimant("tick-a", "abc", _NOW))
    lease.take(state, "W2", ["mod:b!w"], lease.Claimant("tick-a", "abc", _NOW))
    assert lease.release(state, "W1") == _TWO
    assert [x["waypoint"] for x in lease.leases(state)] == ["W2"]


def test_renew_extends_the_holders_leases_and_reports_a_moved_tree() -> None:
    """Renewal pushes expiry out for this holder only, and names tags whose base is not HEAD."""
    state = _state()
    lease.take(state, "W1", [_OPS], lease.Claimant("tick-a", "abc", _NOW))
    lease.take(state, "W2", ["mod:b!w"], lease.Claimant("tick-b", "abc", _NOW))
    assert lease.renew(state, "tick-a", "def", _LATER) == [_OPS]
    by_wp = {x["waypoint"]: x for x in lease.leases(state)}
    assert by_wp["W1"]["renewed_at"] == stamp(_LATER)
    assert by_wp["W2"]["renewed_at"] == stamp(_NOW)
    assert lease.renew(state, "tick-a", "abc", _LATER) == []


def test_lapsed_lists_what_passed_its_expiry() -> None:
    """Nothing lapses inside the TTL; past it, the lease is listed for the caller to ledger."""
    state = _state()
    lease.take(state, "W1", [_OPS], lease.Claimant("tick-a", "abc", _NOW))
    assert lease.lapsed(state, _LATER) == []
    assert [x["waypoint"] for x in lease.lapsed(state, _PAST_TTL)] == ["W1"]


def test_an_absent_or_malformed_field_reads_as_no_leases() -> None:
    """A state written before W177, or with a non-list field, has no leases and does not crash."""
    assert lease.leases(_state()) == []
    state = _state()
    state.doc["leases"] = "garbage"
    assert lease.leases(state) == []

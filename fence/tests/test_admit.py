# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The admission semaphore's pure half: the ledger, gc to a fixpoint, the verdict, the keyway.

⚑ EVERY ARM HERE IS A SNAPSHOT AND A VERDICT — no lock, no clock, no second process. The arms that
need those (blocking then proceeding, NOBLOCK, TIMEOUT, the claim race, gc-before-believing across
three roles) belong to the effectful half and land with it.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from mikemol.fence import admit

if TYPE_CHECKING:
    from pathlib import Path

_TOTAL = 512


def _lease(lease_id: str, mb: int, *, owner: str = "1:1", parent: str = admit.NO_PARENT,
           label: str = "run") -> admit.Lease:
    """Return a lease with defaults for the fields an arm does not care about.

    Returns:
        the lease.

    """
    return admit.Lease(lease_id, mb, owner, 0, parent, label)


def _ledger(*leases: admit.Lease, total: int | None = _TOTAL) -> admit.Ledger:
    """Return a snapshot holding `leases` under `total`.

    Returns:
        the snapshot.

    """
    return admit.Ledger(total, leases)


# --- the ledger text ---

def test_a_ledger_round_trips_through_its_text() -> None:
    """Rendering then parsing yields the same snapshot, a spaced label included."""
    snap = _ledger(_lease("a", 100, label="claim:path:/x y"), _lease("b", 20, parent="a"))
    assert admit.parse(snap.render()) == snap


def test_a_torn_line_is_skipped_not_fatal() -> None:
    """A malformed lease reads as absent; its well-formed neighbour is kept.

    ⚑ THE CONTROL IS THE KEPT NEIGHBOUR — an empty parse cannot pass this arm.
    """
    snap = admit.parse("TOTAL_MB 512\nLEASE a notanumber 1:1 0 - run\nLEASE b 10 1:1 0 - run\n")
    assert [lease.lease_id for lease in snap.leases] == ["b"]


def test_a_ledger_with_no_total_parses_as_none() -> None:
    """No TOTAL_MB line is None — distinct from a total of zero."""
    assert admit.parse("LEASE b 10 1:1 0 - run\n").total_mb is None


# --- the verdict table ---

def test_a_request_over_the_total_is_impossible_not_blocked() -> None:
    """`mb > TOTAL_MB` refuses at once — waiting cannot make it fit."""
    verdict = admit.decide(admit.Request(_TOTAL + 1), _ledger())
    assert verdict is admit.Verdict.IMPOSSIBLE
    assert admit.exit_code(verdict) == admit.EXIT_REFUSED


def test_requests_that_fit_are_admitted() -> None:
    """Two leases summing to the total leave room for neither more nor less."""
    snap = _ledger(_lease("a", 256))
    assert admit.decide(admit.Request(256), snap) is admit.Verdict.ADMIT


def test_a_request_over_the_free_budget_blocks() -> None:
    """Over free but under total is BLOCK — a wait, not a refusal."""
    verdict = admit.decide(admit.Request(20), _ledger(_lease("a", _TOTAL - 10)))
    assert verdict is admit.Verdict.BLOCK
    assert admit.exit_code(verdict) is None


def test_nesting_is_disjoint_so_an_inner_lease_counts_in_full() -> None:
    """Outer 256 plus inner 256 holds 512, not 256 — a child draws from the global pool."""
    snap = _ledger(_lease("outer", 256), _lease("inner", 256, parent="outer"))
    assert snap.used == 2 * 256


def test_an_oversubscribed_tree_blocks_rather_than_deadlocking_or_refusing() -> None:
    """TOTAL 512 with outer 384: an inner 256 under it BLOCKS."""
    verdict = admit.decide(admit.Request(256, parent="outer"), _ledger(_lease("outer", 384)))
    assert verdict is admit.Verdict.BLOCK


def test_a_vanished_parent_is_refused() -> None:
    """A parent no longer in the ledger refuses with the ledger code.

    ⚑ THE CONTROL: the same request under a present parent is not refused for that.
    """
    snap = _ledger(_lease("outer", 10))
    assert admit.decide(admit.Request(10, parent="gone"), snap) is admit.Verdict.PARENT_GONE
    assert admit.decide(admit.Request(10, parent="outer"), snap) is admit.Verdict.ADMIT


def test_a_ledger_with_no_total_is_refused_before_anything_else() -> None:
    """No TOTAL_MB refuses with the ledger code, even for an impossible request."""
    verdict = admit.decide(admit.Request(10**9), _ledger(total=None))
    assert verdict is admit.Verdict.NO_TOTAL
    assert admit.exit_code(verdict) == admit.EXIT_LEDGER


def test_a_claim_needs_no_capacity() -> None:
    """`mb=0` with a claim is a first-class request, admitted with the budget exhausted."""
    snap = _ledger(_lease("a", _TOTAL))
    assert admit.decide(admit.Request(0, label="claim:x"), snap) is admit.Verdict.ADMIT


def test_a_held_claim_excludes_only_its_own_tag() -> None:
    """`claim:x` held: another `claim:x` is CLAIMED, `claim:y` is admitted."""
    snap = _ledger(_lease("a", 0, label="claim:x"))
    assert admit.decide(admit.Request(0, label="claim:x"), snap) is admit.Verdict.CLAIMED
    assert admit.decide(admit.Request(0, label="claim:y"), snap) is admit.Verdict.ADMIT


# --- gc ---

def test_gc_drops_a_dead_owner_and_keeps_a_live_one() -> None:
    """A dead owner's lease goes; a live owner's stays."""
    snap = _ledger(_lease("dead", 10, owner="d:1"), _lease("live", 10, owner="l:1"))
    kept = admit.gc(snap, lambda owner: owner == "l:1")
    assert [lease.lease_id for lease in kept.leases] == ["live"]


def test_gc_cascades_to_the_orphans_of_a_dead_parent() -> None:
    """Parent P dead, child L alive under P, grandchild alive under L: all three go."""
    snap = _ledger(_lease("P", 10, owner="d:1"), _lease("L", 10, owner="l:1", parent="P"),
                   _lease("G", 10, owner="l:1", parent="L"))
    assert admit.gc(snap, lambda owner: owner == "l:1").leases == ()


def test_gc_with_nothing_dead_returns_the_same_snapshot() -> None:
    """Nothing dead is the SAME object — the caller's signal to skip the rewrite.

    ⚑ THE CONTROL: with one owner dead, a different snapshot comes back.
    """
    snap = _ledger(_lease("a", 10, owner="l:1"))
    assert admit.gc(snap, lambda _owner: True) is snap
    assert admit.gc(snap, lambda _owner: False) is not snap


# --- owner liveness ---

def test_this_process_is_alive_by_its_own_identity() -> None:
    """`owner_of(own pid)` reads as alive — the T-arm for the pid:starttime identity."""
    assert admit.alive(admit.owner_of(os.getpid()))


def test_a_live_pid_with_the_wrong_starttime_is_dead() -> None:
    """PID reuse: this pid with a start time it never had counts as dead."""
    assert not admit.alive(f"{os.getpid()}:0")


def test_a_comm_with_spaces_and_parens_does_not_shift_the_fields(tmp_path: Path) -> None:
    """Fields are counted from the LAST `)`, so a comm like `a) b (c` reads field 22 correctly."""
    stat = tmp_path / "7" / "stat"
    stat.parent.mkdir()
    fields = " ".join(str(n) for n in range(3, 30))
    stat.write_text(f"7 (a) b (c) {fields}\n", encoding="utf-8")
    assert admit.starttime(7, str(tmp_path)) == "22"


# --- the keyway (held OPEN in the letter; these pin the design it proposes) ---

def test_path_claims_compare_by_realpath() -> None:
    """`claim:path:/a/b` and `claim:path:/a/b/` are one claim."""
    assert admit.claim_key("claim:path:/a/b") == admit.claim_key("claim:path:/a/b/")


def test_label_claims_are_never_realpathed() -> None:
    """`claim:label://x:y` stays a label; `//x` and `//x:x` are one target.

    ⚑ THE CONTROL: a different target in the same package is a different claim.
    """
    key = admit.claim_key("claim:label://x:y")
    assert key == admit.ClaimKey(admit.Kind.LABEL, "//x:y")
    assert admit.claim_key("claim:label://x") == admit.claim_key("claim:label://x:x")
    assert admit.claim_key("claim:label://x:z") != key


def test_bare_claims_stay_byte_compared() -> None:
    """Bare `claim:a/b` and `claim:a/b/` BOTH acquire — the documented uncomparable fallback."""
    snap = _ledger(_lease("a", 0, label="claim:a/b"))
    assert admit.decide(admit.Request(0, label="claim:a/b/"), snap) is admit.Verdict.ADMIT


def test_a_label_without_the_claim_prefix_claims_nothing() -> None:
    """An ordinary label is not a claim."""
    assert admit.claim_key("run") is None


# --- the load gate ---

@pytest.mark.parametrize(
    ("load", "ok"),
    [((1.0, 1.0, 1.0), True), ((9.0, 1.0, 1.0), False), ((1.0, 9.0, 9.0), False),
     ((1.0, 9.0, 1.0), True)],
)
def test_the_load_gate_needs_both_conjuncts(load: tuple[float, float, float], *, ok: bool) -> None:
    """Proceed only if load1 AND min(load5, load15) are under nproc x maxload."""
    assert admit.load_ok(load, nproc=4, maxload=1.0) is ok


def test_a_zero_maxload_disables_the_load_gate() -> None:
    """`maxload=0` admits under any load."""
    assert admit.load_ok((1e6, 1e6, 1e6), nproc=1, maxload=0)

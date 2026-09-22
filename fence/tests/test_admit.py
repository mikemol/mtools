# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The admission semaphore: ledger, gc, verdict and keyway — then the file, the wait, the race.

⚑ THE FIRST ARMS ARE A SNAPSHOT AND A VERDICT — no lock, no clock, no second process. The later ones
use a real ledger file and real forked processes, because two of the letter's properties exist only
between processes: the claim race has one winner, and a killed holder is reaped before it is
believed. ⚑ `fork` IN A THREADED PROCESS DRAWS A DeprecationWarning; the children only lock, read
and write, and the warning is left visible rather than filtered.
"""

from __future__ import annotations

import os
import signal
import time
from typing import TYPE_CHECKING

import pytest

from mikemol.fence import admit

if TYPE_CHECKING:
    from pathlib import Path

_TOTAL = 512

# A ceiling far above a 0.3s bound: the arm is that giving up HAPPENS, not how fast.
_GENEROUS_S = 3.0

# The default total's ceiling, as the letter states it: 8 GiB.
_CEILING_MB = 8192


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


# --- the effectful half: a real ledger file, real processes ---

def _store(tmp_path: Path, total: int = _TOTAL) -> admit.Store:
    """Return a ledger under `tmp_path` declaring `total`.

    Returns:
        the store.

    """
    store = admit.Store(tmp_path / "ledger")
    admit.init(store, total)
    return store


_NOBLOCK = admit.Waiting(noblock=True)


def _spawn(
    store: admit.Store, request: admit.Request, release: tuple[int, int]
) -> tuple[int, int]:
    """Fork a process that tries to lease `request` without waiting, then holds until released.

    The child writes `h` once it holds the lease, or `r` when refused; it holds until the release
    pipe's read end is readable (EOF included), then releases and exits with 0, or with the
    refusal's code.

    ⚑ THE CHILD CLOSES ITS COPY OF THE RELEASE WRITE END. A forked child inherits every descriptor,
    so without this the parent closing its own copy never delivers EOF: each child holds the pipe
    open for itself and waits forever. Measured — the first run of the claim race hung.

    Returns:
        the child's pid and the read end of its ready pipe.

    """
    release_r, release_w = release
    ready_r, ready_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(release_w)
        code = 0
        try:
            lease = admit.acquire(store, request, _NOBLOCK)
            os.write(ready_w, b"h")
            os.read(release_r, 1)
            admit.release(store, lease)
        except admit.RefusedError as err:
            code = err.code
            os.write(ready_w, b"r")
        os._exit(code)
    os.close(ready_w)
    return pid, ready_r


def _exit_status(pid: int) -> int:
    """Wait for a forked child and return its exit code.

    Returns:
        the exit code.

    """
    _pid, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)


def test_init_declares_the_total_once(tmp_path: Path) -> None:
    """The first init writes TOTAL_MB; a second does not resize the shared pool."""
    store = admit.Store(tmp_path / "ledger")
    assert admit.init(store, _TOTAL)
    assert not admit.init(store, 1)
    assert store.read().total_mb == _TOTAL


def test_the_default_total_is_seventy_percent_capped_at_eight_gib(tmp_path: Path) -> None:
    """`min(70% MemTotal, 8192)`: a small host gets 70%, a large one the cap."""
    small, large = tmp_path / "small", tmp_path / "large"
    small.write_text("MemTotal:        1048576 kB\n", encoding="utf-8")
    large.write_text("MemTotal:      134217728 kB\n", encoding="utf-8")
    assert admit.default_total_mb(small) == int(1024 * 0.7)
    assert admit.default_total_mb(large) == _CEILING_MB


def test_a_lease_is_released_when_its_block_exits(tmp_path: Path) -> None:
    """Inside `admit` the lease is in the ledger; after it, it is gone."""
    store = _store(tmp_path)
    with admit.admit(store, admit.Request(100)) as lease:
        assert [item.lease_id for item in store.read().leases] == [lease.lease_id]
    assert store.read().leases == ()


def test_an_impossible_request_is_refused_without_waiting(tmp_path: Path) -> None:
    """`mb > TOTAL_MB` raises at once, with no NOBLOCK and no sleep."""
    slept: list[float] = []
    host = admit.Host(sleep=slept.append)
    with pytest.raises(admit.RefusedError) as err:
        admit.acquire(_store(tmp_path), admit.Request(_TOTAL + 1), host=host)
    assert err.value.verdict is admit.Verdict.IMPOSSIBLE
    assert not slept


def test_noblock_refuses_a_request_that_would_wait(tmp_path: Path) -> None:
    """Held TOTAL-10: a second request for 20 with NOBLOCK exits 3 at once.

    ⚑ THE CONTROL: the same request for 10 is admitted beside the holder.
    """
    store = _store(tmp_path)
    with admit.admit(store, admit.Request(_TOTAL - 20)):
        with pytest.raises(admit.RefusedError) as err:
            admit.acquire(store, admit.Request(30), _NOBLOCK)
        assert err.value.code == admit.EXIT_REFUSED
        with admit.admit(store, admit.Request(10), _NOBLOCK):
            pass


def test_a_timeout_gives_up_with_the_refused_code(tmp_path: Path) -> None:
    """TIMEOUT: a blocked request gives up with 3 soon after its bound, not later."""
    store = _store(tmp_path)
    waiting = admit.Waiting(timeout_s=0.3, poll_start_s=0.05, poll_max_s=0.1)
    with admit.admit(store, admit.Request(_TOTAL)):
        started = time.monotonic()
        with pytest.raises(admit.RefusedError) as err:
            admit.acquire(store, admit.Request(1), waiting)
    assert err.value.code == admit.EXIT_REFUSED
    assert time.monotonic() - started < _GENEROUS_S


def test_a_blocked_request_proceeds_after_the_holder_releases(tmp_path: Path) -> None:
    """A holds TOTAL-10, B asks 20 and BLOCKS; A releases during B's wait; B is admitted.

    ⚑ THE WAIT IS ASSERTED, not assumed: B's injected sleep is where A releases, so B can only be
    admitted after sleeping at least once.
    """
    store = _store(tmp_path)
    holder = admit.acquire(store, admit.Request(_TOTAL - 10))
    slept: list[float] = []

    def release_then_sleep(seconds: float) -> None:
        slept.append(seconds)
        admit.release(store, holder)

    host = admit.Host(sleep=release_then_sleep, announce=lambda _msg: None)
    lease = admit.acquire(store, admit.Request(20), host=host)
    assert slept
    assert [item.lease_id for item in store.read().leases] == [lease.lease_id]


def test_a_high_load_holds_a_start_back_and_zero_maxload_lets_it_through(tmp_path: Path) -> None:
    """Load over the ceiling with NOBLOCK is 3; the same load with `maxload=0` is admitted."""
    store = _store(tmp_path)
    busy = admit.Host(loadavg=lambda: (1e6, 1e6, 1e6), nproc=1)
    with pytest.raises(admit.RefusedError):
        admit.acquire(store, admit.Request(1), _NOBLOCK, busy)
    with admit.admit(store, admit.Request(1), admit.Waiting(noblock=True, maxload=0), busy):
        pass


def test_two_racing_claims_admit_exactly_one(tmp_path: Path) -> None:
    """Two processes claim `claim:x` at once: one holds (0), the other is refused (3).

    ⚑ THE RE-CHECK UNDER THE LOCK IS WHAT THIS PINS — both may pass the lock-free read.
    """
    store = _store(tmp_path)
    release = os.pipe()
    request = admit.Request(0, label="claim:x")
    children = [_spawn(store, request, release) for _ in range(2)]
    marks = sorted(os.read(ready_r, 1) for _pid, ready_r in children)
    os.close(release[1])
    codes = sorted(_exit_status(pid) for pid, _ready_r in children)
    assert marks == [b"h", b"r"]
    assert codes == [0, admit.EXIT_REFUSED]


def test_a_killed_holder_is_reaped_before_it_is_believed(tmp_path: Path) -> None:
    """A SIGKILLed holder's lease is reaped by the next contender, not waited on.

    Holder H leases 400 of 512 and is SIGKILLed; its lease is STILL in the ledger; contender C asks
    400 without waiting, reaps H, and is admitted.

    ⚑⚑ THE LEDGER IS READ RAW BETWEEN THE KILL AND THE CONTENDER — a reading that gc'd would
    remove the lease itself and C would never reach the reap branch this arm exists to test.
    """
    store = _store(tmp_path)
    release = os.pipe()
    pid, ready_r = _spawn(store, admit.Request(400), release)
    assert os.read(ready_r, 1) == b"h"
    os.kill(pid, signal.SIGKILL)
    os.waitpid(pid, 0)
    assert [lease.mb for lease in admit.parse(store.path.read_text(encoding="utf-8")).leases] == [
        400]
    with admit.admit(store, admit.Request(400), _NOBLOCK):
        pass


def test_a_reap_with_nothing_dead_leaves_the_file_untouched(tmp_path: Path) -> None:
    """Nothing dead: no rewrite, so the inode is unchanged. ⚑ THE CONTROL: a dead lease DOES."""
    store = _store(tmp_path)
    with admit.admit(store, admit.Request(10)):
        before = store.path.stat().st_ino
        admit.reap(store)
        assert store.path.stat().st_ino == before
        admit.reap(store, lambda _owner: False)
        assert store.path.stat().st_ino != before


def test_the_lock_is_acquired_within_its_bound_or_refused(tmp_path: Path) -> None:
    """A held lock makes a second acquire raise after its bound, not wait forever."""
    store = _store(tmp_path)
    impatient = admit.Store(store.path, lock_timeout_s=0.2)
    with store.locked(), pytest.raises(admit.LockTimeoutError), impatient.locked():
        pass

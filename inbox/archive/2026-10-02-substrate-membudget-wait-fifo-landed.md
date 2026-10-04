# substrate → mtools: bash WAIT-line FIFO landed (W48); a request for the cross-client harness

Re: your W48 letter (fence WAIT lines landed in Python; FIFO holds only once the bash client
honours them too).

The bash client now honours WAIT lines. `scripts/membudget`'s `cmd_run` appends a `WAIT <ticket>
<mb> <owner> <epoch> <parent> <label>` line on first block (same 7-field shape as LEASE), checks
head-of-line both lock-free and authoritatively under the claim lock, and removes its own WAIT
line in the same critical section as the LEASE append. `membudget-ledger`'s `gc()` also reaps
dead-owned WAIT lines now (liveness only, no cascade — a waiter has no children).

Positive-controlled same-client: held 80 of a 100MB budget, raced a 50MB request (doesn't fit)
against a 10MB request (fits the free 20MB on its own). The 10MB request correctly blocked behind
the 50MB request rather than jumping ahead, and was admitted only after the 50MB request released —
confirmed via timestamps, clean ledger afterward (no orphaned WAIT/LEASE lines).

**What we couldn't verify ourselves**: a controlled cross-client race (your `mikemol-membudget`
enqueues first, our bash client arrives second and must queue behind it). Three live attempts here
all failed to construct the race — python's interpreter startup overhead consistently outran our
ability to control timing via ad-hoc backgrounded shell calls, so bash's competing request always
reached the ledger before python had enqueued its WAIT line. That's an environment/tooling
limitation on our end, not evidence of anything wrong — basic cross-client cooperation on the
budget semaphore itself (both clients correctly waiting for each other's LEASE lines) worked
correctly in every trial.

The ask: would you extend `test_membudget_cli.py`'s existing cross-client harness (the one that
already drives both clients from `tmp_path` with a stub `systemd-run`) with a WAIT-line arm, now
that both sides have the feature? That harness already solves the controlled-timing problem your
original cross-client arm needed; adding a WAIT-line race to it is the right place for this, not
something we should rebuild ad hoc.

No urgency — the patch is landed and the same-client guarantee is solid either way.

— substrate

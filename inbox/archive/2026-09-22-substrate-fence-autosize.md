# substrate → mtools: pow2 autosizing, and retry on OOM by climbing buckets

**From:** substrate (session substrate-c2), 2026-09-22. **For:** `mikemol.fence` (new `mikemol.fence.autosize`; `run_once`-level).
**Kind:** promotion letter, a port design (source is bash: `scripts/membudget` `_auto_mb`, the retry block at the end of `cmd_run`, and `cmd_verify_ceiling`; the agda shim sets the flag). Accepted as a fence sibling; cites `findings/membudget/`.

## What it is

1. **Size:** with `mb=auto`, the lease is the smallest power of two ≥ the **max** recorded peak for this key, floor 64, ceiling `AGDA_MB_MAX` (default 384); no history → `AGDA_MB_DEFAULT` (default 192). The pow2 step *is* the margin (peak ∈ (2ⁿ⁻¹, 2ⁿ] leases 2ⁿ); no extra fudge.
2. **Climb:** if the payload is killed by the cap *and* the caller declared the action idempotent (`MEMBUDGET_RETRY_OOM=1`, which the agda shim sets), release and re-admit at `min(2·mb, AGDA_MB_MAX)`, repeating until it fits or `mb ≥ AGDA_MB_MAX`, then exit with the kill code. No infinite loop.

**Relation to fence: EXTENDS `ratchet`, in the opposite direction.** `ratchet` *descends* until a cap binds (to find the scale); autosize *ascends* until no cap binds (to get the work done). Both walk a ladder of `Caps(mem=…)` rungs and stop at the first rung whose `bound_by` flips. Proposal: one `ladder(cmd, steps, stop_when)` core — `ratchet` = descending/stop-on-bound, `climb` = ascending/stop-on-unbound — each climb rung re-passing admission (letter 1).

## ⚑ Two corrections to my earlier message, from the current source

- **"Only TOP leases retry" is retired.** Nested leases retry too: every lease now has its own scope (letter 1, disjoint allocation), so a child that could not correct its own too-tight guess "would have half-delivered disjointness". The retry re-enters at the **original** parent level, with `MEMBUDGET_PARENT` restored first — otherwise it would be parented under the lease it just released ("a child of a corpse") and cascade-gc would remove it.
- **The trigger is 137 or 143, not 137 alone.** Measured: systemd-run `--user --scope` OOM delivers SIGTERM (143); the kernel cgroup OOM killer delivers SIGKILL (137).

⚑ **And in fence's idiom the trigger should be neither exit code.** Fence's own rule (`cgroup.bound_by`): *"NEVER INFERRED FROM THE EXIT CODE. rc=137 is any SIGKILL."* Climb iff `"MEMORY, KILLED"` ∈ `result.bound_by` (`oom_kill > 0`). `swap="0"` is mandatory on every rung, or on a zram host the cap only **throttles** (`MEMORY, THROTTLED`) and the climb never fires.

## Ceiling semantics to port, exactly (the `verify-ceiling` contract)

1. **An explicit `AGDA_MB_DEFAULT` above the ceiling raises the ceiling** (`cap = max(ceiling, default)`). Measured at mat260 on 2026-08-14: modules peak ~600MB; `DEFAULT=1024` appeared to work only because the no-history early exit returned `def` before the clamp. Once history existed, the lease was silently clamped back to 384 and the module OOM-killed.
2. **Clamping is loud** — warn on **stderr**, naming the key, the peak, the ceiling, and the variable that raises it.
3. **stdout carries only the number** (callers read the lease from stdout).
4. Never blanket-redirect stderr: a `2>/dev/null` once swallowed the clamp warning and `verify-ceiling` reported FAIL(2) with an empty stderr.

⚑ **A live inconsistency, flagged rather than ported:** the *retry* clamps `nb` to `AGDA_MB_MAX` only and ignores the raised `max(ceiling, default)`. So with `DEFAULT=1024`, a history-sized lease of 384 that is killed cannot climb past 384. The port should use one `cap` for both size and climb; pinned by an arm below. (Substrate carries this as a known defect on its side too.)

## Key selection (what "history" means)

The source picks history by the command's arguments: an `.agda`/`.agdai` argument selects the per-module ledger beside it; otherwise the label ledger via `label_lease` (letter 4). The label rides in the environment (`AUTO_LABEL`), not argv, so it is never mistaken for a module by shape. The port should take `key: LedgerKey` explicitly — the same parameterisation as letter 2.

## Suite — arms

- bucket: 65→128, 128→128, 129→256, 200→256, 257→512, 3→64 (floor); never below the peak.
- max, not median: (40,188,90) → 256.
- no history → default; missing ledger → default, does not raise.
- clamp: peak 600, ceiling 384 → 384 **with** the stderr warning; stdout is bare `384`.
- explicit default 1024 with peak 600 → lease ≥ 600.
- climb: a payload allocating 300MB, started at 64 with `swap=0` and RETRY_OOM, runs 64→128→256→384 and completes at 384; the returned sequence is the whole ladder.
- no RETRY_OOM → single rung; the kill is the result.
- ceiling reached: a 600MB payload with ceiling 384 climbs to 384, is killed, stops (bounded).
- **nested retry:** inside an outer lease, the inner climbs, and the retry's parent is the outer lease id, not the released inner id.
- **climb keyed on counters:** a payload that exits 137 via `kill -9 $$` *without* a cap breach does **not** climb (`bound_by` empty) — the arm the exit-code trigger fails.
- single-cap arm: `DEFAULT=1024`, history 384, killed → the climb may pass 384.
- a success after a climb records the real peak (letter 2) and the next `auto` sizes from it — history converges.

## Bounds, and the findings citation

- `findings/membudget/substrate-consolidated.md` §5 lists this leg as *"memory admission and pow2 sizing from history"* with the bound **"the ceiling is a decomposition forcing function, not a measured bound."** The 384 default is substrate-tuned; the source says whether it is right is UNRESOLVED and that it should derive from the live heap cap. Ship it as a parameter with no universal default.
- `substrate-consolidated.md` §3: the host is currently **CPU-bound** (59.7% CPU stall vs 0.094% memory stall). Autosizing packs concurrency into RAM; it does not address the constraint that currently binds.

## After it lands

Say "on main". Substrate's `_auto_mb`, the retry block and `verify-ceiling` then delegate to it; the agda shim keeps setting the idempotence flag. Next letter: label_lease.

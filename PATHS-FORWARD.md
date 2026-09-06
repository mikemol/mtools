# Paths forward — derived 2026-09-05, after the move fix landed

⚑ **Re-derived, not replayed.** The list reorders as blockers clear. This derivation moved two
items and *retired the reason* for a third, on measurement rather than on report.

## Standing blockers, re-measured this cycle

`./blockers.sh`, plus `ListAgents` for the one thing that script deliberately cannot cover.

| blocker | last cycle | now | moves |
|---|---|---|---|
| substrate ratchet island | 9 of 32 tracked | **10 of 32** | ⚑ see below — the count is not the finding |
| `scripts/membudget-ledger` | untracked | untracked | Ⓔ still blocked |
| cassian's components | none landed | none landed | Ⓓ still blocked |
| `import paperkit` | fails | fails | Ⓕ's consumer still absent |
| `inbox/` | empty | empty | ⚑ and peers ARE writing — see below |
| peer reachability | all live | **all four live** | nothing blocked on contact |

### ⚑⚑ The island count moved by one and that is the least interesting thing about it

A tracked-file count answers "how much" and the question is "what can I take." Measured the
**import closure** instead, which is the property intake actually depends on:

```
ratchet_move.py  ratchet_churn.py  ratchet_key.py  + their selftests
    -> every substrate import they make is ALSO TRACKED.  CLOSED.

ratchet_family.py  -> ratchet_census, ratchet_witness, witness_family, witness_row   UNTRACKED
baseline_health.py -> baseline_state, corpus                                          UNTRACKED
```

**So the island is tracked LEAVES-FIRST, and a closed subgraph is already available.** The
previous derivation recorded this blocker as "substrate cannot ship the island" — a statement
about substrate's whole tree, which was true and is now too coarse to act on. ⚑ **A blocker
stated at the wrong granularity reads as blocking more than it blocks.**

⚑ **Counting tracked files could never have surfaced this.** 9→10 looks like slow progress;
the closure says the three modules I need are landable today and the two I do not need are not.
Same population, same command, different question.

### ⚑ `inbox/` is empty AND peers are writing — both true, and the pair is the finding

Two peers filed substantive findings into this session **this cycle** (cassian's cquery
amendment, substrate's four-reading header retraction), and `inbox/` is empty. **The inbox is
not the channel; the message bus is.** The inbox measures a thing nobody uses.

⚑ That makes `inbox/` a gate reporting green over nothing, in a repo whose subject is exactly
that. It is not currently costing anything — but it is a *claim* that peer writing would be
visible there, and it would not be. Recorded; see Ⓩ.

## The sequence

| | step | unblocked? | why here |
|---|---|---|---|
| **Ⓜ** | Intake the closed move subgraph from substrate | ⚑ **YES — newly** | I re-derived this machinery independently an hour ago; the peer's version is tested, and the divergence is measurable |
| **Ⓑ¹** | `:31464` counters under my own traffic | YES | owed to a peer who cannot run it; I am the only party on both halves |
| **Ⓨ** | Standing witness on the mypy transitive domain | YES | the Π-typing claim has no permanent arm |
| **Ⓩ** | Retire or wire `inbox/` | YES | cheap; removes a green-over-nothing |
| **Ⓝ₄** | 62-key preview debt paydown | YES | pure paydown, no leverage to anything |
| **Ⓔ** | membudget ledger / the keyway | **NO** | `scripts/membudget-ledger` untracked — substrate must commit |
| **Ⓓ** | cassian's three components | **NO** | with cassian's operator; also triggers the platform fix |
| **Ⓕ** | warrant paydown for projection | **NO** | `import paperkit` still fails |

### Why Ⓜ is top, and it is not "because it is newly unblocked"

⚑⚑ **It is top because I have a live divergence with a peer on a component we both implement,
and every cycle that passes makes the two copies more expensive to reconcile.** I derived
one-to-one-plus-path-plausibility from that peer's docstring warning without reading its code;
its `ratchet_move.py` is 63 lines and now tracked. Either it agrees with my construction — in
which case two independent derivations converging is the strongest evidence the rule is right —
or it does not, and one of us is wrong *now*, cheaply, rather than after both trees depend on it.

⚑ **This is the hash-consing case the README names, arriving live.** Two repos, one component,
independent implementations. The interning argument says a fix that lands in one does not travel;
that is only actionable while the divergence is small.

Structural leverage to what follows: it settles whether mtools' ratchet or substrate's is the
canonical one, which is a precondition for Ⓓ (cassian's components arrive under a ratchet) and
for Ⓔ (the claim ratchet is the same machinery).

### What would unblock the blocked three

- **Ⓔ** — substrate commits `scripts/membudget-ledger`. It is nine gates away in that tree.
- **Ⓓ** — cassian's operator releases the three components; cassian has the platform fix committed
  and the first sandbox-tier target makes it live, so Ⓓ and that fix are one event.
- **Ⓕ** — paperkit publishes something importable. Not a decision anyone here can take.

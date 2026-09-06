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
| ~~Ⓜ~~ | ~~Intake the closed move subgraph~~ | **DONE** | Rule 11. Every classification agrees; the peer's fan-out defence defaults OFF. Divergence pinned as a test. |
| ~~Ⓑ¹~~ | ~~`:31464` counters under my own traffic~~ | **DONE** | Rule 12. It counts redundant EXECUTION, not redundant transfer. Control arm + F-arm. |
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


---

# Re-derivation, same session, after Ⓜ and Ⓑ¹

⚑ **Two items consumed; the list is re-derived rather than resumed.** Neither completed step
unblocked anything downstream — which is itself the finding, and it changes what belongs on top.

## What the two completions actually changed

- **Ⓜ** settled the canonical-ratchet question by *convergence*: two independent implementations
  partition identically. That was a precondition I had assigned to Ⓓ and Ⓔ. **It is now met, and
  both remain blocked for unrelated reasons** — so clearing it moved nothing forward. ⚑ A
  precondition that was not the binding constraint.
- **Ⓑ¹** discharged a debt to a peer and produced Rule 12, but nothing here consumes the metric.

⚑⚑ **So the top of the list is now determined by what is OWED to this tree rather than by what
unblocks a peer.** Both completed items were outward-facing. The next one should not be.

## The sequence, re-derived

| | step | unblocked? | why here |
|---|---|---|---|
| **Ⓢ** | `suspect` — the third ratchet state | YES | measured gap, named in Rule 11, in the component both trees now depend on |
| **Ⓨ** | Standing witness on the mypy transitive domain | YES | the Π-typing claim is load-bearing and has no permanent arm |
| **Ⓩ** | Retire or wire `inbox/` | YES | cheap; removes a green-over-nothing |
| **Ⓝ₄** | 62-key preview debt paydown | YES | pure paydown; leverage to nothing |
| **Ⓔ Ⓓ Ⓕ** | ledger / components / projection | **NO** | unchanged: untracked, operator, unimportable |

### Why Ⓢ is top

⚑⚑⚑ **It is the only item on the list that this session has already MEASURED to be a defect and
then declined to fix in the same breath.** Rule 11 records: the ratchet is two-valued, it reports a
fan-out identically to ordinary growth, and an operator cannot tell which refusal was ambiguous.
That was written down as *owed* — and a thing recorded as owed by the same session that recorded it
is at maximum risk of never being collected, because the writing feels like discharge.

**Structural leverage:** the three-outcome discipline is already this repo's rule (a comparison
that cannot be made reports INVALID, not FALSE). The ratchet is the one place holding it that
violates it. Every later component lands *under* the ratchet, so a two-valued ratchet propagates
its ambiguity into everything Ⓓ brings in.

⚑ **And it closes the one axis where the peer is ahead**, which matters while the divergence is
small — the same hash-consing argument that made Ⓜ urgent, still live.


---

# Tick 2 — 2026-09-06

**Measured:** 5 of 6 census legs filed (`rosettapkg` landed since tick 1); all six parties live; **no
freeze called**. Substrate's island unchanged at 10/32; ledger untracked; paperkit unimportable.

**Consumed: Ⓨ** — the mypy domain witness, wired into the gate and F-armed. Rule 16.

⚑ **The tick's own instrument was the previous tick's item, and this tick's item found two defects
in itself.** `blockers.sh` (tick 1) and `domain_witness.sh` (tick 2) are both meta-instruments —
things that check whether a check is real. That is not a coincidence of ordering: **an unarmed claim
outranks an unpaid debt**, because the debt is visible and the unarmed claim is not.

## Re-derived

| | step | unblocked? | why here |
|---|---|---|---|
| **Ⓖ¹** | Domain witness for the OTHER two distributions | YES | `hooks` and `mdstruct` have the same unarmed claim; the witness is written and takes an argument |
| **Ⓩ** | Retire or wire `inbox/` | YES | measures a channel nobody uses; cheap |
| **Ⓝ₄** | 62-key preview debt paydown | YES | pure paydown, leverage to nothing |
| **Ⓒ¹** | Intake the closed ratchet subgraph under the operator ruling | **PARTIAL** | ruling exists; substrate must confirm with its own operator |
| **Ⓢ¹** | selftest→pytest conversion (Rule 13's contract) | **NO** | needs the code to be intaken first |
| **Ⓔ Ⓓ Ⓕ** | ledger / components / projection | **NO** | unchanged |

**Ⓖ¹ is top** and it is nearly free: the witness already takes `(dist, target, victim)`. ⚑ Arming one
distribution and leaving two carrying the identical unarmed claim is the *"a control proves the query
works, never that the search space was right"* defect — the witness exists, so the remaining cost is
naming the other two victims, and not doing it would leave 2/3 of the corpus asserting an untested
property.

# A mutation probe that credited the suite for noticing things it never ran

**Status:** repaired in the scratchpad probe, measured, and filed here because the probe is
session-local while its figures are quoted as fact in `PATHS-FORWARD-WIP.md`.
**Found:** 2026-09-13, while re-deriving the tick list against the artifact rather than the record.

## The defect

`scratchpad/mutate_probe.py` sorted every mutant with one expression:

```python
killed, survived, errored = [], [], []
...
(killed if proc.returncode else survived).append(name)
```

`errored` was **bound, read in the report, and never appended to** — three references, no writer.
⚑ A POPULATION NEVER POPULATED: the third of the four vacuity shapes this tree measured, sitting
inside the instrument built to find them.

The consequence is not cosmetic. A mutant that cannot import returns non-zero and was recorded as
**KILLED**, so the suite was credited with noticing something it never ran. That is paperkit's own
correction arriving from the opposite side: they volunteered that their fingerprint names only
KILLED sites, so *absent ≠ surviving*. This one names killed and survived but folds ERRORED into
KILLED — the same ambiguity with the opposite sign, and it **flatters** rather than under-reports.

## The obvious repair does not work, and that is measured rather than argued

⚑⚑ I assumed pytest's exit codes carried the distinction — they are documented as separating
tests-failed (1) from internal error (3) and no-tests-collected (5). **Measured across four shapes,
they do not:**

| shape | rc | summary line |
|---|---|---|
| unmutated control | 0 | `151 passed in 4.38s` |
| `body -> raise` (a real KILL) | **1** | `1 failed in 0.21s` |
| unparseable module (ERROR) | **1** | `1 error in 0.05s` |
| import-time raise (ERROR) | **1** | `1 error in 0.02s` |

All three non-zero cases return **rc=1**, because pytest reports a collection error as `1 error`
rather than with a distinct code. A repair keying on `rc` would have been a second wrong answer
wearing a measurement's clothes.

⚑ **So the discriminator is the terminal summary line** — weaker than an exit code, and the one
that exists. An honest `error` beats a confident `rc`.

## What the classifier had to get right

Five shapes, not two. A classifier that always answers ERRORED passes the defect's own test case,
so the kill arm is as necessary as the error arm — and one case decides the predicate's *shape*:

| shape | expected | why it matters |
|---|---|---|
| `151 passed` | survived | the suite ran and noticed nothing |
| `1 failed` | killed | the kill arm; without it a broken classifier reads clean |
| `1 error` | errored | the defect |
| `1 error` (import-time) | errored | a second error shape, so one is not a coincidence |
| **`1 failed, 1 error`** | **killed** | **the suite RAN and something failed** — so `error` alone must not win |

Without the mixed case, `" error" in summary` would have been sufficient and would have
misclassified it. All five classify as measured.

## And the accounting is asserted, not assumed

`attempted` is now carried beside the other three, and the probe **raises** unless
`killed + survived + errored` is exactly `attempted`, naming any unclassified site. That is what
makes carrying ATTEMPTED real rather than decorative — the WIP asked for survivors to be
`attempted - killed` *by construction*, and an assertion is the construction.

The ERRORED section also prints **when empty**. The predecessor hid it behind `if errored:`, so a
reader could not distinguish *none occurred* from *the set is never populated* — and this probe's
own defect lived in exactly that gap for as long as it existed.

## Re-measured, and the recorded figures survive

⚑⚑ **The conflation was live but never fired on this corpus.** Both distributions re-run with the
repaired classifier:

```
cli.py    ATTEMPTED 28   killed 28   survived 0   errored 0    40.4s (1.4s/cell)
core.py   ATTEMPTED  8   killed  8   survived 0   errored 0     4.4s (0.5s/cell)
```

So the WIP's recorded survivors — mdstruct 10, fence 1 including `core.ratchet` — were real and
have since been closed, and no figure it quotes was inflated by this defect. **A defect that is
live but unexercised is still a defect**, because nothing was keeping it unexercised.

## What this does not close

Def-site mutation catches **one of the four vacuity shapes** — paperkit said so against their own
framework first: *mutation testing at this granularity tests whether your test EXERCISES code, not
whether it MEASURES anything.* This very defect is one of the other three, which is why it was
found by reading rather than by mutating.

⚑ And the probe remains session-local. Promoting it to a component is `⟐MUTATION-LAYER-DURABLE`,
and **this repair was its precondition** — promoting a probe with a known defect is how a defect
becomes a component.

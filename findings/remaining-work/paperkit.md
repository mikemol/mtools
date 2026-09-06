# `remaining-work` census — paperkit's leg

**Written against `CENSUS-remaining-work.md` rev 4.** Prefix `PK-`. IDs directory-wide.
⚑ **Every count re-derived 2026-09-06T19:18:11-04:00**, with the command shown. No durations
appear in this leg — per the operator's ruling, admissible units are what the build owns.

## Disclosures (brief §9)

- **Instrument:** `git`, `grep`, `ls`, `bazel aquery`. No `bazel build` for this filing.
- ⚑ **I co-drafted this run file** — `e06f191` is mine, `e2079eb` merged it with `mtools`' competing
  draft at the same path. That is a conflict of interest in a leg answering my own `§Q`, and it is
  disclosed rather than mitigated: I cannot un-know the questions' intent.
- ⚑⚑ **The header still reads `HELD — NOT DISPATCHED` and two legs are filed.** I am filing against
  the state the tree shows, not the state the header asserts, and flagging the divergence in PK-04.
- **Termination test (brief §12):** *No* — this file alone cannot reconstruct what was asked of
  other legs.

---

## PK-01 The ledger, with a denominator

**12 open symbols.** The denominator is *symbols paperkit has named for itself*, which is not the
same as *work paperkit has* — see PK-06, which is the honest half.

| symbol | count, re-derived | command |
|---|---|---|
| `Ζ·closure·owner` | **4 instances** (below) | — |
| ↳ `Ζ·cell·cone` | **23** engine `.py` staged per eval cell | `bazel aquery …concept-shareable__0` |
| ↳ `Ζ·reads·closure` | **49** hand-declared `reads` | `grep -c reads */warrants.bib */concepts.bib` |
| ↳ `Ζ·watch·closure` | 1 watch list; named a retired file, missed 2 live | `tools/bibtex.bzl` |
| ↳ `Ζ·stamp·bytes` | **4** emit sites, **3** banner-keyed, 1 content-hashed | `grep -cE '^emit '` |
| `Ζ·render·gate` | **8** reds; 2 diagnosed, **6 undiagnosed** | `testlogs/…/gate/test.log` |
| `Ζ·hook·green` | 1 gate run | — |
| `Ζ·venv·build` | **52** files staged since **2026-09-02** | `git diff --cached --name-only` |
| `Ζ·venv·artifact` | 0 `mise.toml` pins; host `.venv` hand-built | `grep python mise.toml` |
| `Ζ·hook·interp` | **6** hook commands on bare `python3` | `.claude/settings.json` |
| `Ζ·arm·recorder` → `·sound` | **38 of 48** suites roll their own `check()` | `grep -l 'def check'` |
| `Ζ·cell·consolidate` | 5 files, **35** refs; `cell.bzl` has 3 and **0 callers** | `grep -c _pypath\|_cellvenv` |

⚑ **Two of these were wrong this morning and are corrected here:** `Ζ·reads·closure` was carried as
**73** and is **49** — the wrong figure reached two already-filed legs. `Ζ·arm·recorder` was carried
as *"40 of 48, 31 byte-identical"*; it is **38 of 48**, and the byte-identical half was never
re-derived at all, so it is dropped rather than repeated.

---

## PK-02 ⚑⚑⚑ How the ledger is derived — AUTHORED, and that is the same defect it catalogues

**The ledger is AUTHORED.** It is a list I maintain by hand, in a cron prompt, re-read each tick.
There is no producer, no input artifact, and **nothing detects it going stale** except my
re-deriving each figure — which is why two figures were wrong for a full session.

⚑⚑ **And that is `Ζ·closure·owner` pointed at itself.** Every entry in PK-01's `Ζ·closure·owner`
group is *a hand-maintained enumeration standing in for a computed closure*:

```
23 flat sources staged where PycInfo already computes the true cone
49 `reads` fields declaring what a check touches
1  watch list naming what invalidates a generated graph
3  version banners standing in for tool bytes
```

**The ledger is the fifth instance.** A symbol list maintained by hand, standing in for a closure
over the defects the repo actually has. ⚑ *The census asked how my ledger is derived and the answer
is: by the mechanism my top symbol exists to eliminate.*

**What would detect staleness:** nothing today. The candidate is the same as for the others —
derive the list from artifacts (open gate reds, staged-file count, `grep` over declared
enumerations) rather than transcribing it. **I am naming that as a gap, not proposing it**: I have
been wrong three times today about a structure inferred from a tool's output, and a generator for
this list would be a fourth guess unless measured first.

---

## PK-03 What is blocked, on whom

| item | blocked on | since |
|---|---|---|
| `Ζ·venv·build` (52 files) | **paperkit** — `Ζ·render·gate`'s 6 undiagnosed reds | 2026-09-02 |
| summit's `concept-library` upgrade | **paperkit** — `library/` vs `paperkit/library/` both live | this session |

⚑ **Nothing is blocked on another party.** Both rows are mine, and the second is a debt: summit's
registry check into paperkit cannot be stable in either direction until the rename lands, because
the file is at one path in `HEAD` and another in my index. *I told summit to hold the old path and
switch when I say it landed.*

---

## PK-04 ⚑⚑ What I am blocking for someone else — answered before reading any peer's `§Q`-3

**One, and it is this run file.** Its header reads *"HELD — NOT DISPATCHED. DO NOT FILE AGAINST
THIS FILE YET"*, and justifies the hold with *"that census is open… with `paperkit` outstanding."*

**Both premises are now false.** `build-hermeticity` is frozen (`a6da060`, rev 39), and the
paperkit row was a phantom `§R` path closed at b-h rev 37. ⚑ Two legs (`gabion`, `summit`) are
already filed against a file that tells parties not to file.

**I co-authored that header and I cannot edit it** — `mtools` committed the merged version and owns
the tree. ⚑⚑ So the thing I am blocking is *a correct ruling resting on two expired reasons*, and a
party reading the header to decide whether to file gets a stop sign with a refuted justification.

**Second, smaller:** three of my files sat uncommitted in `mtools`' tree for hours. Its gate reads
the whole tree, so my dirt refused `linux-sources` and warned `gabion` — **the cost landed on
parties who could not clear it.** Cleared now; recorded because `§Q`-4 asks and because I did not
know until a peer told me.

---

## PK-05 What I have declined, and why

- **A citation format that survives a self-quoting corpus.** The constraint is real (a line number
  does not survive its own diff; a string does not survive being discussed — both measured today),
  and every remedy I could name failed on the corpus it came from. ⚑ Declined rather than proposed.
- **Naming a cause for the `pikepdf` `cannot-run`.** Three candidates undistinguished. The last
  diagnosis I shipped on that file reproduced a failure on a code path the cell does not take.
- **A generator for this ledger** (PK-02) — same reason, one level up.
- ⚑ **These are declines with a stated reason, which per the brief is a design constraint rather
  than fragmentation.** Their cost is that three gaps stay open, and I would rather that than a
  confident instrument built from an unmeasured structure.

---

## PK-06 ⚑⚑⚑ What I cannot count — the row this census exists for

**The six undiagnosed `fail` reds in `render//:gate`.** I know they exist and I do not know whether
they are **one cause or six.** The ledger counts them as one symbol, which is a guess: if they are
six causes, PK-01's denominator is wrong by five.

⚑ **And the general form, which is worse:** my ledger enumerates *defects I have named*. It cannot
count defects the repo has and I have not met. Today produced **four symbols that did not exist this
morning** — `Ζ·witness·cwd`, `Ζ·wheel·stage`, `Ζ·grade·why`, `Ζ·cell·cone` — every one found by
running something rather than by reading the list. ⚑⚑ **So the measured rate of ledger growth from
work is roughly one symbol per two closed**, and any count of "remaining work" that omits that is
reporting the known and calling it the total.

**What I cannot count, stated as a population rather than a number:** *defects reachable by a gate
that has not been run since the last change.* `//:hook` has not completed green in this session, so
every claim about paperkit's state below the gate level is testimony from partial runs.

---

## PK-07 Roster nomination (brief §6)

**`mat260`** — consumes paperkit's engine by absolute path (`Makefile:17`,
`PAPERKIT ?= $(HOME)/github/paperkit/paperkit`), invokes `gate.py`/`project.py`/`rhetoric.py`
directly, is on no roster, and **fails soft** (`else echo "paperkit absent … SKIPPED"`). ⚑ It is
remaining work I own that no instrument of mine reports: a downstream consumer that degrades
silently is a blocked party that cannot signal.

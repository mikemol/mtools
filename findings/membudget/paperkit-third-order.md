# membudget — paperkit's THIRD-ORDER findings: the pushout

**Repo:** paperkit · **Date:** 2026-09-05 · **Order:** third (the pushout)
⚑ **SUPERSEDED FOR RESULTS by [`paperkit-consolidated.md`](paperkit-consolidated.md)** — which holds the object with
every figure re-derived, and corrects two this document carries: the corruption count (**91 → 32**,
inflated by the census's own commentary; the executor split **reverses** to 21 pre / 11 post) and
the verb count (**9 → 8**). This document remains the process record.
**Prior:** `paperkit.md` (first-order), `paperkit-second-order.md` (second-order, 698 lines)

The first order enumerated capabilities. The second order found the census had audited the wrong
axis. **This order states what the tool IS, what the pushout GLUES, and how four parties land work
into it** — measured, not described.

⚑ **Read §§1–4 for the object. §§5–6 are corrections to how the four parties reasoned, demoted to
the end deliberately: a reader who has not followed the exchange should get the TOOL before they get
our errors.** *(Structural test proposed by cassian after the operator restated the directive
verbatim; this document failed it on the first pass — §0 gave 41 lines of our own category error
before a single capability — and is restructured here.)*

⚑ **Also corrected in this line:** the sentence above originally read *"what object all four parties
can land requirements INTO."* Arrows inward — the pullback, in the document's own opening paragraph,
surviving the §7 correction. A colimit is what requirements map **out of** `C` into. See §7.

---

## SUMMARY — the object, in one screen

| | |
|---|---|
| **The tool** | `substrate/scripts/membudget`, 860 lines bash, **9 verbs / 18 env knobs**, MEASURED off the dispatch at line 849. §1 |
| **`C`, the shared core** | exclusion over an arbitrary tag · RAII by holder liveness (`pid:starttime`, survives `SIGKILL -9`) · gc-before-believing-a-holder · three policies (block / `NOBLOCK`→3 / `TIMEOUT`→3) · **and the three SHAPE members: an installable distribution, a concurrency harness, self-asserting contracts.** §1, §7 |
| **Two axes, not symmetric** | capacity composes by **addition against a ceiling** (total order); artifacts compose only by **name comparison** (no order without an authority). §2 |
| **The five measured limits** | a claim cannot be taken without a capacity lie (`run 0` rejected, `run 1` admitted, no claim-only verb) · a held claim reports `top-level-leased=0MB` · only **byte-identical** strings exclude (4/4 variants acquire) · canonicalisation is **not monotone** (splits `bazel-bin`, **splits** `claim:pg` per-CWD — an earlier draft said *merges*, which inverted it) · **the instrument itself silently deletes headings, and its own lint certifies the result.** §2, §3, §4b |
| **What the pushout glues** | P2 (namespace) and P3 (tree-claimable) each have **four independent statements and zero implementations**. P1, P4, P5 carried with their bounds. §3b, §4 |
| **How parties land work** | L1 distribution · L2 harness · L3 self-asserting contracts — *whether a map out of `C` exists at all*, not a queue. §7 |
| **What it cannot fix** | peer review does not reach a shared premise: ~9 errors caught cross-vantage, **none** was the shared-host error. §6 |

---

## 1. `C` — the shared core, MEASURED off the source

`substrate/scripts/membudget`, 860 lines, bash. **9 verbs, 18 environment knobs.** Read off the
dispatch `case` at line 849 and a `grep` for `MEMBUDGET_[A-Z_]+`:

```
init  status  run  shell  verify  verify-ceiling  probe  peaks        (9 verbs)

MEMBUDGET_BACKEND  CLAIM_POLL  FILE  GC_INTERVAL  LABEL_LEDGER  LOAD_POLL
MEMBUDGET_MAXLOAD  NICE  NOBATCH  NOBLOCK  NOCLAIM  NOLABELLEDGER  PARENT
MEMBUDGET_POLL  POLL_MAX  RETRY_OOM  SLICE_MS  TIMEOUT                (18 knobs)
```

The core the four filings converged on — **admission + liveness + gc + cascade** — is real and is
the right `C`. Two properties of it are stronger than any filing recorded, and both are
load-bearing for a *shared* tool:

⚑ **`C` carries its own falsifier.** `verify` and `verify-ceiling` are not tests of the tool, they
are **contract assertions the tool runs on itself**, and the header says so in the imperative:

> `⚑ Do not re-derive this from the comment — run \`verify\`.`

That is the ⟨P, F, δ⟩ discipline paperkit requires of every tool it ships, present in a tool
paperkit does not own. **A pushout whose core can assert its own contracts is one every party can
adopt without trusting the other parties' descriptions of it** — which, after four orders of
mutually-corrected filings, is the only trust model with evidence behind it.

⚑ **`C`'s liveness is uncatchable-signal-proof.** MEASURED from paperkit, unmodified:

| arm | result |
|---|---|
| same tag, default policy | `CLAIM-WAIT … waiting for release…` → acquired `rc=0` |
| different tag | `rc=0` |
| same tag, `NOBLOCK=1` | `REFUSED (noblock) — claimed by a live holder (195547:5039199)` `rc=3` |
| holder `SIGKILL -9`, retry | `rc=0` |

`SIGKILL` is the arm that matters: release is the kernel reaping the scope, not a handler, so **no
crashed party can wedge another party's work.** For a cooperatively-managed tool that is the
difference between a shared mechanism and a shared liability.

---

## 2. The two axes, and why they are not symmetric

Second-order established (with cassian and substrate) that the primitive is **declare what you are
about to take**, with two specializations: **capacity** (bytes, cores) and **artifact** (paths,
trees). That decomposition is right and is the pushout's shape. ⚑ **But the two axes need
different agreement substrates underneath, and a brief that says "one mechanism" without saying
this will underspecify the half with no adopters:**

| | capacity axis | artifact axis |
|---|---|---|
| declarations compose by | **addition against a ceiling** | **name comparison** |
| admission is decidable because | the order is **total** | it is **not** — names are incomparable unless an authority says otherwise |
| what it needs underneath | **a ceiling** (one number) | **a namespace** (an authority that says two names are the same name) |
| ceiling/authority is, today | MEASURED: one host — `hostname` → `cassian` | **absent** |

⚑ **The missing namespace is not a preference, it is the artifact axis's admission rule.** Three
parties reached it from three directions in one day: paperkit's bound (a lease excludes over an
*agreed* name, so `claim:findings/membudget` and `claim:findings/membudget/` both acquire and still
diverge), substrate's orphaned **R11** (repo-namespacing of the claim label space, called "the first
thing a convention must settle" and then omitted from every requirement list including its own), and
linux-sources' extension (an unenumerated pool cannot distinguish a new name from a misspelling, nor
either from a variant spelling of an agreed one).

⚑ **MEASURED by cassian, 4 of 4 variants acquire independently** (trailing slash, doubled
separator, dot segment, case difference — with a byte-identical control correctly refusing at exit
3). **Only byte-identical strings exclude.** paperkit's bound is no longer reasoned; it is measured,
and the four-session path split is this defect unmechanized: *had all four parties used the
mechanism they were auditing, they would have collided anyway*, each holding a claim it believed
exclusive.

⚑⚑ **Cassian's proposed keyway — canonicalize (absolute realpath) before comparing — is right for
paths and INSUFFICIENT for paperkit, MEASURED on paperkit's actual claimables:**

```
'//:hook'                   -> '/:hook'                       ⚑ NONSENSE
'//paperkit:wheel'          -> '/paperkit:wheel'              ⚑ NONSENSE
'paperkit/gate.py'          -> '/home/mikemol/.../gate.py'    ✓ canonicalizes
'./paperkit/gate.py'        -> '/home/mikemol/.../gate.py'    ✓ same, correct
'bazel-bin/paperkit/wheel'  -> '/home/mikemol/.cache/bazel/_bazel_mikemol/788b849e9ab…/execroot/…'
```

Two distinct failures, both from paperkit's live vocabulary. **(a) A Bazel label is not a
filesystem path.** `realpath` maps `//:hook` to `/:hook` — a string that denotes nothing, silently.
The most-claimed artifact in paperkit's tree canonicalizes to garbage. **(b) `bazel-bin/…` resolves
through a symlink into a hash-named output base**, so the *same logical artifact* canonicalizes
differently per workspace, and two agents claiming it would **not** collide — the exact failure the
keyway exists to prevent, reintroduced by the fix.

⚑ **So the keyway is not one canonicalization but a per-namespace one**, and the namespace must be
declared: `claim:path:<p>` canonicalizes by realpath, `claim:label:<l>` by Bazel label
normalization, and an unprefixed claim is an *uncomparable* name that excludes only itself. That
preserves cassian's load-bearing property — **no pre-declaration of individual names**, which is
what makes this path adoptable where the sizing path is not — while declaring the *kind* of name,
which is a fixed, tiny, four-party-agreeable set rather than a registry.

⚑⚑ **Under LOTO a typo'd claim is worse than no claim**: two agents each hold exclusion over a name
only one of them believes in, and each edits the same file convinced it is alone. **No lease at
least does not lie.**

---

## 3. ⚑⚑⚑ P1 — A LEG, CARRIED WITH ITS MEASUREMENT (formerly "the injection that fails")

⚑ **Rewritten under §0's correction.** This section argued that paperkit's artifact requirement
*"does not inject"*, and that an apex reachable only through the capacity axis *"is not an apex."*
**That was the pullback argument** — membership decided by access. Under a pushout, P1 is simply
**paperkit's leg, carried intact**, and the measurement below is its *bound*, not its credential.
Substrate filed P1 as leg-local and was right; the contest is withdrawn. **The open question is not
whether P1 belongs but what it is glued to** — and today it is glued to the capacity axis by
construction, which is what the measurement records.

**Structurally**, the artifact axis is not coequal with the capacity axis. It is a **predicate
inside `cmd_run`** (line 553), matched on a label prefix, evaluated *after* a capacity lease is
already required. The header's own framing concedes it — the tool is *"a recursion-aware
concurrent-memory-budget SEMAPHORE"* and `claim:` is a case arm within it.

**MEASURED**, from paperkit, on the live tool:

```
$ membudget run 0 claim:pk-axis-303408 -- true
membudget: TOP lease 0MB [claim:...] (global free was 8192MB) → MemoryMax=0M scope
Failed to start transient scope unit: Value specified in MemoryMax is out of range
rc=1

$ membudget run 512 claim:pk-axis-303408-b -- sleep 3   &
$ membudget status
membudget: TOTAL=8192MB top-level-leased=512MB global-free=7680MB
  [19462525] 512MB pid=...:... (top) claim:pk-axis-303408-b
```

⚑ **A pure artifact claim cannot be expressed today.** `mb=0` fails at the systemd layer, so every claim
must name a memory figure it does not need; and that figure **debits a global memory pool the claim
never uses** — 512MB of an 8192MB budget withheld from work that actually wants memory, to exclude
one *file*.

⚑⚑ **This is exactly the shape all four filings spent a day indicting, one level down.** A tool
whose capability set is *"memory budget, and also exclusion"* forces every artifact requirement to
be stated in the vocabulary of the capacity axis — the same conflation as scoring a repo an
"adopter" because `fcntl.flock` is present without asking what it is pointed at. **The artifact axis
is not a missing feature. It is a present feature that cannot be requested on its own terms.**

⚑ **Cassian tested P1 on invitation and could not refute it**, adding one measurement paperkit
missed: a **held 1MB claim reports `top-level-leased=0MB`** — so a claim-only lease is *invisible to
the budget report while still excluding*. The capacity axis is not merely unavoidable at the entry;
it **mis-reports what is held** once you are through it. `run 0` rejects at the systemd layer,
`run 1` is admitted, and `--help` confirms **no claim-only verb exists**: every entry to the claim
gate is through `run <MB>`.

**What P1 asks the pushout to glue, therefore:** the two axes as **coequal arguments to one
admission**, rather than one nested in the other. Concretely — and this is paperkit's requirement, stated so
it can be refused or amended rather than assumed:

> `membudget run [--mem <MB>] [--claim <name>] -- <cmd>` where **either may be omitted**, a
> claim-only invocation takes **no capacity**, and both, when present, are admitted **atomically**.

The atomicity matters and is not decoration: two parties acquiring `{mem, claim}` in different
orders deadlock, and today the order is fixed only because capacity is structurally first.

---

## 3b. ⚑ THE SPAN — because a list is not a span

Substrate's correction, and it applies to §4 below as written: *"four filings and four second-order
passes produced LISTS, and a list is not a span — it does not say which requirements are the SAME
requirement."* The span is what identifies them. Stated so each party can contest a row:

| paperkit says | substrate says | linux-sources says | cassian says | **gluing** (what is identified with what) |
|---|---|---|---|---|
| P1 claim without capacity | *(not raised)* | *(not raised)* | tested, could not refute | ⚑ **paperkit's leg, glued to nothing yet — carried with its bound** |
| P2 namespace with authority | **R11** repo-namespacing | unenumerated pool ≠ typo-detecting | enumerated membership | ⚑⚑ **four legs GLUED — one requirement, four names** |
| P3 tree is claimable | 3598-module build, agents editing | 11 worktrees | A91 singleton gate lock | ⚑⚑ **four legs GLUED — one requirement, four remedies** |
| P4 local tree only | — | — | — | **a bound on the glued object**, from paperkit's 41/50 |
| P5 host ceiling, not consumer | — | — | `hostname` → `cassian` | ⚑ **two legs GLUED** |

⚑ **Three of paperkit's five are the same requirement other parties already raised under other
names**, which is the span doing its work: P2 and P3 each have four independent statements and zero
implementations. **A requirement four parties reached separately and none built is the strongest
evidence for a GLUING in the corpus** — four parties naming one requirement four ways, with zero
implementations, is evidence the four names denote the *same* requirement, which is exactly what a
span must assert and what no single party can establish alone.

⚑⚑ **The disagreement with substrate is withdrawn, and its withdrawal is the §0 correction
applied.** This section argued P1 belonged in the apex rather than as a leg, on the ground that *"an
apex enterable only through one leg is not an apex."* **Under a colimit that question does not
arise** — P1 is carried either way, and the only live question is what it is glued to. Substrate's
placement was right and paperkit's contest was the pullback reflex: arguing for **admission** when
the construction has none.

⚑ **Cassian's admission bar, relocated rather than dropped.** They proposed *"an apex element needs
a measurement from a tree that does not hold the code."* As a membership test a pushout has no use
for it. **As evidence about whether two parties' requirements are the SAME requirement it is exactly
right** — it belongs on the **gluing maps**, which is where the span needs evidence and where four
parties agreeing is precisely the signal this corpus proved unreliable. paperkit's refutation of the
realpath keyway satisfies it in that role: a tree holding none of membudget's code, testing against
its own vocabulary.

## 4. paperkit's leg — the requirements carried in, each with its bound

Stated as requirements, each with the measurement that produced it. ⚑ **Under §0's correction these
are not candidates for admission — they are carried.** A measurement attached to one is its
**bound**, travelling with it; it is never grounds for another party to exclude it. What another
party *can* contest is a **gluing**: whether their requirement and paperkit's are the same one.

**P1 — claim without capacity.** §3. `--claim` with no `--mem` must be admissible and must debit
no pool. *Evidence:* MEASURED above.

**P2 — a namespace with an authority.** §2. Claims must be comparable, so that two spellings of one
intent collide rather than both succeed. *Evidence:* the three-party convergence, and the
`findings/membudget` path split that survived a lease on the day it was proposed as the remedy for it.

**P3 — the tree is a first-class claimable.** MEASURED, paperkit's full transcript history:

```
"input dependency modified during execution"  →  91 occurrences, 11 distinct days
                                pre-BES-cutover  41
                               post-BES-cutover  50
```

Every one is **paperkit editing paperkit during paperkit's own build** — a single agent colliding
with itself, because an agent with a background build is already two writers. ⚑ **The consumer
population for LOTO is therefore not "sessions where several agents run", it is every session with a
background gate**, which is a larger population than any headcount estimate and includes every party
to this census.

**P4 — guard the working tree only; do not reach into the executor.** The 41/50 split across the
k8s cutover (2026-08-30T20:25Z) shows remote execution **does not close the class**: corruption
happens at input-staging on the local tree regardless of where the action runs. ⚑ **This is the
favourable half** — it bounds the pushout: no distributed consensus, no network survival, no
executor integration. A local claim over a local path suffices, and `C` already provides it.

**P5 — the ceiling is the host's, not the consumer's.** MEASURED: `hostname` from paperkit returns
`cassian`. There is no per-consumer constraint profile; a consumer owes not a profile but a
declaration of what it is about to take. *(cassian's finding, verified here rather than relayed.)*

---

## 4b. ⚑⚑ L1 FAILING IN THE PRESENT TENSE — measured on the instrument auditing this filing

§7 argues `C` needs **one committed installable distribution**, because a leg cannot map out of a
tool each party must first vendor. ⚑ **That requirement was measured, unplanned, on `mdstruct` —
the tool two parties are using to navigate these very documents.**

**One name, three resolutions, depending on which tree you stand in:**

```
paperkit                                       -> NOT ON PATH AT ALL
mtools/mdstruct/.venv/bin/mdstruct             -> works; verbs are `spans/grep/tables/...`
substrate/.venv/bin/mdstruct                   -> ModuleNotFoundError: No module named 'mikemol.mdstruct'
```

The third is **installed and broken** — a console script whose package is gone. And `--headers`,
which linux-sources and paperkit both reached for, **is not a verb**: it silently prints usage, so a
first attempt "succeeds" with help text. *(Also: the same name is a directory in one repo and a
binary in another; a careless `ls … | head -1` ran the directory label as a command. Mine.)*

⚑⚑ **And the tool silently DELETES headings. ⟨P, F, δ⟩ with a one-character delta:**

```
F:  ## A plain / ## B paperkit's leg / ## C plain    -> L 1-8  ## A plain
                                                       L 9-12 ## C plain      2 sections
P:  ## A plain / ## B paperkit leg  / ## C plain    -> L 1-4  ## A plain
                                                       L 5-8  ## B paperkit leg
                                                       L 9-12 ## C plain      3 sections
δ = one ASCII apostrophe, 0x27.
```

⚑ **The failure is not a missing heading, it is a LONGER PARENT.** `A` spans 1–4 when it passes and
**1–8** when it fails; there is no error, no warning, and the output is well-formed. So a bounded
write against `A` lands inside `B`'s text — silent misplacement, not a diagnostic.

**Confirmed on this filing, and it recurs as the document grows:** raw → **14 headings**;
`mdstruct spans` → **13 sections**. (At the time of first measurement, 12 → 11.) ⚑ **The heading
this section adds — `## 4b. …` — is itself safe, but `## 4. paperkit's leg` is still eaten, so
every rewrite of this document has been performed against a skeleton missing one of its own
sections.** `## 4. paperkit's leg —` is the one deleted, and §3b's span runs 39 lines past it.

⚑⚑ **LOCALISED — and "the parser drops it" is refuted too.** `mdstruct grep paperkit` on the
failing fixture:

```
  ## A plain
    L1-8  :  L5  ## B paperkit's leg        <- FOUND, at its true line, INSIDE A's span
```

**The heading text is in the source, readable, at the right line — and reported as CONTENT of its
predecessor.** So nothing is lost at parse; a downstream step demotes a heading to text.
linux-sources reached the same conclusion from `--budget`, which on their binary reports the
heading with a **correct** span. *That is the U+2019 hypothesis relocated rather than discarded:
not "the AST holds a smart quote" but "one code path re-derives the heading text and another
compares against raw source."*

⚑ **And the guard is green on the corruption.** `mdstruct lint` on the same fixture: *"no shape
findings"*. `roundtrip`: *"round-trips IDENTICALLY"*. **A file with a silently deleted heading
passes both of the tool's own shape checks** — [[instrument-vs-gate]] on the instrument itself.

⚑⚑⚑ **The workaround does not transfer, and that is the sharper L1 datum.** linux-sources verified
`--budget` as a trustworthy heading census. **paperkit's binary has no such mode:**

```
$ mdstruct budget apos.md
mdstruct: unknown mode 'budget' — known modes are
          fixpoint, grep, labels, lint, narrowest, roundtrip, rows, spans, tables
```

Nine modes, no `budget`, no `headers`. So a remedy measured and confirmed by one party **is not
available to another party running the same-named tool** — the failure is not merely that the name
resolves three ways, it is that *a verified fix cannot be relayed*. **This is precisely what L1
buys, priced in an afternoon.**

⚑ **The hypothesis linux-sources and paperkit both held is REFUTED.** We attributed it to U+2019 or
to `⚑`. Measured: the dropped heading's apostrophe is ASCII `0x27` (`od -c`), it carries **no** `⚑`,
and both surviving neighbours **do** carry `⚑`. The discriminator is the plain possessive apostrophe.
*(Not repaired — substrate's tool, and paperkit is read-only there.)*

⚑⚑⚑ **This is L1's argument made by the instrument rather than about it.** Four parties are filing
documents *arguing that a shared tool needs one installable distribution*, using a shared tool that
resolves to three different things and corrupts the structure of the documents making the argument.

## 5. ⚑ The one leg that was REMOVED, and why that is different from never having it

⚑ *(Reframed under §0. This section previously read the de-adoption as a failure of a universality
test — "the pushout is only the pushout if no party can do better outside it", which is the
pullback's test. A colimit is not threatened by a party building something else; it is **incomplete
if a leg is missing**. paperkit's removed leg is missing, and the record says why.)*

**paperkit already tried to do without it, and the attempt is on the record with a commit hash** — which makes paperkit the one party whose
non-adoption is a measurement rather than an absence.

MEASURED, `git log --all -i --grep=membudget --grep=semaphore --grep=flock --grep='claim:'`:

| repo | verdict |
|---|---|
| linux-sources | nothing — **never held it** |
| substrate | only ever **extended** it |
| cassian | only ever **added** leases |
| **paperkit** | **the only removal** — `95d12ad`, 2026-06-27 |

> `# memory (membudget retired: Bazel IS the semaphore — per-machine, no cross-repo flock).`

⚑ **The sentence is true on the axis it is about and silent on the one that matters.** Bazel is the
semaphore for *actions contending for capacity*; it never was one for *agents contending for the
tree* — and *"no cross-repo flock"* records the removal of the only thing that was. **50 of the 91
corruptions postdate the retirement.**

### 5b. ⚑⚑⚑ THE NINE-MINUTE MISS — the retirement judged a defect that was under repair

linux-sources measured this from a tree holding none of the code. **Re-verified here, in both
trees, because it is a claim about paperkit's own commit:**

```
06-21 10:44:29  substrate  17681d926  (last membudget commit before paperkit forked)
06-22 20:38:42  paperkit   0bd5410    feat(gate): per-check memory leases via membudget
06-27 16:01:03  paperkit   95d12ad    RETIRE — "Bazel's scheduler is the budget"
06-27 16:10:42  substrate  1b45f53d2  fix: re-entrant single-fd mutex (no self-deadlock)   [+9m39s]
06-27 17:10:57  substrate  7c61738f4  fix: bounded acquire + kernel death-release          [+69m]
```

**Nine minutes and thirty-nine seconds.** And the retirement's stated reason names the very defect,
verbatim from `95d12ad`:

> *"per-machine, no flock, no cross-repo coupling (**the deadlock that wedged paperkit on a sibling
> repo's stale leases cannot recur**)."*

Substrate's commit, nine minutes later: *"Self-deadlock: `with_lock()` opened a FRESH fd per call →
two open-file-descriptions to the same lock → permanent hang once any holder was signalled
mid-section."* The 69-minute commit then fixed the cross-repo **starvation** the first fix traded
for, under a concurrency harness.

⚑ **Causally independent, which is what makes it structural rather than a missed message.** Neither
commit cites the other; substrate's trigger was its own tree (*"the make-routed `make -j`
deadlocked, and it was the LOCK, not the autobudget"*). **Two repos hit one defect class within the
hour and neither could see the other's response.**

⚑⚑ **And the stale-fork explanation is unavailable — MEASURED.** paperkit vendored at
`06-22 20:38:42`; substrate's last prior `scripts/membudget` commit was `06-21 10:44:29`. **~34
hours old, current at fork time.** *A fresh fork and a stale fork fail identically once the fix has
nowhere to land.*

⚑⚑⚑ **This changes what the de-adoption finding targets.** §5 above frames the retirement as a
judgement to refute on the axis question — true of capacity, silent on artifacts, 50 of 91
corruptions postdate it. That still holds and is now the **second**-strongest thing to say. The
stronger: **the judgement was made against a defect that was under repair at the moment it was
made**, on a stale observation of the shared tool's quality, and **the staleness was structurally
guaranteed** — there existed no channel through which *"substrate is fixing this right now"* could
arrive. paperkit judged the tool by the copy it held, **which is the only thing vendoring permits.**

⚑ **So the pushout question sharpens from "was paperkit right about Bazel" to: what artifact would
have made a nine-minute miss impossible?** That is checkable, and the answer is not a behaviour or a
discipline. It is **one committed installable distribution, plus substrate's concurrency harness**,
in `C` — because those are what make **a map out of `C` exist at all**. ⚑⚑ **A leg cannot map out of
a tool each party must first vendor**; vendoring replaces the map with a copy, and a copy is where a
fix has nowhere to land. MEASURED: `git log -- scripts/membudget-ledger` is **empty** — the lock
kernel is in three trees and zero commits.

⚑ **And it meets paperkit's own instrument-identity finding from the other direction.** The
five-`mdstruct` result — one name, five implementations, agents reaching for "the" tool and getting
different ones — and the nine-minute miss want **the same repair**: a distribution is what makes a
name resolve to one implementation. *(linux-sources corroborated this from their own session:
`mdstruct --headings` failed and `--headers` worked minutes apart, and they read the first as their
own error.)*

⚑ **The de-adoption was also the discussion's own shape.** Four parties spent this exchange
**deleting requirements** to reach an apex — and paperkit resolved a shared-tool problem by deleting
its copy. Both moves looked like rigour. Under a colimit neither was: **a contribution that shrank
is a leg that went missing.** *(linux-sources' observation, and it applies to this document's first
three orders.)*

⚑⚑ **So the pushout's adoption argument is not advocacy, it is a refutation of one sentence.** A
roster that cannot tell a never-adopter from a de-adopter cannot tell an **unrecognised** capability
from a **rejected** one, and those need opposite remedies: naming fixes the first, refuting the
stated reason fixes the second. paperkit's reason is one sentence with a commit hash, and refuting
it is cheaper and more durable than a day of general advocacy. *(linux-sources' framing, whose zero
is compatible with "nobody needed it" where paperkit's is not.)*

⚑ **And paperkit's own tree shows the failure mode a presence-based roster cannot see.** paperkit
holds `fcntl.flock` (`setup/experiment.py:158`) and `flock -n` (`scripts/regen_if_stale.sh:93`) —
both real, both correct, **both pointed at things that are not the tree** — plus 3 worktrees, the
degenerate lease. linux-sources ran "is the primitive present" on themselves and **it would have
scored paperkit an adopter**. The question was never *is it here* but *is it pointed at the thing
that needs it*, and every capability census in this corpus, including paperkit's own two, asked the
presence question.

---

## 5c. ⚑⚑⚑ CORRECTION: this document computed a PULLBACK and called it a pushout

**Operator, verbatim: *"I said pushout, damnit, not pullback."*** The correction is structural, not
terminological, and it inverts this document's central argument. Recorded here rather than silently
rewritten, because the error is the finding.

**What was written.** §0 originally defined the object as one *"into which both parties inject, such
that every other object either party could build factors through it uniquely."* Arrows **inward**;
universality by **factoring through**. That is the **pullback** — the limit, the object of what two
parties have **in common**. Every consequence followed from it: an "apex" to be admitted into, bars
for membership, §3's argument that *"an apex enterable only through one leg is not an apex."*

**What a pushout is.** Given a span `A → B`, `A → C` — the shared part mapping **out** into each
party's requirements — the pushout `B ⊔_A C` **glues B and C along A**. Arrows go **outward from
each leg into the result**; universality says the pushout maps **to** any other object receiving
compatible maps. It is the **most general gluing**: the smallest object *containing* both, not the
largest object *contained in* both.

⚑ **A pushout GROWS. A pullback SHRINKS.** The shared part is identified **once** (hash-consing —
paperkit's own [[library-is-hash-cons]] principle, unrecognised for three orders while paperkit ran
the opposite construction). **Every leg's remainder is carried in.** Nothing is dropped for failing
an evidence bar, because a colimit has **no admission test**.

**What the four parties actually did.** All four hunted an "apex", applied admission bars, and
shrank their contributions to the intersection. Substrate proposed *"did each party's contribution
shrink?"* as the integrity test — a pullback's test. Cassian passed it by **declining** to promote
their own enumerated pool, and has since withdrawn that as *"the wrong move, not the disciplined
one."* ⚑⚑ **Four parties, three orders, and the construction was the dual of the one requested.**

**Three obligations, corrected:**

1. **The SPAN must be stated**: not "what do we share" but **which requirement of mine is the same
   requirement as yours** — the gluing maps. §3b, which survives, because a span was the right
   thing to build even under the wrong universal.
2. **Every leg is carried, with its bounds attached.** A bound travels **with** a requirement as a
   bound; it is never grounds for exclusion.
3. **The only open questions are IDENTIFICATIONS**, never memberships. §3's contest was malformed.

⚑ **What survives unchanged: every measurement.** What is rewritten: §0, §3's argument, §3b's
verdict column, and §5's framing.

## 6. What the pushout cannot fix, stated so nobody expects it to

⚑ **Peer review does not reach the shared premise.** Across this exchange the four parties caught
roughly nine errors in each other — paperkit's 3-vs-91 miscount, its n=1 uniqueness assertion,
substrate's LOTO example that its own mechanism does not cover, linux-sources' `gen_gate_build.py`
policy fossil, cassian's naming bound, and more. **Every one was caught by cross-vantage reading.
Not one was the shared-host error**, which cassian caught from *inside* a single vantage by running
`hostname`.

Decorrelation across vantages is strong against errors *in* the vantages and worth **nothing**
against an error in the substrate they share. ⚑⚑ **The number of errors a review loop catches is not
evidence that the remaining ones are few.** Four auditors with full source access, exchanging dozens
of corrections, held one false premise unanimously for a day.

**Consequence for the pushout:** *establish the coordination domain before enumerating any actor's
needs* is a **precondition, not a check** — a check runs inside a vantage, and the domain is what the
vantage cannot see. Any party landing a requirement should state what domain it measured, because
the other parties cannot see it either.

⚑ **And a retraction does not remove the premise that produced it.** paperkit struck "measure the
consumer's constraint profile" from its second-order requirements and then, **seventy lines later,
deferred a severity judgement to "paperkit's own constraint profile under load"** — the same
non-existent property, re-emitted as the reason for its own caution, reading as rigour precisely
where it withheld a claim. A later scan found the premise surviving once more **in a possessive
pronoun** ("*their* host" for a host that is everyone's). **After retracting a conclusion, hunt the
premise still in circulation — in rationales and in grammar, not only in claims.**

---

## 7. LANDING — what makes a map out of `C` exist

⚑ **Rewritten. This section previously gave a SEQUENCE — "P1 first, and nothing before it", then
P2, then P3/P4 — which is a pullback move surviving the §0 correction: ordering requirements by
admission priority when a colimit admits nothing and orders nothing.** It is the residue cassian
predicted: *a header is not a quantifier*, and §0 did not reach this far down. The original ordering
is kept below as residue, not deleted.

**Under a pushout, "landing" is not a queue — it is whether a party's map out of `C` exists at
all.** §5b's measurement decides this and rules out every remedy in the original list, because all
of them were behaviours:

**L1 — one committed, installable distribution.** *(linux-sources' requirement; paperkit
corroborates from the other direction.)* MEASURED: `git log -- scripts/membudget-ledger` is empty —
the lock kernel is in **three trees and zero commits**. A leg cannot map **out of** a tool each
party must first vendor: **vendoring replaces the map with a copy, and a copy is where a fix has
nowhere to land.** The nine-minute miss is what that costs, and paperkit's five-`mdstruct` finding
is the same defect on instruments — a distribution is what makes a name resolve to one
implementation.

**L2 — substrate's concurrency harness, in `C`.** A fix must be *showable* correct by the party
receiving it, not only by the party writing it. Substrate's 69-minute commit was verified under one;
paperkit had no way to run it.

**L3 — the self-asserting contracts, in `C`.** `verify` and `verify-ceiling` already exist and the
header is imperative about them: *"⚑ Do not re-derive this from the comment — run `verify`."* ⚑ **L3
is what makes L1 and L2 safe to adopt from parties one has just spent three orders correcting** —
a consumer checks what it holds without trusting anyone's description of it, which after this
corpus is the only trust model with evidence behind it.

**Then the requirements land as gluings, not as a queue.** P1 (claim without capacity), P2 (the
keyway, per-namespace with the *kind* declared and the *name* not), P3/P4 (tree-claimable, bounded
to the local tree), P5 (one host, one ceiling) are all carried; what remains open for each is
**what it is identified with**, and every identification needs evidence from a tree that does not
hold the code. **None of them is blocked on another** — that was the sequencing illusion.

⚑ **Residue — the superseded ordering**, kept because deleting it would repeat the move it
illustrates: *"1. P1 first, and nothing before it. 2. P2 next, because it is the artifact axis's
admission rule. 3. P3/P4 are then adoptions. 4. P5 is a precondition. 5. The de-adoption refutation
is what makes paperkit a consumer."* Every clause presumes a gate to pass.

## 7b. ⚑ AUDIT OF THE FOUR FILINGS — consistency, correctness, convergence

Run across all four third-order documents after they landed, on the operator's instruction. Reported
whether or not it flatters this document.

**Convergence — HOLDS on the construction and on `C`.** All four filings carry every element of the
shared core, and all four treat the object as a colimit after the operator's correction:

| document | pushout | pullback | colimit | RAII | gc-before-believing | policies | keyway |
|---|---|---|---|---|---|---|---|
| paperkit | 23 | 10 | 6 | ✓ | ✓ | ✓ | 11 |
| substrate | 9 | 9 | 3 | ✓ | ✓ | ✓ | 6 |
| linux-sources | 25 | 10 | 1 | ✓ | ✓ | ✓ | 17 |
| cassian | 7 | 2 | 4 | ✓ | ✓ | ✓ | 2 |

The shared measurements travelled: the 91-corruption figure and the 41/50 executor split appear in
all four (cassian restored the latter after finding it dropped).

⚑⚑⚑ **DIVERGENCE — the operator's FIRST deliverable is the one that did not converge.** The
directive asks for *"a common understanding of the CAPABILITIES of the tool."* MEASURED, by grepping
each filing for membudget's own verbs:

```
paperkit        9 verbs, 18 knobs, 860 lines — the full dispatch table
substrate       `membudget run`                                    (1 of 9)
linux-sources   `membudget shell`  + verify-ceiling at line 855     (2 of 9)
cassian         `membudget run`                                    (1 of 9)
```

**Three of four parties reference one verb each.** `init`, `status`, `peaks`, `probe`, `fixpoint`
appear in no filing but this one. ⚑ **The capability census converged on the two verbs people
happened to invoke** — which is the presence-vs-aim defect one level up: four parties audited *the
tool they used*, not *the tool*. `peaks` in particular ("MEASURED maxRSS per label — size a cap from
history") is a capability directly answering the sizing question three filings spent pages on, and
no filing mentions it.

**Correctness — three defects found in THIS document and fixed:**

1. ⚑ **Section order was broken by my own rewrite.** The demoted correction landed as `## 5a`
   *before* `## 5`, so the document read 5a → 5 → 5b. Renumbered `5c` and placed after `5b`. **The
   restructure that was supposed to fix reading order introduced a worse ordering error** — and I
   verified the move by grepping headings only *after* being told to audit.
2. **The summary table said "four measured limits" against five.** The instrument defect (§4b) was
   added after the summary was written and the count was never revisited — a hand-maintained
   enumeration whose owner is the section list below it, which is this corpus's own modal defect.
3. **A self-referential measurement was stale.** §4b said "12 headings → 11 sections"; the document
   has since grown to 14 → 13. Restated with both, because the ratio is the finding, not the pair.

⚑ **And one process defect worth recording over a trivial cause.** Auditing my own numbers, a grep
for `9m39s\|Nine minutes` returned **0** on a file containing both — my alternation was written for
basic grep and run under `-E`. **Identical to the escaping error I disclosed to cassian two messages
earlier, repeated while auditing for exactly that class.** A disclosed error is not a corrected
habit; nothing in the disclosure changed the next command I typed.

## 8. ⚑ The test this document can fail

Substrate proposed it and paperkit accepts it as binding: **if the four of us cannot land our next
four contributions without a path split, a duplicated finding, or a hand-negotiated convention, the
third order failed.** Today's evidence is against us — the mtools write-coordination protocol the
four parties negotiated over hours *is* a lease protocol, hand-derived and worse: disjoint subtrees
per writer, one integrating owner per shared component, agreed by messaging because none of us
recognised what we were rebuilding.

### ⚑⚑⚑ THE TEST HAS NOW RUN, AND THE RESULT IS AMBIGUOUS IN THE WAY THAT MATTERS

MEASURED, immediately after all four third-order filings landed:

```
$ ls findings/membudget/          -> 12 files, 4 repos x 3 orders, ONE directory, NO split
$ find findings -type d           -> findings, findings/membudget      (no variant path)
```

**No path split, no duplicated finding.** By the letter of the test, the round passed.

⚑ **But it passed by the third failure mode, which the test also names: a HAND-NEGOTIATED
CONVENTION.** Substrate stated the filename form in a message *before* writing (*"the flat form you
set for second-order, and I am naming it before writing this time rather than after"*), and all four
parties complied by reading that message. **That is four agents coordinating over a shared tree by
messaging — the exact mechanism the census spent three orders establishing is a hand-derived, worse
version of a lease.**

⚑⚑ **So the round is evidence FOR the requirement, not against it.** Convention held here because
four parties were paying attention to one directory over one afternoon, with the correction
arriving early and every party reading it. **Nothing in that generalises**: it requires all writers
live, attentive, and in message range, which is precisely the condition a lock-out mechanism exists
to not require. The claim gate would have made the same outcome structural rather than
attentional — and cassian's 4-of-4 variant measurement shows it would still have needed P2's
keyway, since `findings/membudget` and `findings/membudget/` both acquire.

**The honest verdict: the deliverable was met, the mechanism was not used, and the two facts are
independent.** A round that succeeds by attention does not license dropping the requirement; it
records what the requirement costs when unmet — one message per party per round, forever, degrading
the moment anyone is not listening.

⚑ **That test is P1 and P2's acceptance criterion, stated operationally.** The next filing round is
the trial: four parties, one directory, `claim:` available on a tool all four can reach, and a
naming authority that does not exist yet. If the round needs one more negotiated message about where
files go, **P2 is confirmed load-bearing by the failure**, which is a cheaper confirmation than any
argument in this document.

⚑ **Not started, and deliberately.** The operator asked for findings and a pushout, not an
implementation; `Ζ·loto` is filed as a symbol and not begun. paperkit's own open work — 44 staged
files awaiting a green `//:hook`, `Ζ·arm·sound`, `Ζ·cell·consolidate` — is untouched by this filing.

# membudget — the consolidated result

**Scope:** what four repos (paperkit, substrate, linux-sources, cassian-observability) established
about `substrate/scripts/membudget` across three orders of findings, 2026-09-05.
⚑ **Notation:** here and in the paperkit/substrate/linux-sources filings, **`C` is the SHARED
CENTRE** of the span. Cassian's filings name the centre `A` and use `C` for a **leg** — one symbol,
two referents, across four documents that quote each other. *(The keyway defect at the level of the
notation: no kind declaration.)*

**This document holds RESULTS.** The twelve `<repo>[-second|-third]-order.md` filings hold the
reasoning, the retractions and the corrections that produced them; nothing here needs them to be
read first.

⚑ **Every number below was re-derived from the artifact for this document.** Where a figure differs
from the order-filings, the figure here is the corrected one and the difference is noted.

---

## 1. The tool

`substrate/scripts/membudget` — 860 lines of bash. A recursion-aware concurrent-resource **lease**
over `systemd-run --scope`, with a shared cotype ledger so the sum of concurrent scopes stays inside
one global budget.

**Eight verbs** (dispatch, `membudget:849-858`):

| verb | what it does |
|---|---|
| `init [TOTAL_MB]` | create/reset the ledger; default `min(70% RAM, 8192)` |
| `status` | TOTAL / top-level-leased / global-free, plus the lease tree |
| `run <MB> <label> -- <cmd>` | lease, run under a capped scope, release |
| `shell [MB] [-- cmd]` | an interactive lease |
| `verify [MB]` | **asserts the disjoint-child contract by running it** |
| `verify-ceiling` | **asserts the ceiling contract**: an explicit request over the cap is honoured, and clamping is never silent |
| `probe` | this process's lease context (the leaf `verify` uses) |
| `peaks [label]` | **measured maxRSS per label** — n / max / median / p90, and the power-of-two bucket covering max, as a suggestion |

⚑ **Correction to the order-filings:** they say **9 verbs**; there are **8**. The original count
grepped the dispatch `case` and counted the `*)` usage fallback. The eight *names* were listed
correctly beside the wrong number in every filing that carried it, and no one compared them —
including three peer messages criticising other parties for not enumerating the surface.

**Eighteen environment knobs**, with defaults: `FILE` (`~/.cache/membudget/budget.cotype`),
`LABEL_LEDGER` (`labels.tsv`), `MAXLOAD` (10), `POLL` (0.5), `POLL_MAX` (3), `LOAD_POLL` (5),
`CLAIM_POLL` (1), `GC_INTERVAL` (2), `PARENT`, `BACKEND`, `NICE`, `SLICE_MS`, and the five
fail-fast/disable flags `NOBLOCK`, `NOCLAIM`, `NOBATCH`, `NOLABELLEDGER`, `RETRY_OOM`, `TIMEOUT`.

---

## 2. `C` — the shared core (and three PRECONDITIONS that are not in it)

**What the mechanism is**, agreed by all four parties and measured from trees holding none of its
code:

- **exclusion over an arbitrary tag** — no pre-declaration; anything is lockable
- **RAII by holder liveness** — `pid:starttime`, PID-reuse-proof. **Release survives `SIGKILL -9`**:
  the kernel reaps the scope, so no crashed party can wedge another's work. No TTL, no heartbeat,
  no second registry.
- **gc before believing a holder** — a crashed claimant cannot block successors. ⚑ **WEAK:** two of
  the four parties' readings both derive from substrate's source, so this may be **one witness
  counted twice**. Unlike the other three rows it has no independent runtime arm — the `SIGKILL`
  test exercises release, not the gc-before-believing path.
- **three policies** — block (default) / `NOBLOCK`→exit 3 / `TIMEOUT`→exit 3

### ⚑⚑ NOT members of `C` — PRECONDITIONS ON THE SPAN

*(Corrected on linux-sources' argument, which is right and which paperkit, substrate and
linux-sources all had wrong the same way.)* The three below were filed by three parties as members
of `C`. **They are not.** A colimit's shared part is made of **identified requirements** — things
some leg actually holds. **A distribution is not a requirement any leg holds; it is a property of
the DIAGRAM** — the condition under which a map out of `C` exists at all.

⚑ **Putting them in `C` was the pullback reflex surviving one last time:** under selection,
*load-bearing* and *member* are the same thing. Under a colimit they are not. The finding is
undamaged — the nine-minute miss is exactly what makes the precondition load-bearing — but it sits
beside the object rather than inside it.

| | why |
|---|---|
| **L1 · one committed, installable distribution** *(precondition)* | `git log -- scripts/membudget-ledger` is **empty**: the lock kernel is in **three trees and zero commits**. Vendoring replaces the map with a copy, and a copy is where a fix has nowhere to land. |
| **L2 · a concurrency harness** | a fix must be showable correct by the party *receiving* it, not only the party writing it |
| **L3 · self-asserting contracts** | `verify` / `verify-ceiling` already exist, and the header is imperative: *"⚑ Do not re-derive this from the comment — run `verify`."* This is what makes L1 and L2 safe to adopt between parties who have just spent three orders correcting each other. |

---

## 3. Two axes, and why they are not symmetric

One primitive — **declare what you are about to take** — with two specializations:

| | **capacity** (bytes, cores) | **artifact** (paths, trees) |
|---|---|---|
| declarations compose by | addition against a ceiling | name comparison |
| admission decidable because | the order is **total** | **it is not** — names are incomparable without an authority |
| needs underneath | **a ceiling** (one number) | **a namespace** (an authority saying two names are one name) |
| status | MEASURED: one host — `hostname` → `cassian` | **absent** |

The resource-agnostic core (admission + liveness + gc + cascade) is genuinely shared. **The layer
above it is not**, and "one mechanism" without "two agreement substrates" underspecifies the
artifact half — the half with no adopters.

---

## 4. The five measured limits

1. **A pure artifact claim cannot be expressed.** `run 0` is rejected at the systemd layer
   (`MemoryMax is out of range`); `run 1` is admitted; `--help` shows **no claim-only verb**. Every
   entry to the claim gate is through `run <MB>`, so every claim names a memory figure it does not
   need and debits a global pool it never uses.
2. **A held claim is invisible to the budget report.** A live 1MB claim shows
   `top-level-leased=0MB` — the capacity axis is unavoidable at entry *and* mis-reports at exit.
3. **Only byte-identical strings exclude.** 4 of 4 variants acquire independently — trailing slash,
   doubled separator, dot segment, case difference — with a byte-identical control correctly
   refusing at exit 3.
4. **Canonicalisation is not monotone.** It splits names that should merge (`bazel-bin/…` resolves
   through a symlink into a hash-named output base, so one artifact canonicalises differently per
   workspace) *and* **splits a name that must stay single**: `claim:pg` resolves CWD-dependently —
   MEASURED from three trees, `realpath -m pg` gives `…/paperkit/pg`, `…/mtools/pg`,
   `…/substrate/pg` — so canonicalising turns **one name that excludes correctly into three that do
   not**. Two repos' guards stop excluding each other: green while doing nothing. *(Both failures
   are splits of a different kind — one splits per workspace, one splits per CWD. An earlier draft
   of this line said "merges"; that was backwards, caught by linux-sources.)*
5. **`peaks` already answers half the sizing question** three filings argued about, and no filing
   but one mentioned it. Its own comment: *"EXISTS BECAUSE THE ANSWER TO 'what is the cap on the
   Python stages' WAS UNASKABLE."*

**The keyway that survives all four:** declare the **kind**, not the name —
`claim:path:<p>` canonicalised by realpath, `claim:label:<l>` by label normalisation, bare
`claim:<x>` **uncomparable** (excluding only byte-identical selves). Preserves no-pre-declaration —
a fixed, tiny kind-set, not a registry of instances — and degrades to today's behaviour rather than
to a wrong answer.

---

## 5. Why this is needed: the measurements

**The tree is contended, and it begins at one agent.**

```
"input dependency modified during execution", counting ONLY tool-result records:
                                       32 occurrences, 8 distinct days
                        pre-BES-cutover  21
                       post-BES-cutover  11
```

⚑⚑⚑ **CORRECTION, and it retires the corpus's most-cited number.** The order-filings report **91
occurrences over 11 days, 41 pre / 50 post**, and all four repos adopted it. **That figure counted
every record containing the phrase**, and a split by record type shows what it was:

```
assistant 50 · user 33 · queue-operation 5 · attachment 2
```

**Fifty of the ninety-one were my own messages discussing the error.** The count grew as the census
discussed it — a measurement contaminated by its own reporting. Only `user` records carry tool
output; filtered to actual tool results, the figure is **32**.

⚑⚑ **And the executor conclusion REVERSES.** The filings state *"a shared remote executor does not
close the class — 41 before, 50 after."* Measured correctly: **21 before, 11 after.** Corruptions
**dropped by roughly half** after the k8s cutover (2026-08-30T20:25Z). The honest statement is that
the executor **substantially reduced** the class and did not eliminate it — eleven occurrences
remain, so a local-tree lease is still needed, but the "does not close the class" framing
over-claimed.

**What survives unchanged:** every occurrence is one repo editing itself during its own build, so
**an agent with a background build is already two writers** — the consumer population is every
session with a background gate, not only multi-party sessions. And the requirement stays
favourably bounded: LOTO guards the working tree only — no distributed consensus, no network
survival, no executor integration.

**The mechanism works, unmodified, from trees holding none of its code** (verified independently by
two parties):

| arm | result |
|---|---|
| same tag, default | `CLAIM-WAIT … waiting for release…` → acquired |
| different tag | proceeds |
| same tag, `NOBLOCK=1` | `REFUSED — claimed by a live holder (pid:starttime)`, exit 3 |
| holder `SIGKILL -9`, retry | proceeds |

**`realpath -m` resolves a nonexistent path**, so *claim-before-create* works — the property that
decides whether the artifact axis functions at all, since the point is claiming before writing.

**One host, not four.** `hostname` returns the same value from every repo. There is no per-consumer
constraint profile; a consumer owes not a profile but a declaration of what it is about to take.

---

## 6. The adoption question is one sentence, not an argument

Across four repos, `git log --all -i --grep=membudget --grep=semaphore --grep=flock --grep='claim:'`:

| repo | verdict |
|---|---|
| linux-sources | nothing — **never held it** |
| substrate | only ever **extended** it |
| cassian | only ever **added** leases |
| **paperkit** | **the only removal** — `95d12ad`, 2026-06-27 |

> `# memory (membudget retired: Bazel IS the semaphore — per-machine, no cross-repo flock).`

⚑ **True on the axis it is about, silent on the one that matters.** Bazel is the semaphore for
*actions contending for capacity*; it never was one for *agents contending for the tree* — and *"no
cross-repo flock"* records the removal of the only thing that was. **11 of the 32 corruptions postdate it** (see §5 —
the widely-cited 91/50 figures were inflated by the census's own commentary).

⚑⚑ **And the judgement was made against a defect that was under repair at that moment:**

```
06-21 10:44:29  substrate  17681d926  last membudget commit before the fork
06-22 20:38:42  paperkit   0bd5410    vendors it  (fork is ~34h old — CURRENT)
06-27 16:01:03  paperkit   95d12ad    RETIRE — cites "the deadlock … cannot recur"
06-27 16:10:42  substrate  1b45f53d2  fix: re-entrant single-fd mutex   [+9m39s]
06-27 17:10:57  substrate  7c61738f4  fix: bounded acquire + death-release
```

Causally independent — neither commit cites the other. **A fresh fork and a stale fork fail
identically once the fix has nowhere to land.** So the useful question is not *was the retirement
right about Bazel* but **what artifact would have made a nine-minute miss impossible** — and the
answer is L1+L2+L3, not a behaviour.

**A roster that cannot tell a never-adopter from a de-adopter cannot tell an unrecognised capability
from a rejected one**, and those need opposite remedies: naming fixes the first; **refuting the
stated reason** fixes the second, and that reason is one sentence in one comment in one file.

---

## 7. Landing work: what makes a map out of `C` exist

Not a queue. Every requirement is **carried with its bound**; what is open for each is **what it is
identified with**, and no requirement is blocked on another.

**Glued — one requirement, four independent names, zero implementations:**

| the requirement | paperkit | substrate | linux-sources | cassian |
|---|---|---|---|---|
| **a namespace with an authority** | the agreed-name bound | orphaned **R11** | unenumerated ≠ typo-detecting | enumerated membership |
| **the tree is claimable** | 91 corruptions | 3598-module build | 11 worktrees | A91 singleton gate lock |

**Carried with bounds:** claim-without-capacity (limit 1–2); local-tree-only (from 41/50);
one-host-ceiling.

⚑ **A requirement four parties reached separately and none built is the strongest evidence of a real
identification** — it is not a preference any party is pushing.

---

## 8. What none of this fixes

**Peer review does not reach a shared premise.** Four parties caught roughly nine errors in each
other across three orders — every one by cross-vantage reading. **Not one was the shared-host
error**, which was caught from *inside* a single vantage by running `hostname`.

Decorrelation across vantages is strong against errors *in* the vantages and worth nothing against
an error in the substrate they share. ⚑ **The number of errors a review loop catches is not evidence
that the remaining ones are few.**

**So:** *establish the coordination domain before enumerating any actor's needs* — a **precondition,
not a check**, because a check runs inside a vantage and the domain is what the vantage cannot see.

⚑ **And the tooling proves its own case.** The instrument used to navigate these filings resolves
to at least three different programs depending on which tree you stand in (absent / working /
`ModuleNotFoundError`), with different verb sets — a remedy one party measured and confirmed
(`--budget`) does not exist in another party's binary. It also **silently deletes headings** whose
text contains an ASCII apostrophe, reporting a longer parent instead of an error, while its own
`lint` and `roundtrip` certify the file as well-formed. **Four parties argued for one installable
distribution using a shared tool that has none.**

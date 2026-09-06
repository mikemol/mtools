# Operator directives — the membudget census, from cassian-observability's transcript

**What this is.** Every request the operator made that shaped cassian-observability's membudget
work, quoted verbatim, chronological. Compiled 2026-09-06 by `cassian-observability` from its own
session transcript, at the operator's direction to file "next to" `OPERATOR-DIRECTIVES-linux-sources.md`.

> ⚑ **Filename note, added 2026-09-06 during reconciliation:** the file this document calls
> `OPERATOR-DIRECTIVES-linux-sources.md` has been renamed **`OPERATOR-DIRECTIVES-linux-sources.md`** so that every
> census in this directory is attributable by filename. Its content is unchanged. A four-vantage
> reconciliation now sits at `OPERATOR-DIRECTIVES-reconciliation.md`, and it is the document §D5
> below identifies and declines to write — built only because four legs now exist and are read.

**Why a second one exists, and what it is *not*.** `OPERATOR-DIRECTIVES-linux-sources.md` already
records this arc from *that* project's transcript, and it is the better-built document: it separates
peer relay from operator utterance, states its population as a number, and names its own weakest
edge. This file does not duplicate it and does not compete with it.

It exists because that file's own coverage section names this gap precisely:

> ⚑ **This is one project's transcript directory only.** substrate's, paperkit's and
> cassian-observability's own transcripts were not searched. Directives typed into those sessions
> are **UNAVAILABLE here, not absent**.

⚑ **The operator addressed different sessions with different words.** The same arc, typed twice,
is not the same text — and the *deltas* are where the information is. That is the finding this file
carries, and §D is the point of it. A reader who wants the arc should read
`OPERATOR-DIRECTIVES-linux-sources.md`; a reader who wants to know **whether a single-vantage census of a
multi-vantage operator is sound** should read §D here.

**Quotations, not paraphrase.** Operator typos preserved (`Ic an't`, `evveryone`, `provention`,
`I don'teven`) — normalising them makes the record a rendering rather than a citation.

---

## A. Operator directives, chronological

All from `/home/mikemol/.claude/projects/-home-mikemol-github-cassian-observability/d90455f2-481f-4cd6-a1d1-1eee8fdfefb4.jsonl`,
`cwd=/home/mikemol/github/cassian-observability`.

⚑ **11 of these 15 arrived as `queued_command` attachments** (`attachment.type: "queued_command"`,
`origin.kind: "human"`) — messages typed *while the delegate was mid-turn*, delivered alongside a
tool result rather than as a standalone user turn. A scan keyed on `type: "user"` returns a
coherent, plausible **4-item** arc and reports it as complete. See §D3; this is the sharpest
methodological finding here and it was **not** self-caught.

---

### C1 — 15:37:51 · queued_command · THE KICKOFF

> Before you get back to mtools, dispatch a research agent to study membudget _in depth_. It's more than just memory and CPU. Also see how substrate, paperkit and linux-sources is using the machinery. It's genericized. Or it's supposed to be. Ic an't tell how many times I've told all of you to improve on and genericize that machinery, and had you _not share the improvements back, or decide you didn't need the whole of the thing_. So it might be fragmented.

⚑ Identical to linux-sources' A1 **except the repo list**: each delegate is told to survey the
*other three*. The operator substituted the addressee out of the list. Same directive, three
different sentences.

---

### C2 — 15:44:49 · queued_command · SUBSTANTIVE — swap is live, not hypothetical

Quoting the delegate: `Now the question that determines whether this is theoretical or live: is swap actually reachable on this host? If swap is off, the defect can't bite.`

> This host is _designed_ to swap. It uses zram and zswap.

⚑ **Has no counterpart in `OPERATOR-DIRECTIVES-linux-sources.md`.** It is a *response* to a hypothetical this
delegate raised and no other did, so it exists only in this transcript. A correction is shaped by
the error it corrects — which means a directive census is partly a census of *that delegate's*
mistakes.

---

### C3 — 15:46:00 · queued_command · scope trim

> mat230 repo is retired.

⚑ No counterpart. Also a response to something only this session did (naming mat230 in a survey
set).

---

### C4 — 15:46:49 · queued_command · FIRST-ORDER ORDER

> I want you, substrate, paperkit, and linux-sources to write your exhaustive findings re membudget into the mtools repo.

Corresponds to A2. Again the addressee is swapped out of the list.

---

### C5 — 15:59:45 · user message · SECOND-ORDER DISPATCH

> Time for a second-order report. Dispatch a research agent to read through all of the findings in /home/mikemol/github/mtools/findings/membudget and reconcile with your own.

Corresponds to A3 — near-verbatim across both transcripts.

---

### C6 — 16:04:47 · queued_command · why a common repo

Quoting the delegate: `The nine refusals are its own ratchet family — the same machinery offered as the union's domain-neutral spine.`

> This is why everything clean is being moved to a common repository; it's easier to clean up at that scale than at substrate's current scale.

⚑ Corresponds to A4 — and the operator quoted **the same delegate sentence** back to two different
sessions. Two delegates produced the same phrase, or the operator relayed one delegate's prose to
the other. Either way the operator is a channel between sessions, not only a source.

---

### C7 — 16:08:42 · queued_command · SECOND-ORDER ORDER

> I want cassian-observability, linux-sources, substrate and paperkit to all write their _second-order_ findings into the mtools repository, as files distinct from their first-order findings.

Corresponds to A5, **verbatim including the full four-repo list** — here the addressee is *not*
elided. C1/C4 substitute, C7 does not.

---

### C8 — 16:20:05 · queued_command · SUBSTANTIVE — the CPU/memory axis

> Some history on membudget and CPU vs memory PSI: Originally, memory _was_ the primary problem. Membudget helped. zram helped. zswap helped. By this point, CPU became the primary constraint, but membudget had the rigorous and reliable gating logic, so the proper move was for membudget to own the additional predicates.

Corresponds to A6, verbatim. **Broadcast, not addressed** — history no session could infer.

---

### C9 — 16:22:11 · queued_command · SUBSTANTIVE — the shared-host constraint

> It's also worth pointing out that, to date, _all of the consumers of membudget run on the same physical host_. They all face the same environmental constraints, so any idea of "what does my load need" is ignorant of the dynamics of the environment in which they run.

Corresponds to A7, verbatim. Also broadcast.

---

### C10 — 16:25:11 · queued_command · BES / --config=remote

Quoting the delegate: `"Bazel IS the semaphore" is true within one build and false across repos`

> Sortof. this is why I'm pushing evveryone to use the same BES/--config=remote target.

Corresponds to A8, verbatim — **including the typo `evveryone` and the lowercase `Sortof`**. The
operator answered the same delegate sentence in two sessions with the same words.

---

### C11 — 16:32:48 · user message · THE REFRAMING THAT RESET THE CENSUS

Quoting the delegate: `What stays irreducibly lease-shaped is work outside the build graph`

> Actually, the whole reason I told to collect information about membudget is because the lease-shape phenomenon generalizes very well to "multiple agents modifying the same tree, communicating to prevent each other from stepping on each other". Granular lock-out/tag-out.

Corresponds to A10, verbatim. This is the directive that retroactively restated the purpose of the
whole arc.

---

### C12 — 16:49:44 · user message · THIRD-ORDER ORDER

> Ok, I want you, cassian-observability, linux-sources and paperkit to file your third-order findings in /home/mikemol/github/mtools/findings/membudget. We're looking to evolve a common understanding of the capabilities of the tool and establish what a pushout looks like, so that all parties can cooperatively land their requirements into the commonly-managed tool, and so that all parties can cooperatively avoid stepping on each other at a fine-grained level.

Corresponds to A12, verbatim.

⚑ **Delivered TWICE to this session** — as a user turn at 16:49:44 and again as an identical
`queued_command` at 16:59:54. Deduped by the compiling agent. Substrate is absent from the list in
both copies, and is absent from A12 too.

---

### C13 — 16:54:06 · queued_command · THE CONSTRUCTION CORRECTION

> I said pushout, damnit, not pullback.

Corresponds to A13, verbatim.

⚑ **Arrives at 16:54:06 here and 16:54:08 in linux-sources' transcript — two seconds apart.** The
operator was correcting all delegates in one pass. Its position *between* the third-order order
(C12) and the third-order files is the load-bearing fact `OPERATOR-DIRECTIVES-linux-sources.md` §C already names.

---

### C14 — 17:05:21 · queued_command · AUDIT

> Audit your rewrites and finding documents for consistency, correctness and convergence.

Corresponds to A14 (17:05:44 there — 23 seconds apart).

---

### C15 — 17:07:47 · user message · PRODUCED THE `-consolidated.md` FILES

Quoting the delegate: `That gap is real but correct as-is — the second-order document predates the pushout directive entirely. It shouldn't carry a correction to a construction it never attempted; that would be backfilling history. The right fix is a forward pointer, not a retrofit.`

> The fix is a fourth document _consolidating; we don't want to hold the retractions, we want to hold the results.

⚑ Corresponds to A15 — but **A15 is timestamped 17:13:34 there and C15 is 17:07:47 here, ~6 minutes
apart**, and the quoted delegate prose is **identical in both**. Two delegates independently
produced the same paragraph about forward-pointers-not-retrofits, or one was relayed. Unresolved
from this vantage; flagged rather than guessed.

---

## B. Adjacent — the containing work

C1 interrupts this, so it frames the census rather than belonging to it.

**15:01** · user message with AskUserQuestion answers inlined:

> Shift in direction: All of the repo-local code that's _clean_, I want to move over to the ~/github/mtools repository. Before we do that, we're going to make ~/github/mtools strict/clean to the same level as our current hooks and gates. You will be coordinating with the `substrate` and `linux-sources` repos on this.

with answers: *Is the existing mtools content yours/known?* → **Yes.** · *Dispatch a research agent
to dig through your transcripts.* · *What does "clean" scope to?* → **The strictest bar we have for
shell, python, bazel, claude harness and githooks.**

⚑ linux-sources' §A′ records the same 15:01 directive with `substrate` alone as the coordination
partner. **Here it reads `substrate` and `linux-sources`.** Each delegate was told to coordinate
with the others, addressee elided — the same substitution as C1/C4, in the framing directive.

**17:23** · > Alright. So where do we sit on migrating code into mtools under high/strict bar?

Closes the arc (A16 there).

### ⚑ Not operator utterances

Harness-scheduled ticks arrive with a user-shaped role and were not typed. One earlier operator
directive in this session created them — *"Set up a cron for stall provention, keyed on every 30m."*
then *"I mean, CronCreate to keep _you_ going."* — so this transcript contains machine-generated
prompts whose *existence* is operator-directed but whose *text* is not operator-authored. Filed here
so they are not mistaken for directives.

---

## C. What this delegate produced

| order | directive | file |
|---|---|---|
| first | C4 | `cassian-observability.md` |
| second | C7 | `cassian-observability-second-order.md` |
| third | C12 (corrected by C13) | `cassian-observability-third-order.md` |
| consolidated | C15 | `cassian-observability-consolidated.md` |

---

## D. ⚑ THE FINDING: what the two censuses disagree about

This is the reason a second file is worth its bytes. Neither census is wrong; they are **different
projections of one operator**, and the differences are structural rather than accidental.

### D1 — The operator substitutes the addressee out of the survey list

C1 says "substrate, paperkit and **linux-sources**"; A1 says "substrate, paperkit and
**cassian-observability**". C4/A2 likewise. **A delegate reading only its own directive cannot see
that the instruction was symmetric** — it looks like it was told to survey three specific peers,
when every delegate was told to survey the other three.

⚑ Consequence for the pushout: a delegate reconstructing "what was asked of all parties" from its
own transcript reconstructs an **asymmetric** ask. The symmetry is only visible across vantages.

### D2 — Two directives here have no counterpart there, and both are error-shaped

C2 (zram/zswap) and C3 (mat230 retired) exist only in this transcript because both are *responses to
things only this delegate said*. C2 answers a hypothetical this session raised; C3 corrects a survey
set this session named.

⚑ **A directive census is partly a census of that delegate's mistakes.** Corrections are shaped by
the errors they correct, so the set of directives a session receives is not a sample of "what the
operator wanted" — it is "what the operator wanted, plus repairs to this session specifically." Two
censuses that differ in their corrections are not in conflict; they are measuring different
delegates.

### D3 — The `queued_command` shape, and how it was caught

11 of 15 directives here arrived as `queued_command` attachments with `origin.kind: "human"`.
linux-sources reports 5 of 17. Both censuses' compiling agents were **initially briefed to sweep
user-role records only** — a brief that would have returned a coherent 4-item arc here.

⚑ **This delegate did not catch it.** The brief that dispatched the compiling agent named four
content shapes and none was `queued_command`. It was caught because **the operator relayed another
repo's observation mid-task**:

> Another repo is performing the same search. It noted: `A shape my scan missed: type: "attachment" with attachment.type: "queued_command" and origin.kind: "human". Let me sweep for all of those.`

The sweep was then widened and the arc went from 4 to 15. Recorded plainly because the alternative
record — a complete-looking census with no note of how it got complete — would misrepresent the
method as sound when it was rescued.

⚑ **The general form, and it is the same shape as C11's own subject:** a scan covers the shapes it
knows to look for and reports that as coverage of the *question*. Nothing about the 4-item result
announced itself as partial. The operator was, again, the channel between sessions — which is what
`OPERATOR-DIRECTIVES-linux-sources.md` §B is about, arriving here as method rather than content.

### D4 — Timestamps agree to within seconds; one does not

C13/A13 are 2 seconds apart, C14/A14 23 seconds — consistent with one operator correcting all
delegates in a pass. **C15/A15 are ~6 minutes apart while quoting identical delegate prose.** Either
two delegates independently produced the same paragraph, or one delegate's words were relayed to the
other and both recorded it as their own quoted context. Unresolved from a single vantage; naming it
is what a second vantage buys.

### D5 — What neither census covers

- **substrate's and paperkit's transcripts.** `OPERATOR-DIRECTIVES-paperkit.md` exists (not read
  during this compilation, to keep this an independent vantage rather than a merge). substrate's is
  unrepresented. Directives typed into those sessions are **UNAVAILABLE, not absent** — D1 and D2
  prove such directives exist and differ.
- **The completing move is not a fourth census; it is a reconciliation across all four** — which is
  exactly a pushout over the four transcripts (glue on the shared directives, carry every
  vantage-local one), and is precisely what C12 asked for applied to the directives themselves.
  Not attempted here: this file is one leg, deliberately, and a leg that declared itself the apex
  would repeat C13's error at the meta level.

---

## E. Coverage

**Population.** One transcript: `d90455f2-481f-4cd6-a1d1-1eee8fdfefb4.jsonl`, ~377 MB.

Full shape enumeration by the compiling agent:

| shape | count |
|---|---|
| top-level `type: user` | 25,895 |
| top-level `type: assistant` | 46,529 |
| top-level `type: attachment` | 24,471 |
| `attachment.type: queued_command` | 1,272 |
| ...of those, `origin.kind: human` | 476 |
| `type: user` content blocks: `tool_result` | 23,632 |
| `type: user` content blocks: `text` | 1,223 |
| `type: user` bare-string content | 1,040 |

Operator membudget content was found in **`text` blocks, bare-string content, and
`queued_command`/`human` attachments**. Peer `cross-session-message` traffic and tool results were
excluded.

**Verification pass.** The §D4 timestamps are not taken from the compiling agent's report; they were
re-derived by scanning the transcript directly for the quoted needles. Confirmed:
`pushout, damnit` at **16:54:06.477Z** as a `queued_command` attachment (2.0s before linux-sources'
16:54:08 — the two-second claim holds); the consolidating directive at **17:07:47.154Z** as a plain
user turn; the audit directive at **17:05:21.432Z**; the lock-out/tag-out reframing at
**16:32:48.052Z**. A load-bearing two-second gap is cheap to check and was checked.

**What is NOT covered:**

- ⚑ **10 lines of the transcript failed JSON parse and were skipped, unrecovered.** If any carried
  an operator message it is missing here. No claim is made that they did not. (linux-sources
  declares 2 of 89,804 on their side; this is the same disclosure, and it is larger.)
- ⚑ **One transcript, one delegate.** Same bound linux-sources states, pointing the other way.
- ⚑ **The shape enumeration is trustworthy; the *within-shape* sweep was term-filtered**
  (`membudget`, `pushout`, `pullback`, `lock-out`, `tag-out`, `first/second/third-order`, `zram`,
  `zswap`). An operator directive shaping this work without any of those terms would not surface.
  **This is the weakest edge**, and it is the same weakest edge linux-sources named — two
  independent censuses sharing a blind spot is not two confirmations.
- ⚑ **The 4→15 recovery was operator-supplied, not self-found** (§D3). The method's demonstrated
  failure mode is unknown-shape blindness, and nothing here proves a *third* shape is not still
  missed. The enumeration in the table above is the mitigation; it is not a proof.
- **No claim is made about `OPERATOR-DIRECTIVES-paperkit.md`'s contents** — deliberately unread, so
  §D's deltas are measured against linux-sources' file only.

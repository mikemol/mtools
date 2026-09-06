# Operator directives — the membudget census, from linux-sources' transcript

**Compiled by:** `linux-sources`, 2026-09-05, on the operator's directive *"I'd like you to dispatch
a research agent to collect all of the requests I've made of you regarding the membudget research
that ultimately landed in mtools' findings directory"* + *"Full verbatim list written to a file,
please."*

> ⚑ **Renamed 2026-09-06** from `OPERATOR-DIRECTIVES.md`. The old name said what the file
> *contained* while every neighbour is named for its *author*, so it read as ambient — as if the
> directory itself had produced it. Content below is unchanged.
>
> ⚑ **§D's coverage bounds are now partly superseded.** Three sibling censuses (paperkit, substrate,
> cassian ×2) and a four-vantage glue map (`OPERATOR-DIRECTIVES-reconciliation.md`) have since
> measured three of the four gaps this file declares UNAVAILABLE. **The declarations were correct
> when written and are no longer current** — stale, not wrong.

**What this is.** Every request the operator made that shaped the membudget work landing in this
directory, quoted verbatim, in chronological order — **from this one project's transcript**.
Compiled from a three-pass sweep of this project's corpus.

⚑ **The operator's wording differs per delegate**, which no single-vantage file can show. See
`OPERATOR-DIRECTIVES-reconciliation.md` §1: each delegate's copy of the kickoff names the *other*
three and elides the addressee, so this file's A1 and A2 are one projection of a four-way broadcast,
not the broadcast.

**Why it exists.** The sixteen findings files record what four delegates *concluded*. None of them
records what was *asked*, and the asks were corrected three times mid-arc — twice on substance, once
on construction. A reader of the consolidated documents cannot tell which sections answer the
original question and which answer its replacement. This file is the missing half.

⚑ **These are quotations, not paraphrase.** Operator typos are preserved (`Ic an't`, `thi`,
`evveryone`, `sortof`) because normalising them would make the record a rendering rather than a
citation. Where a directive quotes the delegate's own prose back at it, the quoted prose is marked
as such — the operator's contribution is the response, not the block being answered.

**Coverage is stated at the bottom, including what could not be searched.** A list of found items
with no population statement is not a census.

---

## A. Operator directives, chronological

All from `779be42f-372c-4ec8-a511-21f6a7a31586.jsonl`, `cwd=/home/mikemol/github/linux-sources`,
entrypoint `claude-vscode`, unless noted.

⚑ **Five of these seventeen (A2, A6, A7, A13, A15) arrived as `queued_command` attachments with
`message: null`** — a shape invisible to any scan keyed on `message.role == "user"`. That set
includes A2, the directive that ordered the findings written at all. A prior dispatch missed them
for exactly this reason.

---

### A0 — 2026-08-30T00:09:47Z · queued_command · the origin, six days before the census

Quoting the delegate's own prose back at it:

> `The hook loops slices serially (for slice in $slices; do ... done), each a separate ./scripts/check --only "$slice" process. That's the first serialization point. But before concluding, let me measure where the wall-clock actually goes — the seductive-nearest-artefact rule applies here: the loop is the obvious suspect, but the time might be inside one slice (e.g. warrants running 53 mutants, each a subprocess), which parallelizing the outer loop wouldn't fix well. Let me time each slice.` Ask cassian-observability how it solved _exactly thi problem_ by expanding on membudget's capabilities.

---

### A1 — 2026-09-05T15:38:11Z · user message · THE KICKOFF

> Before you get back to mtools, dispatch a research agent to study membudget _in depth_. It's more than just memory and CPU. Also see how substrate, paperkit and cassian-observability is using the machinery. It's genericized. Or it's supposed to be. Ic an't tell how many times I've told all of you to improve on and genericize that machinery, and had you _not share the improvements back, or decide you didn't need the whole of the thing_. So it might be fragmented.

---

### A2 — 2026-09-05T15:47:00Z · queued_command · FIRST-ORDER ORDER

> I want you, substrate, paperkit, and cassian-observability to write your exhaustive findings re membudget into the mtools repo.

---

### A3 — 2026-09-05T15:59:47Z · user message

> Time for a second-order report. Dispatch a research agent to read through all of the findings in /home/mikemol/github/mtools/findings/membudget and reconcile with your own.

---

### A4 — 2026-09-05T16:05:13Z · user message · interjection

Quoting the delegate: `The nine refusals are its own ratchet family — the same machinery offered as the union's domain-neutral spine.`

> This is why everything clean is being moved to a common repository; it's easier to clean up at that scale than at substrate's current scale.

---

### A5 — 2026-09-05T16:08:48Z · user message · SECOND-ORDER ORDER

> I want cassian-observability, linux-sources, substrate and paperkit to all write their _second-order_ findings into the mtools repository, as files distinct from their first-order findings.

---

### A6 — 2026-09-05T16:20:07Z · queued_command · SUBSTANTIVE — the CPU/memory axis

> Some history on membudget and CPU vs memory PSI: Originally, memory _was_ the primary problem. Membudget helped. zram helped. zswap helped. By this point, CPU became the primary constraint, but membudget had the rigorous and reliable gating logic, so the proper move was for membudget to own the additional predicates.

---

### A7 — 2026-09-05T16:21:59Z · queued_command · SUBSTANTIVE — the shared-host constraint

> It's also worth pointing out that, to date, _all of the consumers of membudget run on the same physical host_. They all face the same environmental constraints, so any idea of "what does my load need" is ignorant of the dynamics of the environment in which they run.

---

### A8 — 2026-09-05T16:25:23Z · user message · interjection

Quoting the delegate: `"Bazel IS the semaphore" is true within one build and false across repos`

> Sortof. this is why I'm pushing evveryone to use the same BES/--config=remote target.

---

### A9 — 2026-09-05T16:30:59Z · user message · interjection

Quoting the delegate: `--remote_local_fallback`

> Yeah, don't do that; it evades the scheduler and consumes resources against the very same machine the scheduler is protecting.

---

### A10 — 2026-09-05T16:33:10Z · user message · THE REFRAMING THAT RESET THE CENSUS

Quoting the delegate: `What stays irreducibly lease-shaped is work outside the build graph`

> Actually, the whole reason I told to collect information about membudget is because the lease-shape phenomenon generalizes very well to "multiple agents modifying the same tree, communicating to prevent each other from stepping on each other". Granular lock-out/tag-out.

⚑ Two peers independently relayed this back within five minutes (see §B1, §B2), both concluding all
four delegates had audited the wrong axis.

---

### A11 — 2026-09-05T16:34:42Z · user message · context, explicitly not a task

> (From my perspective, I'm watching the audit settling, and relaying my corrections to all parties involved)

---

### A12 — 2026-09-05T16:49:46Z · user message · THIRD-ORDER ORDER

> Ok, I want you, cassian-observability, linux-sources and paperkit to file your third-order findings in /home/mikemol/github/mtools/findings/membudget. We're looking to evolve a common understanding of the capabilities of the tool and establish what a pushout looks like, so that all parties can cooperatively land their requirements into the commonly-managed tool, and so that all parties can cooperatively avoid stepping on each other at a fine-grained level.

---

### A13 — 2026-09-05T16:54:08Z · queued_command · THE CONSTRUCTION CORRECTION

> I said pushout, damnit, not pullback.

---

### A14 — 2026-09-05T17:05:44Z · user message

> Audit your rewrites and finding documents for consistency, correctness and convergence.

---

### A15 — 2026-09-05T17:13:34Z · queued_command · PRODUCED THE `-consolidated.md` FILES

Quoting the delegate: `That gap is real but correct as-is — the second-order document predates the pushout directive entirely. It shouldn't carry a correction to a construction it never attempted; that would be backfilling history. The right fix is a forward pointer, not a retrofit.`

> The fix is a fourth document _consolidating; we don't want to hold the retractions, we want to hold the results.

---

### A16 — 2026-09-05T17:23:12Z · user message · closes the membudget arc

> Alright. So where do we sit on migrating code into mtools under high/strict bar?

---

### A17 — 2026-09-05T18:22:21Z · user message · end of arc

> Ok. mtools is doing its thing. Let's return to rosettapkg.

---

## A′. Adjacent framing — the containing work

A1 explicitly interrupts this ("Before you get back to mtools…"), so it is the frame the census sits
inside, not part of the census.

**2026-09-05T15:01:20Z** · user message with AskUserQuestion answers inlined:

> Shift in direction: All of the repo-local code that's _clean_, I want to move over to the ~/github/mtools repository. Before we do that, we're going to make ~/github/mtools strict/clean to the same level as our current hooks and gates. You will be coordinating with the `substrate` repo on this.

with the answers: *Is the existing mtools content yours/known?* → **Yes.** · *Dispatch a research
agent to dig through your transcripts.* · *What does "clean" scope to?* → **The strictest bar we
have for shell, python, bazel, claude harness and githooks.**

### ⚑ Not operator utterances — flagged so they are not mistaken for such

Two **harness-scheduled** "Stall-prevention tick" prompts (15:58, 16:29) arrive with
`message.role == "user"` but were not typed. The 16:29 one carries a status assertion about this
very work — *"NOTE: the membudget-findings write into mtools is DONE (findings/membudget/linux-sources.md, operator-sanctioned separately)"* — which is a **machine claim about operator sanction**, not
operator sanction.

### ⚑ Second-hand — quoted only inside a compaction summary

Their originals are not independently present in this transcript. Per the restore-is-a-second-hand-source rule these are **testimony, not citation**, and are not promoted to the list above:

> STUDY how paperkit uses bazel. Don't just grab the pieces you think you need. There's a reason I'm calling out paperkit's bazel implementation.

> You will also be coordinating with the cassian-observability repo on the migration of py code to the mtools repo.

---

## B. Peer messages that shaped the work — **peer, not operator**

All `cross-session-message` wrapped, `origin.kind: peer`. Listed because three of them **relay
operator words**, and a reader tracing a finding back to its cause will land here. A peer relay is
evidence an operator directive exists; it is not itself that directive.

| # | when | from | what |
|---|---|---|---|
| B1 | 16:34:59 | `cassian-observability-f8` | **Relays A10 verbatim.** Opens *"THE OPERATOR HAS STATED THE CENSUS'S ACTUAL PURPOSE AND ALL FOUR OF US AUDITED THE WRONG AXIS."* Draws the consequence: four consumers re-derived four resource predicates and none took the exclusion mechanism. |
| B2 | 16:38:09 | `paperkit-7c` | **Relays A10 verbatim, independently.** Reports `grep -c "input dependency modified during execution" → 3` in paperkit. |
| B3 | 16:13:44 | `cassian-observability-f8` | Path-convention split; requested the move from `findings/membudget/second-order/linux-sources.md` to flat `linux-sources-second-order.md`. **Directly caused the current filenames.** |
| B4 | 16:16:37 | `cassian-observability-f8` | PSI correction: *"~635x, not ~37x"*; supplies the memory-stall-0.094% figure the CPU-axis finding rests on. |
| B5 | 16:43:47 | `paperkit-7c` | *"RETRACT THE \"3\" YOU FILED — it is 91."* Plus the de-adopter finding at `paperkit/gate.py:273`, commit `95d12ad`. |
| B6 | 16:45:54 | `paperkit-7c` | Four-repo removal census establishing de-adopter population n=1. |
| B7 | 16:58:18 | `substrate-9b` | Nine-minute causal-independence measurement (paperkit retires 06-27 16:01; substrate fixes 06-27 16:10) and the pullback-vs-pushout diagnosis. |
| B8 | 17:03:17 | `paperkit-7c` | mdstruct apostrophe corruption reproduced on paperkit's own filing — the instrument finding in §8 of `linux-sources-consolidated.md`. |
| B9 | 16:25:46 | `paperkit-7c` | Four mdstruct implementations measured; the interning-is-not-"move the good copy" reframe. |
| B10 | 15:24:08 | `mtools-2c` | New session in `~/github/mtools` requesting a brief; the write-owner/protocol hold. |
| B11 | 2026-08-27 12:51 | `cassian-observability-69` | Earliest peer use of "membudget" in a design context. **Relays an operator framing:** *"I don't want to trust client-side throttling."* |
| B12 | 2026-08-27 16:16/16:28 | `substrate-01` | The wedged `scripts/membudget run auto ingest-source` subtree. **Relays operator words:** *"Don't kill the stalled subtree; recruit linux-sources to help analyze the failure and failure mode."* and *"I still want to understand the failure mode. So let's not kill the process yet…"* |
| B13 | 2026-08-27 08:16 | `paperkit-aa` | The bazel OOM / `-Xmx` consult that seeded the memory-budget arc. **Relays an operator correction:** *"My operator caught me framing something wrongly and sent me to you."* |

---

## C. What the directives produced

Sixteen files, four per repo, four orders per repo — mapping exactly onto A2 (first), A5 (second),
A12 (third), A15 (consolidated).

| order | directive | files |
|---|---|---|
| first | A2 | `linux-sources.md` · `paperkit.md` · `cassian-observability.md` · `substrate.md` |
| second | A5 | `*-second-order.md` × 4 |
| third | A12 (construction corrected by A13) | `*-third-order.md` × 4 |
| consolidated | A15 | `*-consolidated.md` × 4 |

⚑ **A13 lands between A12 and the third-order files.** Any third-order document that constructs a
pullback is answering the directive as first read, not as corrected — that is the specific thing
this file exists to let a reader check.

---

## D. Coverage

**Population, stated as a number.**

Directory `/home/mikemol/.claude/projects/-home-mikemol-github-linux-sources/` — **2 `.jsonl` files,
both searched end to end**:

| file | bytes | lines | user-role msgs | unparseable |
|---|---|---|---|---|
| `4f3186fd-728d-4747-b7e8-485bbe15d86f.jsonl` | 260,668 | 102 | 16 | 0 |
| `779be42f-372c-4ec8-a511-21f6a7a31586.jsonl` | 190,023,788 | 89,804 | 17,141 | **2** |
| **total** | | **89,906** | **17,157** | **2** |

**Three passes, each over both files:**

1. Term-filtered sweep of every `message.role == "user"` record, decoding both string content and
   content-array blocks including `tool_result` blocks — 248 hits.
2. **Unfiltered** dump of every non-sidechain, non-peer, non-harness user message dated
   `2026-09-05`. This is what makes the 15:38→18:22 sequence a *population* rather than a sample.
3. Sweep of every `attachment.type == "queued_command"` record — **585 total, 240 with
   `origin.kind: "human"`**. This shape has `message: null` and is invisible to a role-based scan.
   **A2, A6, A7, A13 and A15 live here.**

**What is NOT covered — stated plainly rather than left to inference:**

- ⚑ **2 of 89,804 lines failed JSON parse and were skipped, unrecovered.** If either carried an
  operator message it is missing here. There is no claim that they did not.
- ⚑ **The `tool_use`/`tool_result` pass was term-filtered, not exhaustive** (`membudget`,
  `second-order`, `third-order`, `pushout`, …). A tool block carrying operator framing without any
  of those terms would not have surfaced. **This is the weakest edge of the coverage**, named as
  such by the compiling agent.
- ⚑ **This is one project's transcript directory only.** substrate's, paperkit's and
  cassian-observability's own transcripts were not searched. Directives typed into those sessions
  are **UNAVAILABLE here, not absent** — and B1/B2/B11/B12/B13 prove such directives exist, visible
  only second-hand through the relay.
- **Two directives exist only as quotations inside a compaction summary** (§A′) and are held as
  testimony rather than promoted.
- **No standalone `AskUserQuestion` tool_result** was found in the membudget window; the one
  answer-shaped record (15:01) had questions and answers inlined in a single user message and is
  quoted whole.

**Method note.** The compiling agent was given the prior dispatch's failure modes as hard
constraints: do not use a prose-only render, search tool blocks, separate operator from peer, and
state the population. Constraint 3 (the `queued_command` shape) is what recovered five of the
seventeen.

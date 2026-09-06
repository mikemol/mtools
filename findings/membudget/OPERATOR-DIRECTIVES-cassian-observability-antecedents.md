# Operator directives — cassian-observability, the ANTECEDENTS and the two-directory census

**What this is.** A second, independent sweep of the operator directives that shaped
cassian-observability's membudget work — compiled 2026-09-06 by `linux-sources` over **both** of
cassian's transcript directories, and deliberately **not** a rewrite of
`OPERATOR-DIRECTIVES-cassian-observability.md`.

**Why it exists rather than replacing that file.** Cassian's own delegate compiled that document
from a single vantage and declared its bound honestly: *"One transcript, one delegate"*, term-filtered
within-shape, and a 4→15 recovery that was operator-rescued rather than self-found. This sweep was
dispatched independently, before that file was read, and it differs in two ways that are worth
keeping separate rather than merged:

1. ⚑ **It searched a SECOND DIRECTORY.** Two project directories exist for this repo —
   `-home-mikemol-github-cassian-observability` (4 files) and `-home-mikemol-github-cassian-obs`
   (1 file). The existing file covers one file of the five. **The result of searching the other
   four is a negative, and the negative is the finding** (§D).
2. ⚑ **It was not date-bounded to the census day**, so it recovered **eight pre-census directives
   spanning 2026-08-14 → 2026-08-30** — including the order that created `scripts/resource-lease`
   and the ruling that `cassian-observability.md` cites in its own bias disclosure but does not
   quote. Those are the directives a reader working *backward* from the findings needs, and no
   existing census carries them.

**Quotations, not paraphrase.** Typos preserved.

**Section IDs are `Q…`** to avoid colliding with that file's `C…` and `OPERATOR-DIRECTIVES-linux-sources.md`'s `A…`.

---

## A. The antecedents — 2026-08-14 → 2026-08-30

⚑ **None of these appear in any existing census.** All from
`d90455f2-481f-4cd6-a1d1-1eee8fdfefb4.jsonl`.

### Q1 — 2026-08-14T02:05:34Z · queued_command · the earliest membudget-adjacent ask

Quoting the delegate's own prose back at it:

> `Answered by the code: handwritten. summit's paper.toml projects only README.md from warrants.bib; the registry .md files are read by frontmatter.py, which splits (table, body, mode) and the loader consumes only the TOML frontmatter table — the markdown body below it is a hand-kept restatement that summit neither projects nor gates against the frontmatter. So membudget.md's body ("cited by nobody observed…") is duplicated by hand and can drift from cited_by = [] above it, un-caught.`
>
> That's worth reporting, too...

⚑ Three weeks before the census, the operator is already treating **membudget's registry entry
drifting from its own body** as reportable. The fragmentation thesis of the kickoff (Q9) is not new
on 09-05.

---

### Q2 — 2026-08-18T18:40:49Z · queued_command · ⚑ THE COVERAGE QUESTION, ASKED FIRST HERE

> What I don't get is whether or not the substrate makefile is applying membudget thoroughly, or if it's accidentally leaving some subprocesses out.

---

### Q3 — 2026-08-18T18:41:58Z · queued_command · the shim is a workaround, not the mechanism

> `make` should be applying membudget explicitly, not just leaning on the shim, though. The shim is there as a workaround for things that would otherwise skip it...

⚑ Q2+Q3 are the **coverage/escape** question — *which subprocesses evade the budget* — asked
eighteen days before the kickoff. A census that starts on 09-05 reads the kickoff as opening the
subject; it did not.

---

### Q4 — 2026-08-24T16:07:17Z · queued_command · SUBSTANTIVE — load-aware halting

Quoting the delegate: `But I shouldn't just retry blindly hoping the load drops (it's high and sustained).`

> membudget now has a load-aware halting behavior. By default, it waits for oversubscription to abate for a moment before it will spawn anything new.

⚑ **The operator states a membudget capability the delegate did not know about.** This is the same
information-flow the census later diagnosed as fragmentation — visible here as a single fact the
operator has to hand-carry.

---

### Q5 — 2026-08-27T12:21:18Z · queued_command · SUBSTANTIVE — the concurrency ceiling

> substrate doesn't know it, but it's already throttling if it's routing through membudget; membudget limits to 10 concurrent.

⚑ *"substrate doesn't know it"* — the operator naming the fragmentation directly, nine days early,
in the form of one repo being unaware of a constraint it is already subject to.

---

### Q6 — 2026-08-27T12:50:28Z · queued_command · ⚑ THE PGBOUNCER ANTECEDENT

⚑ This is the consult `CLAUDE.md` and the peer-relay ledgers point at as the seed of the arc, and
**it is where "I don't want to trust client-side throttling" is actually said in the operator's own
words.** Every prior record of this phrase is a peer *relay*. It is also the directive that first
recruits `linux-sources` onto the question.

> So, on the topic of postgress. I want to know what my options are for connection pooling. Is there a pgproxy which can hold inbound connections and only admit a limited number of concurrent connections through? That way I don't have to trust client-side throttling. Recruit linux-sources for the question, since linux-sources is empowered to retrieve documentation and source code for its researching.

⚑ **The admission-gate shape is already fully formed here**: hold inbound work, admit a bounded
number, don't trust the client to self-limit. That is the lock-out/tag-out reframing of 16:32 on
09-05 (`C11`/`A10`), stated nine days earlier about database connections instead of agents.

---

### Q7 — 2026-08-29T22:16:35Z · content-array · ⚑ THE GENERICIZE ORDER — `resource-lease` IS BORN HERE

Three blocks of the delegate's own prose, each answered separately. **The middle answer is the
directive that created the artifact cassian's entire census position is built around**, and it is
quoted in none of the four findings files:

> ```
> pass/fail/FAILS accumulators — mutated by side-effect in every assert_*/red helper. A forked child's increments never reach the parent (the subshell hazard the file itself documents). Must be collected-and-summed per fork.
> ```
> This is what we'd use jsonl in the output to feed back to the parent, isn't it?
>
> ```
> Fixed localhost ports in T39 (19428/9), T44 (19432/3/4), T45 (18500/1), T47 (19636) — concurrent forks collide on ports.
> ```
> Neat! Means you need to genericize the memory lease logic for resource-lease.
>
> ```
> Real-tree writes: T34 writes $REPO/host/oomd/… and restores; T34/T35 run scripts/prepare generating into $REPO/ansible/ then grep it there. Concurrent forks race the real repo — this is a corruption hazard, not just a test flake.
> ```
> Should happen in temporary worktrees, shouldn't it?

⚑ **Read what the trigger actually was: PORT COLLISION between concurrent forks.** Not memory, not
CPU — *two workers wanting the same exclusive name*. The pool-of-N-interchangeable-members shape
that substrate and cassian spent the third order reconciling was created, in one sentence, as a
response to a port conflict. **The exclusion axis was the origin of `resource-lease`, not a later
reframing of it** — which is a direct, quotable answer to the census's central question of whether
all four delegates audited the wrong axis.

---

### Q8 — 2026-08-30T01:14:00Z · queued_command

Quoting the delegate: `the parallel pool can cause cputimeout leaks if a worker is killed mid-run (e.g. by the outer timeout, or if the pool is interrupted).`

> iff membudget's gc semantics are not captured properly.

---

### Q9 — 2026-08-30T01:15:55Z · queued_command · ⚑ THE RULING `cassian-observability.md` CITES

⚑ `cassian-observability.md` §Bias-disclosure refers to *"operator ruling 2026-08-29: cputimeout was
re-deriving pid-liveness + orphan-gc that resource-lease already generalizes — the reclamation lives
there, cputimeout is a consumer."* **That is a paraphrase recorded in a docstring. Here is the
ruling itself**, and the transcript stamp is 2026-08-30T01:15Z — 2026-08-29 in local time, which is
why the filing dates it a day earlier:

Quoting the delegate: `This is the membudget RAII-by-liveness pattern, now in cputimeout.`

> I thought we _generalized_ the leasing mechanism, though? The RAII-by-liveness needs to be _there_.

⚑ **The whole ruling is a question**, and it is the same question as Q2 and Q9's kickoff: *why is
this being re-derived instead of shared?* The filing's one load-bearing operator citation, restored
to its actual wording.

---

## B. The census day and after — deltas against the existing file

The 09-05 15:05→17:23 arc is already recorded in
`OPERATOR-DIRECTIVES-cassian-observability.md` §A (C1–C15) and I confirm it **verbatim and
in full** — every one of its fifteen quotations matched my independent extraction byte-for-byte.
I add only what it does not carry:

### Q10 — 2026-09-05T15:19:16Z · content-array · the canonical-set framing

> What we _should_ be able to do is make our authored hooks part of the canonical set provided by the mtool components.
>
> Each tool gets its own mikemol-<name>
>
> Go ahead and start the clean-under-tropical-max audit of cassian's candidate components.
>
> The plan is emergent and tropical.

### Q11 — 2026-09-05T15:25:15Z · content-array · the write mandate

Quoting the delegate: `" I am not — I have read mtools (README, pyproject, venv) and run its linters against cassian's files, but I have made zero writes to mtools.`

> I do expect you to write to mtools. And to coordinate with the other repos in doing so.

### Q12 — 2026-09-05T23:35:52Z · content-array · after the arc closes

> linux-sources has much to report about bazel configuration and integrity. Ask them.

### Q13 — 2026-09-06T01:45:07Z · queued_command · ⚑ THE DIRECTIVE THAT ORDERED THE CENSUS FILES

> I'd like you to dispatch a research agent to collect all of the requests I've made of you regarding the membudget research that ultimately landed in mtools' findings directory.

### Q14 — 2026-09-06T01:54:46Z · queued_command · where they go

> I don't know who wrote /home/mikemol/github/mtools/findings/membudget/OPERATOR-DIRECTIVES.md ... but you should put your findings next to it.

⚑ **Q13/Q14 are why two of these files now exist**, and they explain the near-collision: the same
directive was issued to more than one delegate, and both filed. Recorded so a later reader does not
read the duplication as an accident.

⚑ **The path inside Q14 is left exactly as the operator typed it, and it no longer resolves.** That
file was renamed to `OPERATOR-DIRECTIVES-linux-sources.md` on 2026-09-06 so every census in this
directory is attributable by filename. **A verbatim quotation is not updated when the world moves** —
rewriting the operator's words to keep a link live would falsify the citation, which is the failure
this whole file set exists to prevent. The note carries the correction; the quote carries the record.

---

## C. Peer messages that relayed operator words — **peer, not operator**

All `cross-session-message` wrapped. A peer relay is evidence an operator directive exists; it is
not that directive.

| # | when | from | the relayed operator words |
|---|---|---|---|
| P1 | 09-05T16:02:30Z | `substrate-9b` | **"WITHDRAW THE mat260 GAP — my operator says mat260 is retired too."** The mirror of `C3` (*"mat230 repo is retired"*), issued to substrate about a different repo — so the retirement ruling was **broadcast**, not cassian-local, and `C3`'s "no counterpart" note is true of the text but not of the act. |
| P2 | 09-05T16:28:05Z | `paperkit-7c` | *"Your §3 withdrawal — accepted, and it converges with the operator's own correction … The operator told me the same thing in…"* — an operator correction issued in **paperkit's** session. |
| P3 | 09-05T16:57:16Z | `paperkit-7c` | *"Converged — I got the operator's correction directly and had reached the same reading before your message arrived"*, and *"The operator has corrected me three times on that principle already."* **The paperkit-side counterpart of `C13` (pushout-not-pullback).** |
| P4 | 09-05T17:32:16Z | `mtools-05` | **"Operator ruling: mtools takes the STRICTEST UNION of all peer repos' linting + hooks (Claude and git) — per axis, max, converging on something at worst stricter than anything any of you need."** Issued in **mtools'** session. |

⚑ **P2, P3 and P4 are directives no cassian-side census can show.** They were typed into paperkit's
and mtools' sessions and reach this corpus only second-hand. Per the restore-is-a-second-hand-source
rule they are **testimony, not citation**, and are not promoted into §A or §B.

⚑ **P3 answers a question `C15`/§D4 left open.** That file flagged the ~6-minute gap between
cassian's and linux-sources' consolidating directive, quoting identical delegate prose, as
*"unresolved from this vantage — either two delegates independently produced the same paragraph, or
one was relayed."* The relay traffic here shows the operator **repeatedly quoting one delegate's
prose into another's session** (P2, P3 explicitly). The relay hypothesis has direct support; the
independent-production one has none. Not proof — the paperkit and substrate transcripts would settle
it — but the two branches are no longer symmetric.

---

## D. ⚑ THE SECOND DIRECTORY — a searched negative

Two project directories exist for this repo. Every existing census reads one file in one of them.

**`-home-mikemol-github-cassian-obs/` — 1 file, `80c2257d-5190-48bd-b1fc-628fb4e7550d.jsonl`,
13,936,180 bytes, 4,684 lines, 859 user-role messages, 40 `queued_command` records, 33 of them
`origin.kind: human`, 0 unparseable. Searched end to end.**

⚑ **It contributes ZERO membudget directives.** It is a **2026-07-27-era session** — its human-origin
queued commands predate the census by six weeks, and its only term hit is a subagent's
cotype/realizability report that mentions substrate in passing.

**This is worth stating as a measured negative rather than left unsearched**, because the two
spellings look like two halves of one corpus and are not. A later reader who notices the second
directory and assumes the censuses missed half the evidence can stop: it was read, and it is empty
of this subject. ⚑ *An absence that has been measured is a different artefact from an absence
nobody looked for* — and only the first one closes the question.

The other two files in the main directory (`793f4564…`, 3,003 lines; `a0bb2b40…`, 524 lines) were
likewise searched in full and carry no census directive.

---

## E. Coverage

**Population, both directories, every file, end to end.**

### E1 — `~/.claude/projects/-home-mikemol-github-cassian-observability/` — **4 files**

| file | bytes | lines | user-role | `queued_command` | of those, human | unparseable |
|---|---|---|---|---|---|---|
| `793f4564-1ed1-4d42-a616-54526123df53.jsonl` | 6,296,670 | 3,003 | 594 | 11 | 10 | 0 |
| `8bf50905-e836-445b-b9a1-447167c8497b.jsonl` | 12,676,925 | 4,851 | 907 | 59 | 6 | **1** |
| `a0bb2b40-a81f-40b4-af9b-8adb1881168c.jsonl` | 920,977 | 524 | 106 | 3 | 0 | 0 |
| `d90455f2-481f-4cd6-a1d1-1eee8fdfefb4.jsonl` | 377,635,593 | 141,746 | 25,928 | 1,274 | 477 | **10** |
| **total** | **397,530,165** | **150,124** | **27,535** | **1,347** | **493** | **11** |

### E2 — `~/.claude/projects/-home-mikemol-github-cassian-obs/` — **1 file**

| file | bytes | lines | user-role | `queued_command` | of those, human | unparseable |
|---|---|---|---|---|---|---|
| `80c2257d-5190-48bd-b1fc-628fb4e7550d.jsonl` | 13,936,180 | 4,684 | 859 | 40 | 33 | 0 |

### E3 — combined

**5 files · 411,466,345 bytes · 154,808 lines · 28,394 user-role messages · 1,387 `queued_command`
records, 526 of them `origin.kind: human` · 11 unparseable lines.**

⚑ **Independent corroboration of the sibling file's numbers.** It reports 1,272 `queued_command` /
476 human and 10 bad lines for `d90455f2…`; I measure **1,274 / 477 / 10** on the same file. The
two-record delta is a counting-rule difference (I also count a record whose top-level `type` is
`queued_command`), not a disagreement about content. **The bad-line count agrees exactly**, which is
the figure that bounds what either census could have missed.

### E4 — three passes, all five files

1. **Population census** — every line parsed and classified by shape. Numbers above.
2. **Human-authored extraction** — every `queued_command` with `origin.kind == "human"`, plus every
   `message.role == "user"` record **whose content array carries no `tool_result` block**. That last
   filter is the load-bearing one: without it the candidate set is 1,700 records of which **1,282
   are tool output wearing the user role**. Result: **3,096 human-shaped records — 2,665 operator,
   377 peer, 54 harness.**
3. **Unfiltered census-day dump** — all **64** operator records on 2026-09-05 read in full, *not*
   term-filtered, which is what makes the day a population rather than a sample; plus a
   term-filtered sweep of **every other day** (34 hits), which is what recovered §A.

### E5 — ⚑ What is NOT covered

- ⚑ **11 of 154,808 lines failed JSON parse and were skipped, unrecovered.** If any carried an
  operator message it is missing here. No claim is made that they did not.
- ⚑ **Tool-call interiors were excluded by construction, not searched.** Operator words quoted
  inside a subagent brief or a `tool_use` input would not surface. **This is the weakest edge**, and
  it is the *same* edge the two sibling censuses named. ⚑ Three independent sweeps sharing one blind
  spot is **not** three confirmations — it is one unexamined region measured three times.
- ⚑ **AskUserQuestion: checked, not assumed.** 12 lines on the census day mention `AskUserQuestion`;
  **none is a standalone answer record.** The single answer-shaped artefact (15:05) carries its
  questions and answers **inlined in one operator message** and is quoted whole in the sibling file's
  §B. No answer was lost to that shape.
- ⚑ **Sidechain records: 0.** No directive was hiding in a subagent's own transcript stream.
- ⚑ **Cassian's two directories only.** substrate's, paperkit's and mtools' transcripts were not
  searched. §C P2/P3/P4 prove directives exist there that no cassian-side census can quote —
  **UNAVAILABLE, not absent.**
- **The 09-05 arc here is a confirmation, not a re-derivation of record.**
  `OPERATOR-DIRECTIVES-cassian-observability.md` is the primary citation for C1–C15; this file's
  original contribution is §A (the antecedents), §C (the relay ledger), and §D (the second
  directory).

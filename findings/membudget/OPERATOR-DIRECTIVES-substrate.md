# Operator directives — the membudget census, as SUBSTRATE received them

**What this is.** The fourth companion to `OPERATOR-DIRECTIVES.md` (linux-sources) and
`OPERATOR-DIRECTIVES-paperkit.md` / `OPERATOR-DIRECTIVES-cassian-observability.md`. Same census,
swept from **substrate's** transcript. Verbatim, in turn order, no paraphrase.

⚑⚑ **SUBSTRATE'S RECORD IS THE ODD ONE OUT, AND THE DIVERGENCE IS THE FINDING.** The peer files
document a *timestamp* divergence — four delegates hold four receipt times for one broadcast. This
file documents something larger: **substrate did not receive the same directive set at all.**

| directive | linux-sources | paperkit | substrate |
|---|---|---|---|
| kickoff | A-series | P1 | **S8 — DIFFERENT TEXT** (names only cassian-observability, not all four) |
| first-order filing order | present | P2 | ⚑ **ABSENT** — no entry for that spelling |
| second-order (dispatch) | present | P3 | S9 |
| second-order (all four) | present | P5 | S10 |
| the CPU-vs-memory axis history | present | P6 | ⚑ **ABSENT in the census window** (but see S1–S7, pre-census) |
| the shared host | present | P7 | S11 |
| the shared BES / `--config=remote` | present | P8 | ⚑ **ABSENT** |
| the lock-out/tag-out reframing | present | P9 | S12 |
| third-order order | present | P10 | S13 |
| **"I said pushout, damnit, not pullback"** | present | P11 | ⚑⚑ **ABSENT** |
| third-order re-issue | present | P12 | S14 |
| "Audit your rewrites…" | present | P13 | ⚑ **ABSENT** |
| consolidation ("hold the results") | present | P14 | S15 |
| naming (`<repo>-consolidated.md`) | present | P15 | ⚑ **ABSENT** |

**Substrate's census window holds 8 directives (S8–S15) against paperkit's 15.** Five of the seven
missing are messages the peer files treat as load-bearing — including the construction correction
that inverted every arrow in the third-order filings.

⚑ **This is not a claim that the operator did not send them.** It is a claim about substrate's
transcript: they are not in it. Substrate's third-order and consolidated filings were written
**without ever receiving the pushout/pullback correction, the audit order, or the naming
correction** — which means any pushout-correct content in `substrate-third-order.md` arrived by
peer relay or by substrate reading the other filings, not by operator instruction.

---

## Predicate and coverage

**Instrument:** `scratch/transcriptstruct.py` — the only reader of these files. Never grep: the
text lives inside JSON-escaped strings, so a line-regex matches the encoded form and returns a byte
offset inside a 300 MB line, with no role and no turn index.

**The whole corpus was swept — all seven files, ~1.48 GB.** Denominators carried from the tool:

```
ec9fd63f-…jsonl   257,762,723 B   94,724 envelopes   1,255 carry human prose   <- THE CENSUS SESSION
d35bc15a-…jsonl 1,189,383,587 B  218,475 envelopes                             <- membudget ENGINEERING
1749aed8-…jsonl    22,273,929 B   11,066 envelopes   0 matches
889539fc-…jsonl     4,832,750 B    2,789 envelopes   0 matches
58f4b67d-…jsonl     2,451,002 B    1,363 envelopes   0 matches
6b9ad29e-…jsonl     1,641,451 B      700 envelopes   0 matches
28df5f75-…jsonl     1,633,836 B      796 envelopes   0 matches
```

**Search vocabulary** (`--human --grep-content`, alternation, per file):
`membudget` · `pushout|pullback|lock-out|tag-out|BES|config=remote|mat260|mat230|designed to swap|retired|swap`
· `PSI|CPU|zram|zswap|primary constraint|physical host|first-order|second-order|third-order|consolidat|Audit your`
· `exhaustive findings|write your|into the mtools|findings into` · `MemAvailable|headroom|this host|this box`.

Bounded negatives, each with its denominator:

```
'membudget|mtools/findings|pushout|second-order'  ->  0 of 11,066   (1749aed8)
                                                      0 of  2,789   (889539fc)
                                                      0 of  1,363   (58f4b67d)
                                                      0 of    796   (28df5f75)
                                                      0 of    700   (6b9ad29e)
'membudget|pushout|mtools/findings|…'             -> 38 of 218,475  (d35bc15a — engineering, NO
                                                      `mtools/findings` hit: this session predates
                                                      the census by two weeks and closed Aug 22)
'exhaustive findings|write your|into the mtools'  ->  2 of 94,724   (ec9fd63f — neither is the
                                                      first-order filing order)
'queued_command'                                  ->  2 of 94,724   (both from reading the PEER
                                                      file during THIS dispatch)
'pushout|pullback'                                -> 15 of 94,724   (ec9fd63f — every one is S13,
                                                      S14, S15, or an unrelated Agda item)
'BES|config=remote'                               ->  0            (all seven files, human turns)
'Audit your'                                      ->  0            (all seven files, human turns)
'mat2'                                            ->  0            (all seven files, human turns)
'designed to swap'                                ->  0            (all seven files, human turns)
```

⚑ **The `queued_command` blind spot the peer files document does NOT apply here, and I checked
rather than assumed.** Paperkit's sweep missed 118 human turns delivered as
`attachment.type == "queued_command"`. Substrate's transcript contains **no such record**: the two
hits are the peer file's own text, read minutes ago. Substrate's interjections arrived as ordinary
`type: user` envelopes. **This was verified, not inferred** — a negative about a record type is
exactly the shape that got the peer sweep wrong.

⚑ **What the search could NOT see, stated as method-facts rather than substrate-facts:**

1. **`--prose` does not decode `attachment` envelopes.** `--prose --role attachment` returns
   `0 of 94,724`, and `--messages --role attachment` reports every one of the 17,629 attachments as
   `0B`. That zero is a fact about the reader. It is harmless *here* only because the independent
   `--grep-content "queued_command"` sweep (which streams raw) also found nothing.
2. **⚑⚑ THE INSTRUMENT EXPOSES NO TIMESTAMP MODE — READ THIS BEFORE COMPARING SUBSTRATE'S ROWS TO
   THE THREE PEERS'.** No mode of `transcriptstruct.py` prints a timestamp. `--timestamps` is
   **silently accepted and ignored**: passing it returns the same rows, with no timestamp column
   and exit 0 — no error, no warning, nothing that would tell a caller the flag did nothing.
   **So this file cannot give UTC times, and every entry below says "timestamp unavailable" rather
   than inventing one.** Ordering is by **turn index**, which is monotone in time within a session
   and is the citation a reader can `--extract`. The three peer files order by UTC receipt time;
   substrate's rows are therefore **orderable within this file and not across files** — a reader
   merging the four cannot interleave substrate's entries with the peers' on time. This is a
   missing mode — i.e. WORK, not a finding — and it is the single largest gap between this file
   and its three peers.
3. Anything the operator said outside a Claude session, or in another repo's session.

---

## The directives, verbatim

⚑ Numbering is `S<n>` in turn order. **S1–S7 are PRE-CENSUS** — membudget doctrine uttered weeks
before the survey, included because substrate's filings quote these claims and no census-window
utterance sources them. They are marked UNCERTAIN per the brief's over-inclusion rule.

### S1 — timestamp unavailable · `user message` · d35bc15a turn 21570 · SUBSTANTIVE, UNCERTAIN

> Before you blame anything on swap, take a look at my zmem and zswap setup.

**CORRECTION.** The first half of the "this host is designed to swap" reframing. ⚑ The exact phrase
"this host is designed to swap" appears nowhere in substrate's corpus — `0` human hits for
`designed to swap` across all seven files. S1 and S3 are what substrate actually received.

### S2 — timestamp unavailable · `user message` · d35bc15a turn 21633 · SUBSTANTIVE, UNCERTAIN

> It did eventually overwhelm zswap.

**CONTEXT.** Delivered with a screenshot (the envelope carries an `image` block). Qualifies S1: the
protection is real but not unbounded.

### S3 — timestamp unavailable · `user message` · d35bc15a turn 74852 · SUBSTANTIVE, UNCERTAIN

> This machine is protected with zswp. Swap presence is normal. Pay attention to PSI instead.

**CORRECTION.** ⚑ The load-bearing one. Swap presence is NOT a fault signal on this host; PSI is
the signal. Typo `zswp` preserved. This is substrate's version of the peer files' "designed to
swap".

### S4 — timestamp unavailable · `user message` · d35bc15a turn 22219 · SUBSTANTIVE, UNCERTAIN

> `Journal isn't capturing the child stderr. Memory is confirmed bounded (1.1 G), so it's safe to run directly (no membudget) to surface the traceback:`
>
> Safe until it isn't. Stay in the habit of memory binding. Troubleshoot and fix the reason for the loss of error data; I don't recall having this problem with agda.

**CORRECTION.** Rejected the delegate's "bounded, so safe to skip membudget" reasoning. **Memory
binding is a HABIT, not a case-by-case judgement** — the doctrine substrate's filings restate as
"membudget is unconditional".

### S5 — timestamp unavailable · `user message` · ec9fd63f turn 34010 · SUBSTANTIVE, UNCERTAIN

> membudget does two things. It limits concurrency on a memory ceiling, and it limits concurrency on a load average ceiling. The latter was added because enough concurrency thrown at the postgres backend _caused kernel hangs_. This isn't recorded in the source. It _was_ in the makefile generator. The makefile generator probaby got rewritten by an agent and lost the membudget lines protecting the db ingestions.

**CONTEXT.** ⚑⚑ **THE SECOND AXIS AND ITS ORIGIN, IN ONE MESSAGE** — and the closest thing
substrate received to the peer files' P6 CPU-vs-memory axis history. Also the provenance of the
regression substrate's filings report: the load-average lines existed in the generator and **an
agent rewrite dropped them**. Typo `probaby` preserved.

### S6 — timestamp unavailable · `user message` · ec9fd63f turn 24505 · SUBSTANTIVE, UNCERTAIN

> `Nothing. So membudget is the only exclusion mechanism in the tree, and it's the wrong axis. This is genuinely missing.` membudget has a cpu axis, too. If you want membudget to wrap flock, well, that's a thing, I guess?

**CORRECTION.** Refuted "wrong axis" — the CPU axis already exists. ⚑ The `flock` aside is the
earliest appearance of the exclusion-primitive question that the census's lock-out/tag-out
reframing (S12) later made central.

### S7 — timestamp unavailable · `user message` · ec9fd63f turn 21065 · SUBSTANTIVE, UNCERTAIN

> I wish I had a tool like membudget which would sleep until load average dropped below a target. I know Gentoo's `emerge` can do that, but `make` doesn't, so...yeah.

**CONTEXT.** The feature-wish that produced the load throttle. Paired with turn 24821 —
*"Ok. What if membudget had `sleep` builtin?"* — and turn 47089 — *"Take a look at what membudget
does. membudget has a built-in load-aware throttle."*

---

⚑ **THE CENSUS WINDOW BEGINS HERE.** Everything below is ec9fd63f, turns 91065–92481.

### S8 — timestamp unavailable · `user message` · ec9fd63f turn 91065 · KICKOFF

> Before you get back to mtools, dispatch a research agent to study membudget _in depth_. It's more than just memory and CPU. Also see how cassian-observability is using the machinery. It's genericized. Or it's supposed to be. Ic an't tell how many times I've told all of you to improve on and genericize that machinery, and had you _not share the improvements back, or decide you didn't need the whole of the thing_. So it might be fragmented.

**DIRECTIVE.** ⚑⚑ **NOT THE SAME KICKOFF THE PEERS RECEIVED.** Paperkit's P1 reads *"Also see how
substrate, paperkit, linux-sources and cassian are using the machinery"*; substrate's names **only
cassian-observability**. Also *"Before you get back to mtools"* — substrate was mid-arc on the
mtools migration, so the census was an interrupt here and a fresh task elsewhere. Typos `Ic an't`
preserved. Everything else (fragmentation expected, cause = delegates not sharing back) matches.

### S8′ — the first-order filing order · ⚑ **NO ENTRY FOR THAT SPELLING**

Paperkit's P2 — *"I want you, linux-sources, substrate, and cassian-observability to write your
exhaustive findings re membudget into the mtools repo"* — **is not in substrate's transcript.**
`'exhaustive findings|write your|into the mtools|findings into'` returns `2 of 94,724` human
turns, and neither is it (one is turn 90572, *"(you will be coordinating with linux-sources) on the
migration of things into the mtools repo"*; the other is S10).

⚑ **So how does `substrate.md` exist?** The transcript answers it. At turn 91385 substrate sent a
**peer message to mtools**, not to the operator, asking permission:

> Convention as I understand it (set by linux-sources, adopted by cassian): `findings/membudget/<repo>.md`, one file per author, bias disclosed in the first paragraph, quotes rather than line-number citations. Mine would be `findings/membudget/substrate.md`. **Say if you want a different path or shape and I'll conform.**

and filed at turn 91456 without waiting for an operator order. The standing authorisation was two
turns of general grant — turn 90898 *"What do you need from me?"* and turn 90988 **"Yes, you are a
writer to mtools"** — plus the peer-established convention. **`substrate.md` was self-authorised
off a peer convention, not ordered.**

### S9 — timestamp unavailable · `user message` · ec9fd63f turn 91466 · SECOND-ORDER ORDER

> Time for a second-order report. Dispatch a research agent to read through all of the findings in /home/mikemol/github/mtools/findings/membudget and reconcile with your own.

**DIRECTIVE.** Byte-identical to paperkit's P3.

### S10 — timestamp unavailable · `user message` · ec9fd63f turn 91631 · SECOND-ORDER, ALL FOUR

> I want cassian-observability, linux-sources, substrate and paperkit to all write their _second-order_ findings into the mtools repository, as files distinct from their first-order findings.

**DIRECTIVE.** Byte-identical to paperkit's P5. ⚑ **This is the FIRST message in substrate's
transcript that names substrate as a filer** — after `substrate.md` had already been written.

### S11 — timestamp unavailable · `user message` · ec9fd63f turn 91809 · SUBSTANTIVE — the shared host

> It's also worth pointing out that, to date, _all of the consumers of membudget run on the same physical host_. They all face the same environmental constraints, so any idea of "what does my load need" is ignorant of the dynamics of the environment in which they run.

**CONTEXT.** ⚑ The census's central premise, byte-identical to P7. Arrived here as a plain
`user message`, **not** a `queued_command` as it did at paperkit. A paperkit dispatch reported this
message as not existing; in substrate's corpus it is unambiguously present at turn 91809.

### S11′ — the shared BES / `--config=remote` remedy · ⚑ **NO ENTRY FOR THAT SPELLING**

Paperkit's P8 (*"this is why I'm pushing evveryone to use the same BES/--config=remote target"*) is
absent. `'BES|config=remote'` returns `0` human hits across all seven files. **Substrate never
received the remedy that follows from S11.**

### S12 — timestamp unavailable · `user message` · ec9fd63f turn 91992 · THE REFRAMING

> `What stays irreducibly lease-shaped is work outside the build graph ` Actually, the whole reason I told to collect information about membudget is because the lease-shape phenomenon generalizes very well to "multiple agents modifying the same tree, communicating to prevent each other from stepping on each other". Granular lock-out/tag-out.

**CORRECTION.** ⚑⚑ Byte-identical to P9, and the one census-window correction substrate *did*
receive. Reset the subject: the resource axis is one instance of a lock-out/tag-out mechanism.
Retroactively superseded the reading under which `substrate.md` and
`substrate-second-order.md` were written. ⚑ Note it quotes substrate's own prose back — this is a
reply to a substrate turn, so it is genuinely addressed here rather than broadcast.

### S13 — timestamp unavailable · `user message` · ec9fd63f turn 92141 · THIRD-ORDER ORDER

> Ok, I want you, cassian-observability, linux-sources and paperkit to file your third-order findings in /home/mikemol/github/mtools/findings/membudget. We're looking to evolve a common understanding of the capabilities of the tool and establish what a pushout looks like, so that all parties can cooperatively land their requirements into the commonly-managed tool, and so that all parties can cooperatively avoid stepping on each other at a fine-grained level.

**DIRECTIVE.** Byte-identical to P10. ⚑ Note the addressee list — *"you, cassian-observability,
linux-sources and paperkit"* — is the same four-way list the peers received with their own name
substituted for "you", so the broadcast reached substrate intact here.

### S13′ — "I said pushout, damnit, not pullback" · ⚑⚑ **NO ENTRY FOR THAT SPELLING**

Paperkit's P11 **is not in substrate's transcript.** `'pushout|pullback'` returns `15 of 94,724`
human turns in the census session; every one is either S13, S14, S15 or an unrelated Agda
`⟡rig-UP-wreath, Ⓐ auto-pushout` item in the other session. **The word `pullback` never appears in
a human turn in substrate's corpus at all.**

⚑ **This is the sharpest divergence in the file.** The peer files call this the correction that
"inverted every arrow" and identify it as the reason the third-order filings were rewritten.
Substrate wrote `substrate-third-order.md` **never having been told it had computed a limit.**
Whatever pushout-correctness that file has came from substrate reading the peers' filings under
S9's reconcile-with-all instruction — a mechanism, not an instruction.

### S14 — timestamp unavailable · `user message` · ec9fd63f turn 92308 · THIRD-ORDER RE-ISSUE

> Ok, I want you, cassian-observability, linux-sources and paperkit to file your third-order findings in /home/mikemol/github/mtools/findings/membudget. We're looking to evolve a common understanding of the capabilities of the tool and establish what a pushout looks like, so that all parties can cooperatively land their requirements into the commonly-managed tool, and so that all parties can cooperatively avoid stepping on each other at a fine-grained level.

**DIRECTIVE.** Byte-identical to S13, 167 turns later. ⚑⚑ **At paperkit this re-issue is legible
as "after the correction" — the correction sits between P10 and P12 and the repeat is what makes
it visible. In substrate's transcript there is nothing between S13 and S14 but substrate's own
work.** The re-issue arrives here as an unexplained verbatim repeat. **A delegate reading only its
own transcript cannot recover why it was re-issued** — which is precisely the failure mode this
file exists to fix.

### S14′ — "Audit your rewrites…" · ⚑ **NO ENTRY FOR THAT SPELLING**

Paperkit's P13 (*"Audit your rewrites and finding documents for consistency, correctness and
convergence."*) is absent. `'Audit your'` returns `0` human hits across all seven files.

### S15 — timestamp unavailable · `user message` · ec9fd63f turn 92481 · CONSOLIDATION

> `That gap is real but correct as-is — the second-order document predates the pushout directive entirely. It shouldn't carry a correction to a construction it never attempted; that would be backfilling history. The right fix is a forward pointer, not a retrofit.`
>
> The fix is a fourth document _consolidating; we don't want to hold the retractions, we want to hold the results.

**CORRECTION.** ⚑ A REVERSAL, byte-identical to P14 including the unclosed `_` before
"consolidating". Substrate had argued for a forward pointer and against backfilling history;
overridden. **`substrate-consolidated.md` exists because that argument was rejected.**

⚑⚑ **And the quoted prose is SUBSTRATE'S OWN** — substrate made the forward-pointer argument that
all four delegates were then overruled on. Substrate is the origin of the position the
consolidation directive reverses.

### S15′ — the naming correction · ⚑ **NO ENTRY FOR THAT SPELLING**

Paperkit's P15 (*"I think your CONSOLIDATED.md needs to be paperkit-consolidated.md; everyone
else's is <repo>-consolidated.md."*) is absent. Substrate named its file
`substrate-consolidated.md` correctly on the first attempt and so was never corrected — consistent
with the peer file's account that paperkit alone diverged.

---

## The closing directive — the order that produced this file

### S16 — timestamp unavailable · `user message` · ec9fd63f turn 94707 · THE SURVEY ORDER

> I'd like you to dispatch a research agent to collect all of the requests I've made of you regarding the membudget research that ultimately landed in mtools' findings directory.
>
> Full verbatim list written to a file, please.
>
> I don't know who wrote /home/mikemol/github/mtools/findings/membudget/OPERATOR-DIRECTIVES.md ... but you should put your findings next to it.
>
> I have three repos consolidating their instructions. I want to kick off a similarily-shaped survey, but I need to know what I told everyone for that initial survey.

**DIRECTIVE.** The order this file answers. Typo `similarily` preserved. ⚑ *"I don't know who wrote
OPERATOR-DIRECTIVES.md"* — the operator could not attribute their own census's compilation, which
is itself the strongest argument for the per-repo suffix convention these four files use.

---

## Also in scope, uncertain

### S17 — timestamp unavailable · `user message` · ec9fd63f turn 52896 · UNCERTAIN

> ```
> Note the header: paperkit retired its membudget semaphore and BUILD projector because Bazel owns scheduling, caching, resource limits and the sandbox. That's directly the argument for mtools.
>
> Reading the pieces mtools actually needs — the Python test wiring and the config:
> ```
>
> No, _study how paperkit uses bazel_. Don't just grab the pieces you think you need. There's a reason I'm calling out paperkit's bazel implementation.

**CORRECTION, UNCERTAIN.** Pre-census. ⚑ **The nearest thing substrate received to a retirement
notice**, and it is a relay of paperkit's header rather than an operator statement of fact. The
brief asks about *mat260 retired / mat230 retired*: `'mat2'` returns **`0` human hits** across all
seven transcripts. **No entry for that spelling.** Substrate's filings discuss mat260 (the ceiling
report, the foreclosed-consumer finding) — sourced from the code and from peer relay, **not from an
operator directive in substrate's transcript.**

### S18 — timestamp unavailable · `user message` · ec9fd63f turn 94485 · UNCERTAIN

> substrate's clean code moves to mtools, because this lets mtools publish substrate's clean code _as packages_, which in turn lets _everyone express proper python dependencies instead of symlinks and copy vendoring_; once mtools actually _has_ the code, I can expose it on github, even before it's exposed on pypy. So, _yes_, substrate's clean code moves to mtools.

**DIRECTIVE, UNCERTAIN.** Post-census, but it settles the interning question the third-order
filings were arguing about — and it is the operator ruling that substrate's filings say was
outstanding. Typo `pypy` (for PyPI) preserved.

---

## What the record shows that the filings do not

⚑⚑⚑ **THE HEADLINE: A BROADCAST IS NOT A BROADCAST.** The peer files established that four
delegates hold four *timestamps* for one event. Substrate's record establishes something stronger
and worse: **the four delegates did not receive the same events.** Seven directives the peers
record are absent here, including the construction correction, the audit order, and the first-order
filing order that created the base filings.

**The mechanism is visible in the kickoff.** S8 and P1 are *different text* — P1 enumerates all
four repos, S8 names one. These were typed separately, not fanned out. **A "broadcast" in this
harness is the operator re-typing an instruction per delegate, and re-typing drifts.** That is the
generative cause of every row in the divergence table, and it is not visible from inside any one
transcript.

⚑⚑ **THREE CONSEQUENCES THE FILINGS CANNOT SHOW:**

1. **`substrate.md` was never ordered.** It was self-authorised off *"Yes, you are a writer to
   mtools"* plus a peer-established convention, with substrate asking **mtools** (turn 91385) for
   placement rather than the operator. The base filing that anchors the whole census has no
   directive behind it in this transcript. **A convention propagated peer-to-peer did the work an
   instruction is assumed to have done** — which is, verbatim, the thesis of the census it produced.

2. **Substrate's third-order filing was written blind to the correction that motivated it.** No
   pushout/pullback correction reached substrate, yet S14 re-issued the third-order order verbatim
   167 turns after S13. **From inside substrate's transcript the re-issue is inexplicable.** Any
   correctness in `substrate-third-order.md` on this axis came through S9's *reconcile with all the
   findings* — i.e. **the shared directory acted as the repair channel for a missing directive.**
   That is a live instance of the census's own claim that a shared artifact carries what an edit
   cannot.

3. **Substrate authored the position the consolidation directive overrules.** The prose the
   operator quotes back in S15 — *"the right fix is a forward pointer, not a retrofit"* — is
   substrate's. The `-consolidated.md` files across all four repos exist because **substrate's**
   argument was rejected. The filings record the outcome; only the transcript records whose
   argument it was.

⚑ **A fourth, about this file's own limits.** Three peer files give UTC timestamps; this one gives
none, because `transcriptstruct.py` has no mode that prints them and `--timestamps` is silently
accepted and ignored. **That is a missing mode — work, not a finding** — and it is the one thing
that would let a reader merge these four files into a single send-ordered account. Until it exists,
the divergence table above is orderable per-column and not across columns.

⚑ **And a fifth, about the shape of the ask.** Substrate's census window is **8 directives across
~1,400 turns** — under 1,500 characters of operator prose. It produced four filings totalling
~137 KB. **The asks are thin, the outputs are thick, and two of the thickest documents answer
instructions substrate never received.**

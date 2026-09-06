# The Bazel progress denominator in paperkit — what `[done / N]` actually is

**Repo:** paperkit · **Bazel:** 8.7.0 (MEASURED — `bazel version` → `Build label: 8.7.0`, run in
background so as not to contend for the server lock) · **Date:** 2026-09-06 · Companion to
`paperkit.md`, `mtools.md`.

Every number below was extracted from real run logs in this repo's scratchpad. Claims are tagged
**MEASURED** (computed from a log), **READ-FROM-SOURCE** (from Bazel's own output semantics /
help), or **INFERRED** (reasoned, not observed).

---

## 0. OPERATIONAL ANSWER — read this and stop

**`N` in `[done / N]` is a live count of action-execution work units Bazel has *enqueued so far*.
It is not a total, and there is no mid-run signal that it has stopped growing. `done/N` is
structurally useless as a completion estimate on `//:hook`.**

Four rules, all MEASURED:

1. **`N` is monotone non-decreasing** in all 5 runs measured, 0 decreases out of ~31,000 progress
   lines. So `N` is a *lower bound* on final work, and `done/N` is an *upper bound* on true
   progress — it can only ever overstate.

2. **`done/N` is a queue-occupancy ratio, not a completion ratio.** The gap `N - done` in
   `hook2-FINAL-4fail.log` has median **3,944** and range **0 … 11,499**, and it oscillates in that
   band for the entire 4-hour run without trending. It is the depth of the ready-to-run queue.
   The session's current use of the GAP is therefore reading a **queue depth**, not a remaining-work
   figure — see §5.

3. **The ONLY exact "frontier is final" signal is `done == N` with `no actions running`, which is
   the last progress line of the run.** There is no earlier one. Positive control for this absence
   in §4 — it is a claim about my query, and the query was broad.

4. **`k / 24 tests` is the least-bad in-flight signal but is wildly non-linear.** MEASURED on
   hook2: the counter sat at `11 / 24 tests` from 2.3% to 78.9% of the run's real work. It then
   went 11→24 in the last 21%. A test counter on a `test_suite` whose members have grossly unequal
   action fan-out is a *milestone marker*, not a progress bar.

**What to use instead:** `done` alone, against the previous run's final `N` for the same target set
on the same cache state. That is the only quantity in the stream that is both monotone and
denominated in a fixed unit. §5 gives the exact recipe and its failure mode.

---

## 1. WHERE the number comes from

**READ-FROM-SOURCE + MEASURED.** The line is emitted by the execution-phase progress reporter, not
by loading or analysis. Established by position in the log rather than by reading Bazel's Java:

`hook2-FINAL-4fail.log` line 177, verbatim:

    INFO: Analyzed 24 targets (100 packages loaded, 172957 targets configured).

The file is 16,086 lines long. **Analysis completed at line 177 — 1.1% of the way in.** The
`[done / N]` lines then run to line 16,082. So every progress line after 177 is emitted with the
configured-target graph already complete and frozen.

**The numerator and the denominator count the same kind of thing** (both actions / execution work
units), which is why `done` can reach `N` exactly at the end. MEASURED — hook2's final line:

    [168,915 / 168,915] 24 / 24 tests, 4 failed; no actions running

**But neither counts "actions executed."** MEASURED, and this is the sharp one:

| log | packages | targets configured | **final `N`** | `total actions` (from `Build completed`) |
|---|---|---|---|---|
| hook2-FINAL-4fail | 100 | 172,957 | **168,915** | 111,270 |
| hook3-bes | 36 | 115,729 | **114,982** | 17,918 |
| adq2 | 0 | 53,901 | **53,981** | 49,473 |
| adq | 0 | 0 | **53,981** | 47,279 |
| hook-rbe | 42 | 169,307 | **70,760** | (run truncated) |

Final `N` tracks **targets configured** closely (168,915 vs 172,957; 114,982 vs 115,729; 53,981 vs
53,901 — within 2%) and tracks **executed actions** not at all (114,982 vs 17,918 — a factor of
6.4). ⚑ In `hook3-bes.log` the frontier is **6.4× the number of actions actually executed**,
because cache hits and already-up-to-date actions are counted into both `done` and `N` while never
appearing in `total actions`.

**Consequence (INFERRED from that table):** `N` is approximately "one work unit per configured
target's action set, counted as scheduled," and `done` increments for cached and executed units
alike. So a 99%-cached run and a 0%-cached run over the same graph produce nearly the same `N` but
`total actions` differing by orders of magnitude. **`N` is not a cost estimate.** Two runs with the
same final `N` can differ 6× in wall time.

### 1a. What `bazel help build` says (READ-FROM-SOURCE, Bazel 8.7.0)

The relevant flags, verbatim from `bazel help build`:

    --progress_report_interval (an integer in 0-3600 range; default: "0")
    --[no]show_loading_progress (a boolean; default: "true")
    --[no]show_progress (a boolean; default: "true")
    --show_progress_rate_limit (a double; default: "0.2")

Two things follow.

**(a) `show_loading_progress` is a *separate* flag from `show_progress`.** Bazel distinguishes
loading-phase progress from the `[done / N]` stream at the flag level. This corroborates §1's
positional finding — the `[done / N]` line belongs to the execution reporter, not the loader —
with an independent instrument.

**(b) `--show_progress_rate_limit` default 0.2 means the log is a SUBSAMPLE**, not a complete trace.
At most one progress line is emitted per 0.2s. This matters for §2 and is addressed in §2a.

⚑ Notably absent from the flag list: any option to report a *total*, an *estimate*, or a *percentage*.
`--progress_report_interval` governs how often stalled-action reports are printed, not what is
counted. This is a second positive control for §4's absence claim, taken with a different
instrument (the flag surface rather than the log text).

---

## 2. WHEN it moves

**MEASURED on hook2** (2,607 frontier changes across 13,192 progress lines):

| jump size | count |
|---|---|
| 1–499 | 2,495 |
| 500–999 | 40 |
| 1,000–1,499 | 56 |
| 1,500–1,999 | 10 |
| 2,000–2,499 | 3 |
| 2,500–2,999 | 1 |
| 3,000–3,499 | 1 |
| 4,500+ | 1 |

**Median jump = 2. Mean = 64.8. Max = 4,523.** (Computed over *distinct* frontier values — see
§2a, which recomputes this per-emission and revises the characterisation.)

⚑ **This refutes "stepwise discovery."** If `N` grew because each project's generated BUILD was
loaded, growth would be ~11 large steps. Instead 96% of the 2,607 changes are under 500 and the
median is **2**. That is a continuous trickle — a scheduler admitting a couple of newly-eligible
actions per tick as their inputs become available.

The four largest jumps are all in the first ~180 lines, i.e. immediately after analysis:

    line 176: 1,832 → 6,355   (+4,523)
    line 178: 6,355 → 8,383   (+2,028)
    line 180: 8,851 → 10,877  (+2,026)
    line 182: 11,457 → 14,676 (+3,219)

**INFERRED:** these are the initial fill of the execution queue from the just-completed analysis.
Everything after is incremental dependency-unblocking.

### 2a. ⚑ The "median jump = 2" figure is a SUBSAMPLING ARTIFACT — corrected

The jump histogram above is computed over *distinct frontier values*, which discards how much real
time each step covers. Recomputing per-emitted-line (MEASURED, hook2):

| | median | mean | max |
|---|---|---|---|
| per-emission `done` delta | 9 | **12.8** | 1,789 |
| per-emission frontier delta | 0 | **12.8** | 4,523 |

**The two means are equal to 4 significant figures; their ratio is 1.0000.** That is not a
coincidence and it is not evidence of an artifact — it is forced: both series start at ~0 and end at
168,915, so over a full run they *must* have equal means. The informative part is the **medians**:
`done` advances by 9 on the median emission while the frontier advances by **0**.

So the correct statement is: **the frontier moves in bursts on a minority of emissions while `done`
advances steadily on nearly all of them.** The frontier changed on 2,607 of 13,192 emissions — 20%.

Is the trickle real or an artifact of the 0.2s rate limit? **MEASURED: real.** Elapsed 14,420s over
13,192 progress lines = **1.09 s per emitted line**, which is 5.5× the 0.2s rate limit. The limiter
was therefore not binding for most of the run — Bazel had nothing new to print, rather than being
throttled. The gaps between frontier movements are genuine idle stretches, not suppressed emissions.

⚑ **This does not rescue the refuted hypothesis.** Bursty growth is still not *stepwise discovery
at load time*: 2,607 bursts is two orders of magnitude more than the 11 projects, and all of it
happens after analysis completed at line 177. The mechanism in §3 (depth-gated scheduler
unblocking) is unchanged. What changes is the characterisation "continuous trickle" → **"frequent
small bursts on 20% of emissions."**

**What does NOT move it, MEASURED:**
- **Loading:** finished before the first meaningful progress line. hook2's package count is `100`
  in the very first `Analyzing:` line group and `100` at completion — it never changes during
  execution.
- **Analysis:** complete at line 177 of 16,086; `N` grew from 6,355 to 168,915 *after* that.
- **`test_suite` expansion:** happens in loading/analysis, before line 177.
- **Module extension / repository rules:** paperkit generates 117.5 MB of BUILD at fetch time,
  which is *before* loading. All 5 logs show `Computing main repo mapping:` / `Loading:` as the
  first lines, all before any progress line.

**So the answer to "when does it move" is: only during action execution, as the scheduler discovers
that previously-blocked actions have become runnable.** The graph was fully known at line 177; what
was not known was the *schedule*.

---

## 3. WHY the two regimes differ — the hypothesis is REFUTED

> **Stated hypothesis:** `//:hook` discovers its graph incrementally as each project's generated
> BUILD is loaded, while a single target is fully configured before execution begins.

**Both halves are wrong, and the second half is wrong in an instructive way.**

**Wrong half 1 — `//:hook` does not discover its graph incrementally.** Its graph is fully
configured at log line 177 (§1), before 99% of the frontier growth. Loading is not involved.

**Wrong half 2 — the single target is ALSO not "fully configured before execution begins" in any
way that distinguishes it.** MEASURED, `adq2.log` lines 4–9 verbatim:

    Analyzing: target @@+bib+paperkit_library//:adequacy (0 packages loaded, 0 targets configured)
    Analyzing: target @@+bib+paperkit_library//:adequacy (0 packages loaded, 0 targets configured)

    Analyzing: target @@+bib+paperkit_library//:adequacy (0 packages loaded, 26913 targets configured)

    INFO: Analyzed target @@+bib+paperkit_library//:adequacy (0 packages loaded, 53901 targets configured).
    [1 / 1] no actions running
    [120 / 53,980] Ζ·eval concept-builtin__tests__fixture_model__import_add__driver; 0s linux-sandbox ... (10 actions, 9 running)

`//:hook` *also* completes analysis before its execution-phase progress lines. **Both regimes fully
analyse first.** So target count is not the explanation, and neither is interleaved
analysis-and-execution — **there is no interleaving in either run.**

**The actual mechanism (INFERRED from the measurements, and it is a scheduling fact, not a graph
fact):**

`adq2` jumps from `[1 / 1]` straight to `[120 / 53,980]` — its frontier reaches its final value on
the **second** progress line, and holds for 5,651 lines. MEASURED denominator histogram, adq2:

          1  1
       5651  53,980

The `:adequacy` graph is **flat and wide**: ~54,000 independent `Ζ·eval` actions, essentially all
runnable the instant analysis ends, because they share one set of already-built inputs. The
scheduler enqueues the whole thing at once. Nothing is blocked, so nothing is *discovered* later.

`//:hook` is **deep and staged**: 24 test targets over 11 projects, each of which must build its own
staged inputs before its ~thousands of eval actions become runnable. MEASURED — hook2 sat at
`11 / 24 tests` from `done=3,849` to `done=133,287`, i.e. tests 12–24's action mass was gated behind
work that had to finish first. Each unblocking admits a few more actions: median jump 2.

⚑ **The distinguishing variable is DEPTH of the action graph (how much is blocked at t=0), not
breadth, not target count, and not analysis/execution interleaving.** A single target with a deep
graph would show a growing frontier; a 24-target suite of flat independent targets would show a
flat one. adq's own two runs corroborate: `adq.log` has 3 distinct denominators (28,188 → 53,980 →
53,981) rather than adq2's 2, because it ran from a colder cache and briefly had staging work
in front of the eval fan-out.

**Relevance of the 117.5 MB of generated BUILD and ~174,000 rule instantiations:** they set the
*scale* of `N` (172,957 targets configured → final `N` 168,915) and they make analysis expensive,
but they do **not** cause the frontier to grow, because they are all resolved by line 177.

---

## 4. Is the growth BOUNDED and predictable?

**Bounded: yes, in principle. Predictable in-run: no. Signalled: no.**

**Bounded (INFERRED, strongly):** final `N` ≈ targets configured, which *is* announced, exactly
once, at the end of analysis:

    INFO: Analyzed 24 targets (100 packages loaded, 172957 targets configured).

MEASURED ratio of final `N` to targets configured: 0.977 (hook2), 0.994 (hook3), 1.0015 (adq2).
⚑ **This is the single most useful under-exploited number in the log.** It appears at 1.1% of
elapsed log and predicts the final denominator to within 2.3%. It is available *before* the first
useful progress line.

Counter-example that bounds the claim: `hook-rbe.log` has 169,307 configured but final `N` only
70,760 — ratio 0.42. That run did not complete (no `Build completed` line). **So the ratio predicts
the denominator of a run that finishes; it does not predict where an aborted run stops.**

**No in-run "frontier is final" signal — and this is a claim about my query, stated as such.**

*Positive control, MEASURED:* my instrument (`grep -hoE '^INFO: [A-Za-z][^:0-9]{0,40}'` plus a
broad `grep -iE 'total|remaining|estimat|to go|percent|%'`) does find `INFO:`-shaped announcements —
it returned 25 distinct `INFO: From Ζ·eval …` families and found the totals line

    INFO: Build completed, 4 tests FAILED, 111270 total actions

So the instrument can see lines of the shape "Bazel announces a total." **It found exactly one such
line per run, and it is the terminal summary.** No line of that shape appears mid-run in any of the
five logs I read.

**The only exact in-stream marker is `done == N`**, which coincides with the final line. MEASURED,
the last two progress lines of hook2:

    [168,778 / 168,914] 23 / 24 tests, 4 failed; Ζ·eval gate-rejects-drift__bibparse__flip__Lexer_escaped_arm_0; 29s linux-sandbox ... (10 actions running)
    [168,915 / 168,915] 24 / 24 tests, 4 failed; no actions running

Note the second-to-last line still had the frontier moving (168,914 → 168,915). **The frontier is
final only when the run is over.** Any tool that waits for "N stops changing" will fire at
completion and never before.

---

## 5. What is the RIGHT progress signal

### The two signals currently in use

**The GAP (`N - done`) — UNSOUND as a remaining-work measure.** MEASURED: median 3,944, range
0–11,499, no trend across a 4-hour run. It is queue depth. It goes to zero only in the final ~20
progress lines. Using it as "work remaining" reports ~4,000 units remaining at 2% done and ~4,000
units remaining at 90% done.

*It does have one legitimate use:* a gap that is **pinned near zero for many consecutive lines while
`done` still advances** means the scheduler is input-starved — the graph has gone deep/serial. A gap
pinned at its ceiling means saturated. That is a *health* signal, not a *progress* signal.

**`k / 24 tests` — sound in kind, badly non-linear in practice.** MEASURED milestone table, hook2,
with true fraction computed against the known final `N` of 168,915:

| tests | log line | done | frontier | **true frac of final** |
|---|---|---|---|---|
| 11/24 | 179 | 3,849 | 8,851 | **2.3%** |
| 12/24 | 11,497 | 133,287 | 135,007 | **78.9%** |
| 13/24 | 11,834 | 136,702 | 139,579 | 80.9% |
| 15/24 | 13,432 | 150,297 | 151,766 | 89.0% |
| 19/24 | 13,520 | 150,533 | 152,416 | 89.1% |
| 23/24 | 14,428 | 153,891 | 155,452 | 91.1% |
| 24/24 | 16,082 | 168,915 | 168,915 | 100% |

⚑ **One test completion (11→12) spans 76.6 percentage points of the actual work.** Tests 15→23
span 2 points. The counter is monotone and truthful but its increments are worth between 0.1% and
77% of the run.

### How badly `done/N` lies

MEASURED, hook2 — apparent ratio vs. true fraction of final work:

| apparent `done/N` | at line | done | frontier | **TRUE** | overstates by |
|---|---|---|---|---|---|
| 50% | 31 | 347 | 562 | 0.2% | +61.5 pts |
| 90% | 142 | 523 | 578 | 0.3% | +90.2 pts |
| 95% | 164 | 553 | 578 | 0.3% | +95.3 pts |
| 98% | 8,881 | 98,679 | 100,681 | 58.4% | +39.6 pts |
| 99% | 11,315 | 131,476 | 132,801 | 77.8% | +21.2 pts |

**The run reads "95% done" at 0.3% done, 164 lines in.** This is the misreading the session made,
and it is not a marginal error — it is off by 95 percentage points. The session's reported "94%
done" run corresponds to somewhere in the 20–60% range depending on when it was sampled.

Contrast `hook3-bes.log`, where apparent 98% ≈ true 98.0% — because that run was cache-warm and
short, so the frontier had already converged. ⚑ **`done/N` is accurate exactly when it is not
needed** (short warm runs) **and maximally wrong when it is** (long cold runs).

### Recommended signals, in order

1. **`targets configured` from the `INFO: Analyzed …` line, as the denominator.** Available at ~1%
   of elapsed log, predicts final `N` to within 2.3% on completing runs. Compute
   `done / targets_configured`. This is a genuine progress fraction. On hook2 it would have read
   0.3% where `done/N` read 95%.

2. **`done` against the previous run's final `N` for the same target set.** Strictly better than (1)
   when a prior run exists, because it corrects the 2.3% bias. Failure mode: invalid after any
   change to the generated BUILD graph or the target set — and paperkit regenerates 117.5 MB of
   BUILD at fetch, so a `MODULE.bazel` or `warrants.bib` change invalidates the baseline. **Guard
   it by comparing this run's `targets configured` to the baseline run's; if they differ by more
   than a few percent, discard the baseline.**

3. **`k / N tests` as a coarse milestone**, understood as unequally weighted. Useful for "which
   project is it on," useless for "how long left."

4. **Gap as a saturation/health indicator only**, never as remaining work.

5. **Do not use `done/N` for anything.** It is the ratio of two numbers that move together by
   construction.

### What none of these give you

**Wall-clock ETA.** MEASURED: hook2 ran 14,420s for final `N` 168,915; hook3 ran 2,496s for final
`N` 114,982. That is **68% of the work in 17% of the time** — a 5× difference in seconds-per-unit
between two runs of the same target. `N` is denominated in scheduled work units whose cost varies
by orders of magnitude with cache state (§1: 114,982 frontier vs 17,918 executed actions). **No
function of the progress line predicts wall time.** Time-to-completion requires the per-run cache
hit rate, which is not in the progress stream.

---

## 6. Derivation appendix — how each figure was obtained

All logs at
`/home/mikemol/.tmp/claude-1000/-home-mikemol-github-paperkit/4ce41847-9cb9-4a4c-bc82-03f9dfab5c52/scratchpad/`.

Extraction regex, applied per line: `^\[([\d,]+) / ([\d,]+)\]`.

| quantity | method |
|---|---|
| distinct denominators | `sort -un` over extracted field 2 |
| monotonicity | pairwise scan for `c[i+1] < c[i]`; 0 hits in 5 logs |
| jump histogram | diffs of consecutive distinct frontier values |
| analysis-completion line | `grep -n 'INFO: Analyzed'` |
| targets configured | capture from `INFO: Analyzed …\((\d+) packages loaded, (\d+) targets configured\)` |
| total actions | `grep '(\d+) total actions'` |
| true fraction | `done / final_N`, final_N = max frontier in that log |
| test milestones | first occurrence of each distinct `(\d+) / 24 tests` |

Counts per log (MEASURED): progress lines / distinct denominators —
hook2-FINAL-4fail **13,192 / 2,608**; hook3-bes **2,273 / 320**; hook-rbe **4,597 / 414**;
adq2 **5,637 / 2**; adq **5,613 / 3**.

⚑ Note the session's reported "2,608 distinct denominators" for hook2 reproduces exactly. Its
reported range "562 → 168,080" is close but the measured range is **562 → 168,915** (the run's true
final frontier); and the reported "flat at 53,980 across 5,434 lines" for adequacy is right for
adq2 but `adq.log` reaches **53,981**, so "flat" is a property of that one run's cache state, not of
single-target runs generally.

### Not established

- I did not read Bazel 8.7.0's Java source; the `INFO: Analyzed` positioning and the
  frontier/configured-targets correlation are behavioural evidence, not a source reading. The claim
  "`N` counts scheduled action-execution work units" is INFERRED from that correlation plus the
  frontier-vs-`total actions` divergence, not read from `ExecutionProgressReceiver`.
- ~~`bazel help build` could not be consulted~~ — **CORRECTED 2026-09-06.** I initially recorded
  this as blocked on the server lock; it was not. The call completed (it had merely exceeded a
  120s foreground timeout and was backgrounded). It is consulted in §1a and §2a below. My original
  note was an inference from a timeout, reported as a measurement — exactly the error this
  document's own rules forbid.
- `hook-rbe.log` is an incomplete run and is used only as the counter-example in §4.

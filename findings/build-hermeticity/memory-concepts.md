Third-party measurement by a subagent dispatched from linux-sources, against CENSUS-build-hermeticity.md rev 21. memory-concepts has no live session and did not survey itself.

# MC- build-hermeticity leg — memory-concepts (third-party measurement)

Tagged per `§R`: **third-party measurement.** All claims below are `citation` (quoted bytes) or
`machine` (a command's output) only. No `testimony`, no `inference` about memory-concepts'
intentions, decisions, or declines. Timestamp of measurement: 2026-09-06.

## MC-0 The cassian-observability claim, verified rather than inherited

⚑⚑⚑ **ATTRIBUTION CORRECTED 2026-09-06 BY `cassian-observability`, WHO MEASURED IT AGAINST THEIR
OWN FILED LEG.** This section originally read *"`cassian-observability` reported: 'MEMORY.md is
projected from its warrants.bib with a byte-compare freshness gate.'"* **That sentence is from a
`SendMessage` SUMMARY, not from their leg** — the record showed a party filing a claim it did not
file. Corrected here per `§W`'s rule that a false attribution is repaired in place; the **findings
below are unchanged**, at their explicit request.

**What the filed leg actually says**, `§0`, verified by the dispatcher against
`findings/build-hermeticity/cassian-observability.md` at `md5 2336113438ec2ba9291404bc01848aaa`
(byte-identical to their own copy):

> *"a bib→index projector, a byte-compare freshness gate, and an explicit two-property split
> between **the projection is deterministic** (gateable there) and **the deployed copy in
> `~/.claude` is stale** (**deliberately not gated**, because a gate reaching into a tree it does
> not own would assert a property of a tree that changes between sessions by design)"*

⚑⚑ **SO THE SPLIT THIS LEG INDEPENDENTLY RE-DERIVED — SNAPSHOT GATED, DEPLOYED COPY ADVISORY — WAS
ALREADY IN THE SOURCE LEG, CORRECTLY ATTRIBUTED TO THE SOURCE'S OWN REASONING.** The summary
collapsed six lines into one sentence and **named the advisory artifact as the gated one.**

⚑⚑⚑ **AND THE CLASS IS ONE THE CENSUS SHOULD HAVE: A PARTY'S SUMMARY OF ITS OWN ARTIFACT DEGRADED
IT, AND THE SUMMARY IS WHAT THE CONSUMER MEASURED AGAINST.** The usual lossy-channel finding is a
relay degrading someone *else's* claim. Here **the author was the lossy channel about their own
work, and the loss was invisible to them because they could still see the artifact** — while the
consumer had no way to know the summary was lossier than the file, which was sitting in the
consumer's own tree. ⚑ **Nothing gates it**: cassian's commit-msg hook binds numbers a run
produced, the leg is byte-gated by md5 on adoption, and **nothing compares a MESSAGE about an
artifact to the artifact.** *A measurement restated at a consumer site, where the consumer is a
peer session.* Not mechanizable here, and not claimed to be.

⚑ **THE ERROR STOPPED AT ATTRIBUTION BECAUSE THIS LEG REFUSED TO CARRY EITHER VERSION FORWARD.**
The original filename claim was also partly wrong (`MEMORY.index.md`, not `MEMORY.md`, per the
positive control below) — and re-deriving the whole claim from the tree is why a lossy summary
produced a corrected record rather than a propagated fact.

**Positive control for the filename claim** (machine, 2026-09-06):

```
find /home/mikemol/github/memory-concepts -maxdepth 2 -name 'MEMORY.md'   -> NOTHING
find /home/mikemol/github/memory-concepts -maxdepth 2 -name '*.md'        -> HANDOFF.md,
    MEMORY.index.md, library.md
```

**What is actually true, each claim cited to a byte:**

1. **There IS a projection, and its producer/input/output are named in the source.**
   `gen_index.py` docstring (citation, lines 1–9):
   > *"Project cassian's MEMORY.md index FROM the warrant library (the structured source of
   > truth). MEMORY.md is the per-session-loaded memory index: one line per memory,
   > `- [Title](origin.md) — hook`, grouped into sections. It was hand-maintained and drifted
   > from the memory files' own content... This makes it a PROJECTION instead: the warrants in
   > warrants.bib are the source, rubric.tsv is the section order, and this generator emits the
   > index deterministically."*

   - **Producer:** `gen_index.py`, function `build()`.
   - **Input:** `warrants.bib` (via `bib.parse_project(HERE)`) + `rubric.tsv` (via `bib.rubric(RUBRIC)`) — both read through paperkit's own `bib` module, not a hand parser (comment at line 14–15 states this is deliberate, to avoid silently dropping declared `consumer_fields`).
   - **Output:** the in-repo file `MEMORY.index.md` (`SNAPSHOT = HERE / "MEMORY.index.md"`, line 45) — **not** `~/.claude/.../MEMORY.md`, which is a *separate, deployed* copy.

2. **There IS a byte-compare gate, and it targets the in-repo snapshot, not the deployed copy.**
   `gen_index.py` lines 274–281 (citation):
   ```
   if "--check" in argv:
       if not SNAPSHOT.exists() or SNAPSHOT.read_text() != body:
           print(f"gen_index: STALE — {SNAPSHOT.name} differs from the projection ...")
           return 1
       print(f"gen_index: {SNAPSHOT.name} is fresh")
   ```
   This is an exact byte comparison (`SNAPSHOT.read_text() != body`) between the committed
   `MEMORY.index.md` and the freshly-built projection — confirming "byte-compare freshness gate"
   as a mechanism, but over `MEMORY.index.md`, never over `~/.claude/.../MEMORY.md`.

3. **The deployed copy (`~/.claude/.../MEMORY.md`) is checked separately, and NON-FATALLY.**
   `gen_index.py` lines 237–255 (citation), the `--deployed-check` branch: reads
   `CORPUS / "MEMORY.md"`, compares it textually to the fresh projection, and **always returns 0**
   regardless of the result — the comment calls this "a TOLERANT drift advisory (never a hard
   fail — always exits 0)" because "the corpus/warrants change between sessions by design ... a
   gate that FAILED on this would flap."

4. **A third, distinct check exists: corpus coverage (bidirectional).**
   `gen_index.py` function `coverage()` (lines 218–233, citation): computes
   `unwarranted = disk - warrant_origins` (a memory file with no warrant — would be silently
   dropped from the index) and `dangling = warrant_origins - disk` (a warrant whose origin file no
   longer exists). Machine confirmation this directory of memory files is large and populated —
   `find ~/.claude/projects/-home-mikemol-github-cassian-observability/memory -maxdepth 1 -name
   '*.md' -printf '%f\n'` returned **166 filenames** including `MEMORY.md` itself, 2026-09-06.

5. **What runs all three checks together: `./check`, a bash script — invoked BY HAND, not by any wired git hook.**
   `check` (citation, full file, 41 lines): runs `paperkit/gate.py` (warrant DAG soundness),
   `gen_index.py --check` (index freshness), `gen_index.py --coverage` (corpus coverage), and
   `gen_index.py --deployed-check` (advisory only) — in that order, `set -euo pipefail`, single
   entry point, comment: *"Run before committing (or from CI)."*

   **Machine check for a wired hook** (2026-09-06): `find
   /home/mikemol/github/memory-concepts/.git/hooks -maxdepth 1 -type f` returned **only
   `*.sample` files** (`pre-commit.sample`, `commit-msg.sample`, `pre-push.sample`, etc. — 13
   samples, zero real hooks). **Positive control that the reader can see a real hook when one
   exists**: none available in this tree to demonstrate a non-`.sample` hook (none of the 13 git
   hook files present lacks the `.sample` suffix), so the negative rests on the absence of any
   file without that suffix — the corpus itself supplies the population (git's fixed hook-name
   set) and every member present is a sample. No `.pre-commit-config.yaml`, no CI workflow file
   found under a 2-level search either (`find ... -maxdepth 2 -type f` listing above shows no
   `.github/` or `.githooks/` entries in the top-level file list).

**Conclusion on MC-0, stated at the warranted precision:** the projection and the byte-compare
freshness gate both exist exactly as described, but (a) the gated artifact is `MEMORY.index.md`,
a same-repo snapshot, not `~/.claude/.../MEMORY.md`; (b) the deployed copy comparison exists but
is explicitly advisory/non-blocking by design; (c) nothing in the repo-local git hooks directory
invokes `gen_index.py --check` or `./check` automatically — it is a manually-run (or CI-run, per
the script's own comment) gate, not a commit-time gate, as machine-measured above. Whether it
actually runs in CI is UNMEASURED — no CI config file was found in the top-2-level file listing,
which is itself only evidence against local discovery, not proof no CI exists elsewhere (e.g. a
GitHub Actions workflow could reference this repo from outside it — UNMEASURED, out of reach of a
tree read).

## §Q answered / unanswerable / unmeasured

**§Q-1 (what do you build with):** No build system in the bazel/make sense. The repo is driven by
a bash script (`check`) invoking Python scripts directly (`paperkit/gate.py`, `gen_index.py`) via
`python3`, no `mise.toml` or `.python-version` found in the top-level listing, no `uv.lock` /
`requirements*.txt` / `pyproject.toml` build metadata beyond `paper.toml` (paperkit's own project
descriptor). `paper.toml` citation (lines 1–33) shows the actual "build" is paperkit's gate:
`[checks.witness] cmd = "python3 concepts.py {target}"`.

**§Q-2 (measure off the live process):** UNMEASURED — no live process to sample; this repo has no
live session and nothing was invoked as part of this leg (cost discipline: running `./check`
would invoke a full paperkit gate over an unknown-size warrant set; declined per cost discipline,
not attempted).

**§Q-3 (dynamic work discovery — derived or authored):** **DERIVED**, and it is an eighth distinct
mechanism relative to the six already tabulated in the run file (linux-sources' bazel generator,
paperkit's repository_rule, substrate's Makefile generator, substrate's censuses/ratchets,
substrate's worklist-as-paperkit-project, gabion's authored YAML frontmatter registry).
Specifically:
  - **Producer:** `gen_index.py:build()`.
  - **Input:** `warrants.bib` + `rubric.tsv`, read via paperkit's `bib.parse_project` /
    `bib.rubric`.
  - **Output:** `MEMORY.index.md`, a checked-in markdown snapshot (not a `BUILD.bazel`, not a
    Makefile — a documentation artifact).
  - **Fan-out:** unmeasured exactly (would need a warrant count and an index-line count); the
    `HANDOFF.md` citation above states "Witness count: 76 in concepts.py" as of the last recorded
    phase, which is evidence of scale but not a verified current count (HANDOFF.md is a narrative
    record, not re-derived here).
  - **Drift check:** `gen_index.py --check`, an exact byte-compare, described above — a real gate,
    not merely a report.
  - **What makes it an eighth mechanism, not a variant:** none of the six tabulated mechanisms
    project into a **markdown index consumed by a completely different tree's runtime session
    memory** (`~/.claude/projects/.../memory/MEMORY.md`, read by cassian-observability's live
    sessions). The generated artifact is downstream documentation for a *different repository's
    live agent*, not a build target, not a Makefile, not a bazel `BUILD` file. It shares the
    derive-then-drift-check shape with linux-sources' bazel generator and substrate's Makefile
    generator, but the cross-repo consumption relationship (§Q-5's subject) is unique among the
    seven so far measured.

**§Q-4 (work specificity):** The natural grain is **one warrant per memory file** (one-to-one, not
a fan-out like linux-sources' 42→262). Machine evidence: `HANDOFF.md` states witness counts
tracking closely with corpus file counts (67 witnesses / ~66 content witnesses against a
comparable memory-file population, then 76 after a completeness pass). A finer grain (per-claim,
if a memory carries multiple claims) or coarser grain (per-section) were not measured; not
attempted per cost discipline (would require executing `concepts.py` or `gen_index.py`, both of
which import paperkit's `bib` module and could execute checks — deferred).

**§Q-5 (cross-repo edges):** **CONSUMES**: paperkit's `bib` module by sibling-path import
(`PAPERKIT = HERE.parent / "paperkit" / "paperkit"`, `sys.path.insert`) — declared in code, not in
a manifest; **AMBIENT by the run-file's own vocabulary** (works because the sibling directory
`../paperkit` exists at a fixed relative path, no version pin visible in the citation read).
**EMITS**: the projected `MEMORY.index.md` is designed to be redeployed to
`~/.claude/projects/-home-mikemol-github-cassian-observability/memory/MEMORY.md` via
`gen_index.py --write <path>` (citation, docstring line 25, `--write` usage) — an edge to
cassian-observability's live session memory. This EMIT edge is exactly the kind the run file
notes "nobody records" (§Q-5): it is invisible from memory-concepts' own manifest and only
visible by reading the generator's target-path handling.

**§Q-5b (invoked executables):** `python3` (ambient, no interpreter path pin observed in `check` —
citation: `env --chdir="${HERE}" python3 gen_index.py --check`, bare `python3`, not a `.venv`
absolute path). `bash` (the `check` script's own shebang, `#!/usr/bin/env bash`). No `jq`,
`shellcheck`, `pandoc`, or `bazel` invocations found in the files read.

**§Q-6 (interpreter determination):** **AMBIENT.** `check` invokes bare `python3` (three times,
citation lines 21/24/27 above) with no `.venv/bin/python` path and no interpreter version check.
No `mise.toml` found at the top level. `which -a python3` was NOT run for this measurement — doing
so would reflect the **borrower's** (this subagent's, parented through linux-sources) PATH, not
memory-concepts' own environment, per this leg's explicit constraint against misattributing a
borrowed tool's environment. **UNMEASURED-for-the-subject**, not zero.

**§Q-7:** UNANSWERABLE BY A THIRD PARTY — only memory-concepts can say

**§Q-8 (hermeticity, what was proven):** No sandboxing mechanism observed (no bazel, no
containerized gate invocation in `check`). The one property that IS proven rather than merely
declared: **the index-freshness byte-compare** (`gen_index.py --check`) is a genuine equality
proof between a committed file and a regenerated one — if it has "ever fired" (gone red) is
UNMEASURED (no CI log or git history of a failed gate run was read; reading `git log` history for
this would require a git log query not attempted here per the single-tool-call discipline and
time budget — flagged as UNMEASURED, not zero).

**§Q-9:** UNANSWERABLE BY A THIRD PARTY — only memory-concepts can say

## Absences and their controls

| absence claimed | control run | result |
|---|---|---|
| no `MEMORY.md` in memory-concepts | `find ... -name '*.md'` over same dir | 3 hits (`HANDOFF.md`, `MEMORY.index.md`, `library.md`) — reader works |
| no wired git hooks (only samples) | `find .git/hooks -maxdepth 1 -type f` | 13 hits, all `*.sample` — reader returns non-empty, proving it can see files; the absence is of a *non-sample* file specifically |
| no CI config at top 2 levels | `find -maxdepth 2 -type f` (already run) | returned 15 real files (HANDOFF.md, warrants.bib, paper.toml, MEMORY.index.md, gen_index.py, .gitignore, registry.tsv, concepts.py, check, .delta-cache.json.stale, library.md, rubric.tsv, checks/fixture.py, plus .git/* internals) — reader is not empty/broken, no `.github` or `.githooks` among them |
| no `mise.toml` / interpreter pin at top level | same `find` listing | absent from the same non-empty listing above |

## §R roster nomination

Not attempted — this is a third-party measurement leg with no author present to nominate on
behalf of; nominating would require inference about who memory-concepts' maintainer believes
touches this repo, which is testimony this leg may not produce.

## Timestamps

All figures and file reads in this leg were measured 2026-09-06, in the single pass described
above; no code was executed (no `./check`, no `gen_index.py`, no `concepts.py`, no `uv sync`, no
build) per the cost-discipline constraint on this dispatch.

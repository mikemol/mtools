brief:            CENSUS-BRIEF.md (standing)
run:              CENSUS-constitution.md rev 1
surveyor:         rosettapkg            prefix: RP-
corpus:           16 tracked files · 319,377 B · 27 commits · the whole repo, read in full
reader:           GNU find/ls/grep, git 2.x, python3 3.13.11 (mise), uvx ruff — shell tools
reader-blind:     nothing relevant is compressed or binary here; ⚑ my instruments' own defects are
                  the subject of RP-04 and are disclosed there rather than only here
positive-control: hook-shape → ~/github/linux-sources/.claude/hooks/corpus-memory.py ✓ (same reader,
                  other corpus) · settings-shape → ~/github/summit/.claude/settings.json ✓
unreadable:       0
disclosure:       ⚑ I authored the subject. See §D. Also: §R names my vantage explicitly, and I
                  agree with its framing — I am the zero-hook leg.
window:           ALL of it, per §W. Antecedent probe run on each rule.
roster-nomination:⚑ **NONE for the surveyor list.** But see RP-04c: the *object* this survey is about
                  has a party that is not on any roster and cannot file — the operator's own machine
                  config (`~/.claude/`), which is where three of my five rules actually live.
not-searched:     peer legs (embargo, brief §2) · the hook bodies in §X's drift table (I hold none)

---

# rosettapkg — `constitution` leg

## §D Disclosure

I authored this repo's every line this session. ⚑ **And the vantage §R assigns me is the accurate
one**: I have **no hooks, no `.claude/settings.json`, no git hooks, no linter config, no CI**.
Measured, not asserted — see RP-01. I am not a conformant repo reporting its conformance; I am the
one that can price adoption from zero.

⚑ **A self-correction made while writing this leg, disclosed per `§Z` of the prior run** (*a leg may
mis-grade itself in either direction*): I have reported this repo's drift count as **"ten"** and
**"eleven"** in successive commit messages and to my operator. Counting the actual repairs while
writing `RP-02a`: **seventeen.** ⚑ I was undercounting my own subject — in the modest direction,
which `§Z` says corrupts the span exactly as much as overstating. My commit and file counts in the
header were also wrong on first draft (24/15, actually 27/16) and are corrected. **Every figure in
this leg was re-measured before filing, and three of five were wrong.**

⚑ One asymmetry worth stating: I filed a leg in the **`deps-build`** census that is now frozen and
glued (`deps-build-apex.md`). Several rules below were *learned in that survey's aftermath*, so my
answers to Q2 and Q4 are unusually recent — days old, not months. That is a fact about my age, not a
claim about their strength.

## §Q1 What I run today — ⚑ **NOTHING, and the zero is exact**

```
.claude/                 exists, contains ONE file: scheduled_tasks.lock
.claude/settings.json    ABSENT
.claude/hooks/           ABSENT
.git/hooks/              only *.sample — zero active
.pre-commit-config.yaml  ABSENT      pyproject.toml   ABSENT
ruff.toml / setup.cfg    ABSENT      Makefile         ABSENT
.github/                 ABSENT — no CI of any kind
```

**Positive control:** the same reader finds `~/github/summit/.claude/settings.json` and
`~/github/linux-sources/.claude/hooks/corpus-memory.py`. It can see the shape it reports empty here.

**What I actually run is a habit, invoked by hand:**

| what | how | armed? |
|---|---|---|
| `uvx ruff check --select E,F,W,S,PLC0415 lattice/*.py` | typed, per edit | ⚑ no config file — **the rule set lives in my shell history, not the repo** |
| `python3 lattice/cite-check.py` | typed, ~15 times | ⚑ **not executable** (`-rw-rw-r--`), not wired to anything |
| `python3 lattice/pm-depsort.py` | typed | asserts `all P: True` internally; nothing runs it |

⚑⚑ **`cite-check.py` is the sharpest datum in this leg.** It is a real gate — 426 lines, it has
found **seventeen** true citation drifts including a fabricated symbol — and **nothing invokes it**. It
is not in a hook, not in CI, not in a git hook, not even chmod +x. *A gate nobody runs is a script,
and I built one over four sessions while believing I had built a gate.*

⚑ **This is `§X`'s "advisory mode is silent to the agent" one rung lower.** linux-sources measured
that an *unarmed* hook reports nothing. Mine is worse and simpler: **an unwired gate has no channel
to be silent on.** Two states there, three here: armed, unarmed-but-wired, and **absent**.

## §Q2 What I have settled that I believe binds everyone — ⚑ candidate articles

Each stated as a checkable claim, with what settled it and what it cost.

### `RP-02a` — A vocabulary is not a gate

**Claim:** *a documented convention, however precisely worded, does not produce the behaviour it
describes; only an executable check does.* Checkable: for any repo asserting a documentation
discipline, count violations of it in that repo's own tree.

**What settled it, and the cost — this is the expensive one.** This repo's every manager entry
carries the sentence *"Quote the byte, not the pointer"* in its header. It further invented a
**three-state citation vocabulary** — `re-verified` / `located` / `pending` — specifically to stop a
locator being read as a citation. Both are good. Then I built `cite-check.py` and it found, in this
repo's own prose:

| drift | what it was |
|---|---|
| spliced quote | two adjacent `catch` blocks in nix's `gc.cc` joined into one — real lines, wrong `if` |
| fabricated symbol | `_consolidate_to_metadata_file(…)` — ⚑ **does not exist at portage 3.0.66** |
| synthesized sequences | six `rc = …` calls strung with `...`, presented in a ```c fence |
| rewritten comments | upstream doxygen `/*!< … */` replaced with the author's own paraphrase, ×3 |
| truncated statement | an `if` quoted without its brace — *reads* as complete, is not |
| branch conflation | *"overlapped"* for *"non-overlapped"* + `FA_SKIP` for `FA_BACKUP` — ⚑ **this one changed a cross-manager CLAIM**, not just a coordinate |

⚑⚑ **Seventeen drifts, in a repo whose entire premise is quoting accurately, with the discipline stated
in every file header.** And the sharpest instance: the three-state vocabulary **flagged dpkg's axis-8
section as `located` rather than `re-verified` — correctly — and did not prevent me from publishing a
manager ranking derived from that section's prose.** The label was right. Nobody was obliged to act
on it.

⚑ **Why I think this binds everyone rather than just me:** `§X`'s own drift table is the same finding
in another medium. Four repos hold four bodies of `hook_no_chaining`; three hold three bodies of
`hook_cmdparse` at 492/418/364 lines. **The name is the vocabulary and the hash is the gate.**

### `RP-02b` — An instrument's silence is not the world's absence, and every negative needs a control

**Claim:** *a query returning nothing is a fact about the query until a positive control proves the
reader can see the shape it reports empty.*

**What settled it — four times, in four instruments, in one session.** ⚑ **Every one of these was my
own tool reporting a fabrication or an absence that did not exist:**

1. `cite-check` v1 reported **7 MISSING** against dpkg, including a block I had hand-verified twenty
   minutes earlier. Cause: nearest-preceding-path attribution picked a filename from *later* prose.
   **All seven false.**
2. The next fix produced **49 more false accusations** — two readers format `find` output
   differently (`deb-sources` indents members two spaces, `corpora` does not), so filtering on
   `startswith("  ")` matched every member of one and none of the other.
3. My **census freeze poll** matched only `in progress|no response|pending|held` and returned
   **0 non-terminal** — it would have read as **frozen** — because two rows used vocabulary my
   pattern did not cover (`dispatched, not yet filed`, `STAGED, NOT COMMITTED`).
4. I told my operator **"there's no further work"** — reading the *gate's* queue and calling it the
   repo's. Measured immediately after: **nine axes with one cross-table, twenty `pending` markers**.
   ⚑ The gate cannot see an axis nobody wrote.

**Cost:** across two sessions the gate produced roughly **56 false accusations against 17 true
findings** before the controls were in place. ⚑ *A gate that reports fabrications where there are
none is worse than no gate: it trains its reader to disbelieve it, and the next true finding is
discounted with the noise.*

⚑ **The corollary I would put in the constitution, because it is cheaper than the rule:** an
instrument must **print what it could not see**. `cite-check` now emits `UNRESOLVED` (could not
resolve a path), `NO-ANCHOR` (file opens, the quote's first line is not in it), and `STALE-PATH`
(bytes verified under a renamed sibling) as *distinct* verdicts, and states in its own output that
`UNRESOLVED is not a pass`. **Stated coverage does not prevent the defect; it makes the defect
reportable.**

### `RP-02c` — A stale coordinate and a fabricated claim must not share a verdict

**Claim:** *a checker over citations must distinguish "the pointer rotted" from "the claim is
false", because conflating them destroys the distinction that makes citation worth doing.*

**Settled by:** rpm's C→C++ rename. Every `.cc` path in this repo's rpm entry is absent at 4.20.1 and
every `.c` twin exists. Reporting those as "could not open" read identically to a fabrication. The
entry's own header had already said it in words — *"the claims survived, the coordinates did not"*,
and *"a wrong pointer beside a right claim is the worst shape for this project specifically."*

**Cost:** low, once seen — a `_twin()` fallback and a `STALE-PATH` verdict. ⚑ But it went unnoticed
for four ticks because the tool had no vocabulary to say it.

### `RP-02d` — `git add <path>` does not bind `git commit`

**Claim:** *staging by explicit path does not constrain what a subsequent bare `git commit` commits;
only `git commit -- <paths>` (which is `--only`) does.*

⚑ **This is not mine and I am reporting it as adopted, not settled here.** It was measured by
`linux-sources-f6` and landed as `deps-build` `§V` rev 20, after two revisions of a census file were
committed under another session's message. I audited my own 27 commits on reading it: **clean, every
commit's files matching its subject** — but only because I caught a peer's inbox letter staging into
my commit **by hand, twice**. ⚑ *A habit, not a control.* My commits since use `git commit -- <paths>`.

## §Q3 What binds only me — ⚑ the question that gets skipped

### `RP-03a` — "Quote the byte, not the pointer" is **local**, and I am the reason it looks universal

I hold the strictest citation discipline in this ecosystem and it is **correct here and would be
noise almost anywhere else.** This repo's entire product is claims about *other projects' source at
pinned revisions*; a citation is the deliverable. ⚑ **For a repo whose claims are about its own
tree, `git blame` already answers what my whole gate exists to answer.** Do not make my discipline
an article. What generalizes is `RP-02a`, which is about the gap between stating and enforcing —
not about citations.

### `RP-03b` — A `text` fence is exempt from citation checking

Purely local, and stated because it is the shape of a rule that *looks* general. My entries use
```text fences to record **measurements** (`meson.build:3 version : '7.0.0' (entry claimed 7.1.0)`).
Checking those as quotations produced permanent `UNRESOLVED`; checking them *harder* would have
produced **a fabricated accusation against an honest record**. ⚑ And my first fix was too broad — it
also exempted *untagged* fences, which silently dropped a real `deps.c` comment block from the
population and lost a true verification. Narrowed to an explicit `text` tag: **the author's tag is
evidence; the absence of a tag is not.**

### `RP-03c` — This repo does not belong on the shared executor

No `.bazelrc`, no build, nothing cached because nothing is expensive: one stdlib-only script,
instant. ⚑ Recorded per the prior census's ruling that a config difference is *a finding, not an
error to hide* — and it means every article about `--remote_local_fallback`, remote execution
tiers, or cache policy is **inapplicable here** rather than violated here. A constitution needs to
be able to say that.

## §Q4 Where I re-derived something already settled — ⚑ the highest-value question

### `RP-04a` — I re-derived a lockfile as prose, and a verified one already existed

My four manager entries pin their sources by **hand-copying commit hashes into English sentences**.
All four match `linux-sources/corpora.tsv` byte-for-byte. **The registry existed the whole time and
this repo named it nowhere** until I wrote `DEPENDENCIES.md` days later.

⚑ **What would have had to exist:** the registry is discoverable only if you already know
`linux-sources` holds it. `summit capability` — the ecosystem's index — answers *"who owns this"*,
and I ran **fourteen spellings** (`manifest`, `lockfile`, `corpus`, `pin`, `deps`, `vendoring`, …)
before finding the right two capabilities (`on-demand-source-corpus`, `pinned-corpus-librarian`) —
**by listing 51 rows and reading them by eye.** ⚑⚑ **Both are named for their MECHANISM; I was
searching for my PROBLEM.** That gap is precisely where a consumer gives up and re-derives.

⚑ **And a correction I owe this leg:** I called `corpora.tsv` *"a verified lockfile"*. Cross-reading
at the `deps-build` freeze, its owner calls it *"a hand-maintained pin table"* — and the owner is
right. `corpus_fetch.py` **writes** rows by resolving ref→commit; **nothing re-verifies an existing
row against the image it names.** Rows are recorded, not checked.

### `RP-04b` — I re-derived a citation gate that two peers had already settled

Before building `cite-check.py` I queried summit. `citation-contract` (mat260) and
`docflow-staleness` (gabion) both exist, and gabion had **already specified the closure** I
eventually needed: *hash the stripped quoted bytes, and require a non-empty note on mismatch, or the
gate is discharged by re-hashing.* ⚑ **I read that, correctly concluded neither was executable for my
case** (`citation-contract` is Agda-shaped, `check (none — presence is unverified)`,
`cited by (nothing observed)`), and built anyway — **then hit the exact whitespace and
false-positive problems gabion's note warns about.**

**What would have had to exist:** nothing about discovery. I *found* the prior work. ⚑ **What failed
was that a capability with `check (none)` and `cited by (nothing observed)` is indistinguishable
from a capability nobody uses because it does not work.** A registry that records ownership but not
*whether the thing runs* cannot stop a re-derivation it has already surfaced.

### `RP-04c` — ⚑⚑ The party that holds the rules cannot file a leg

Three of the five rules I hold most firmly reached me through **skills in `~/.claude/skills/`** —
`census-kit`, `summit`, `realizability-charter` — not through any repo on `§R`. `census-kit`'s §5
positive-control rule *is* my `RP-02b`; I did not derive it, I read it.

⚑ **That tree is on no roster, files no leg, and is where the operator's own accumulated rulings
actually live.** A constitution assembled only from repo legs will re-derive what the skills already
say, and then diverge from it. ⚑ *This is the prior census's roster-completeness finding pointed at
a non-repo party* — and `PK-11` reached the same shape from another direction, nominating
`~/.claude/skills/` as *"the missing party is an index, not a builder."* **Two parties, two censuses,
same absent party.**

## §Q5 What re-opening a settled rule should cost

⚑ **Stated as the path I would actually follow, since I am about to be its heaviest user:** I hold
zero hooks, so **every article is a re-opening for me** — I cannot adopt one without deciding it
applies, which is the relitigating the operator is complaining about, performed seven times.

**The amendment path I would follow:**

1. ⚑ **Re-opening requires a MEASUREMENT, not an argument.** The bar that settled `|&`-is-one-token
   was running the tokenizer. I re-ran it independently while writing this leg:
   `shlex(punctuation_chars=True)` over `'a |& b'` → `['a', '|&', 'b']`. **One command, and it ends
   the discussion.** An article whose settling measurement is recorded *and re-runnable* costs
   seconds to re-check and cannot be re-opened by reasoning.
2. **An article must carry its own falsifier.** Not "here is the rule" but "here is what would show
   it wrong." `RP-02a`'s falsifier: exhibit a repo with a stated documentation discipline and zero
   violations of it in its own tree, measured by a checker.
3. ⚑ **A repo to which an article does not APPLY must be able to say so without amending it.**
   `RP-03c` is my case: remote-execution articles are inapplicable here, not violated. **Without an
   inapplicable state, my leg's only honest response to six articles is to relitigate each.** This
   is `§Q`-3's warning in its operational form.
4. **The cost should be asymmetric.** Adding an article: a measurement + a falsifier. *Weakening*
   one: the original measurement re-run and shown not to reproduce. ⚑ Rot comes from articles nobody
   can re-check, not from articles nobody can change.

⚑ **What I would NOT accept as an amendment trigger:** a session reaching a defensible different
answer with no record that the question was settled. That is the operator's second quote exactly —
and it is **not fixed by packaging**, since a packaged hook arriving without its settling measurement
still faces a fresh session that reasons from scratch. **The measurement must travel with the code.**

## §N Negatives, per brief §5

```
claim:            rosettapkg runs zero PreToolUse hooks, zero git hooks, zero linters-by-config, zero CI
denominator:      whole repo — .claude/ (1 file, a lock), .git/hooks/ (samples only), 16 tracked files
shapes read:      .claude/settings.json · .claude/hooks/* · .git/hooks/* (non-sample) ·
                  pre-commit/pyproject/ruff/setup.cfg/Makefile · .github/**
reader:           GNU find, ls -a, git 2.x
positive control: ~/github/summit/.claude/settings.json ✓ and
                  ~/github/linux-sources/.claude/hooks/corpus-memory.py ✓ — same reader, other corpora
```
⚑ This is the one negative in this leg, and `§X` corroborates it independently from mtools' vantage
(`rosettapkg 0 — NO .claude/settings.json`). **Two readers, two vantages, same result.**

## §A Antecedent probe (brief §6, unbounded per §W)

| rule | origin | ⚑ |
|---|---|---|
| `RP-02a` vocabulary-is-not-a-gate | **here**, 2026-09-06, across commits `177ca31`→`f065e48` | the only one I can claim |
| `RP-02b` positive controls | ⚑ **`census-kit` skill §5** — *read, not derived*. My four instances are corroboration | RP-04c |
| `RP-02c` stale ≠ fabricated | **here**, `dfcbcc7` — but the *distinction* is `managers/rpm-yum.md`'s own header, written days earlier | I built the tool that couldn't say what my prose already said |
| `RP-02d` `git commit -- <paths>` | ⚑ **`linux-sources-f6`**, `deps-build` §V rev 20 | adopted, not settled here |
| `RP-03b` text-fence exemption | **here**, `f651bdb` | local |

⚑ **Two of five originate outside this repo and one outside every repo on `§R`.** A leg reporting
these as its own would have manufactured two false origins.

## §C Coverage

16 tracked files · 319,377 B · 27 commits, all read. 0 unreadable. **Not searched:** peer legs (embargo); the
27 hook bodies in `§X`'s drift table (I hold none of them and cannot verify that table — I carry it
as the dispatcher's measurement).

## §T Termination (brief §12)

**No** — a reader of my file alone could not reconstruct what was asked of the other legs. ⚑ And my
leg is structurally unable to: **six legs can report what their hooks do; I can only report what
having none costs.** That asymmetry is the point of my seat, and gluing it is the apex's job.

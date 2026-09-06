# `mtools` — deps-build leg

**Written against `CENSUS-deps-build.md` rev 1** (brief `CENSUS-BRIEF.md` rev 1).

## §9 Disclosures — first paragraph, per brief

**I own and authored the entire subject.** Every artifact cited below was written by this session
today. That is not a normal surveyor position and it degrades this leg in a specific way: I cannot
distinguish *"my repo does X"* from *"I decided X eight hours ago and have not yet been wrong about
it."* Where a peer's leg reports a practice with months of load on it, mine reports a decision.

**mtools is the census's own destination.** `§X` names this repo as "the intern table… the
destination this census informs." I am surveying the target of the survey, and my incentive is to
report it as ready. Discount accordingly; I have tried to make the negatives concrete enough to
check.

**My inputs differed from peers', in three ways I can name:**

1. My dispatch was **one line in a peer message**, not the run file. I read `§R`/`§Q` only after
   being pointed at them. No finding here came from that message.
2. I have been in **active finding-traffic with `substrate` and `cassian-observability` all day**,
   before this census existed. Their findings are in my tree, cited, and committed. Per brief §2 this
   is pre-freeze cross-contamination that I cannot undo — it is disclosed per-item below and tagged
   **testimony**.
3. ⚑ **I hold a `§X` fact no leg can infer and one peer may not have:** the operator ruled today that
   *substrate's clean code moves to mtools*, so packages replace symlink/copy vendoring. That ruling
   post-dates most of my tree and is the reason several items below are "designed for, not built."

**Roster nomination (brief §0):** the roster names six surveyors and an apex. I would nominate
nobody new — but I flag that `rosettapkg` is a party I have **never interacted with and cannot see**;
I have no basis to judge roster completeness beyond the five repos I hold paths to. That is a
statement about my reader.

**§12 termination test:** *could a reader of my file alone reconstruct what was asked of the other
legs?* **No.** I surveyed only myself, per `§Q`. Reconstructing the ask is the apex's job.

---

## §10 Coverage, as a population

**Inclusion predicate, stated as inclusions (brief §3):**

```
A  tracked files in mtools @ 16f7f3b                        -> 123
B  git commits, all of them                                 -> 52
C  bazel rule targets, `bazel query kind(rule, //...)`       ->  42
D  peer trees, read-only, for antecedent probe only          ->   4 repos
E  none — no CI system exists; no shape checked carried one
                                                    TOTAL   -> 123 files / 52 commits / 42 targets
```

**Shapes enumerated before filtering (brief §4)**, by extension, over all 123 tracked files:

| shape | n | shape | n | shape | n |
|---|---|---|---|---|---|
| `.py` | 54 | `.toml` | 6 | `.bib` | 3 |
| `.md` | 24 | `.sh` | 6 | `.pyi` | 1 |
| `.txt` | 10 | `.bazel` | 6 | `.lock` | 1 |
| `py.typed` | 3 | `.tsv` | 3 | `.json` | 1 |

plus 5 extensionless: `.gitignore`, `.githooks/pre-commit`, `.bazelversion`, `.bazelrc`, `LICENSE`.

**Unparseable / unread: 0.** Every tracked file is UTF-8 text and was readable. **I make no claim
about the untracked tree** (`.venv`, caches, `bazel-*` symlinks) — deliberately ignored, not
searched, ~99M.

**What I did not search, and why:** peer repos beyond the antecedent probe (`§Q` says survey
yourself); the reflog and stash (no artifact cites them); GitHub (no remote exists).

### ⚑ Antecedent probe (brief §6) — the finding is about my leg, not my repo

Window is UNBOUNDED per `§W`, so the probe is cheap. Every artifact I cite below originates
**today**:

| artifact | first commit |
|---|---|
| `.bazelrc` | 2026-09-05T13:40:46-04:00 |
| `.githooks/pre-commit` | 2026-09-05T14:24:27-04:00 |
| `ratchet/…/core.py` | 2026-09-05T14:37:16-04:00 |
| `findings/bazel/mtools.md` | 2026-09-05T18:32:15-04:00 |

**The whole repo is 8 hours old** (first commit 13:40:46, last 21:39:11, same day).

⚑⚑ **But the ideas are not, and the probe is what surfaces it.** The trees these were derived from:
`substrate` 2026-05-15, `paperkit` 2026-06-22, `cassian-observability` 2026-07-20,
`linux-sources` 2026-08-17. **Every load-bearing design in this leg has an antecedent 3–16 weeks
older than the file that carries it here** — and a reader of my git log alone would date all of it
to today. `MT-01` below is the general form.

---

## Findings

### MT-01 — ⚑ this repo's git history systematically misdates its own designs

**Class: inference**, from the antecedent probe above.

`mtools` was created as a consolidation point, so its files are new by construction while their
content is inherited. `git log` reports authorship dates, and every one of them is today. A future
reader — or an apex — computing origin from this repo's history will attribute to `mtools` designs
that belong to four older trees.

⚑ This is the `§W` justification instantiated in a repo rather than in a query: *a window is a
property of the query; findings inside one are not facts about the subject.* Here the "window" is
the repo's own age, and nothing inside the repo announces it.

**Mitigation in place:** evidence-comments name their origin party in prose. **This is not
machine-readable and no gate checks it.** Unpaid.

### MT-02 — dependency declaration: three-layer, all pinned, one generator (`§Q`-1)

**Class: citation.**

| layer | file | what it names | pinned by |
|---|---|---|---|
| distribution | `<dist>/pyproject.toml` | abstract deps (`dependencies = ["panflute"]`) | nothing — floating by design |
| lock | `<dist>/requirements.txt` | concrete versions | `uv pip compile` |
| module graph | `MODULE.bazel` + `.lock` | `rules_python` 1.0.0, `platforms` 0.0.10 | BCR registry hashes |

Three distributions: `hooks`, `mdstruct`, `ratchet`. Each carries `requirements.txt` **and**
`requirements-dev.txt`. Every lock's line 2 is byte-identical:

> `#    uv pip compile pyproject.toml --output-file requirements.txt`

⚑ **That byte-identity is the verification.** Three locks generated by one spelling of one command;
a hand-edited or differently-generated lock would diverge on line 2. It is checked by eye, **not by
a gate** — an unpaid item, and a cheap one.

`MODULE.bazel.lock` is **tracked deliberately**: registry hashes only, no host paths, so a peer's
first `bazel` invocation cannot silently re-resolve against a live BCR.

### MT-03 — ⚑⚑ dependency discovery is a PERSON, and the implicit set is large and undeclared (`§Q`-2)

**Class: citation** (the measurements) + **inference** (the conclusion).

**There is no import scanner, no manifest reader, no dependency tool.** Discovery is: I read the
code. `linux-sources` has `tools/import_closure.py`; mtools has nothing equivalent. **Absence
reported per §5 below (`MT-11`).**

**The implicit dependency set, measured** — binaries invoked from the 6 `.sh` files and the hook,
by occurrence count:

```
git 13 · realpath 9 · grep 9 · python3 7 · bazel 7 · shellcheck 5
diff 5 · sed 2 · pandoc 1 · kubectl 1
```

**Ten host binaries. Zero of them appear in any manifest.** `pandoc` and `shellcheck` are the
load-bearing ones — real checkers whose absence changes verdicts.

**Three hardcoded absolute paths into a peer repo:**

```
blockers.sh:24                  sub=/home/mikemol/github/substrate
hooks/tests/test_adoption.py:33 _ADOPTER = Path("/home/mikemol/github/substrate")
```

⚑ **A test asserts against a path in another repo.** On a cold machine it does not fail-with-a-
message; it fails as a missing path. This is `§Q`-2's "a file at a fixed path" in its worst form —
the dependency is on *another party's working tree*.

**Three network endpoints** (`.bazelrc`): `grpc://127.0.0.1:31985` (cache + BES),
`http://127.0.0.1:31080` (results), and `:31464` scraped by hand for metrics. Per `§X` these are
shared infrastructure; nothing in my repo declares them as a dependency or degrades gracefully
without them.

### MT-04 — hermeticity: the sandbox is hermetic AND mounts five host directories (`§Q`-4)

**Class: citation.**

```
build --experimental_use_hermetic_linux_sandbox
build --sandbox_add_mount_pair=/bin
build --sandbox_add_mount_pair=/usr
build --sandbox_add_mount_pair=/lib
build --sandbox_add_mount_pair=/lib64
build --sandbox_add_mount_pair=/etc
```

⚑⚑ **This is the honest answer to "what can your build reach that it does not declare": `/usr` and
`/bin`.** That is how `pandoc` and `shellcheck` are found. The flags are **unconditional** (`build`,
not `build:something`) — deliberately, because sandbox flags are *not part of the action cache key*,
so a config-gated hermeticity setting would let a differently-configured peer populate the cache with
verdicts computed under different rules.

**`--remote_local_fallback` is NOT set**, per the `§X` ruling. F-armed: a dead cache endpoint
produces `Failed to query remote execution capabilities: Connection refused` — it refuses rather
than degrading.

⚑ **The gap I have not closed:** `pandoc`/`shellcheck` are host-coupled and should be a toolchain
tier. `.bazelrc` deliberately has no `--stamp`, and adding a stamped toolchain now would either force
a premature `--stamp` or produce an input nothing keys on. **Declared deferred, not solved.**

### MT-05 — build design: every check is an action; 42 targets, 34 tests (`§Q`-5)

**Class: citation.**

```
py_test 24 · sh_test 10 · py_binary 4 · py_library 3 · platform 1     = 42 rules, 34 test targets
```

The design rule is **every gate is a build action with declared inputs**, so ruff, mypy, pytest,
shellcheck, stubtest and the ratchet each have a cache key. Remote cache and BES are **unconditional
`build` lines**, not `--config` — see `MT-09`, which is why.

⚑ **What is NOT cached and why:** nothing is deliberately uncached. The `.bazelrc` has no `-Xmx`
rung and no `--stamp`; both are documented decisions rather than omissions.

**Granularity is the open defect.** 34 test targets cover **192 test functions** — so a test module
is the unit, and 24 `py_test` targets share their keys across many independent propositions.
⚑ **An action's verdict should range over exactly its declared inputs; a module-grained test target
violates that.** I was mid-repair when this census arrived (see `MT-12`).

### MT-06 — ⚑ test design: 192 tests, 192 warrants, enforced 1:1 by the gate (`§Q`-6)

**Class: citation.**

| distribution | test functions | warrants (`@misc{`) | rubric sections |
|---|---|---|---|
| `hooks` | 82 | 82 | 7 |
| `mdstruct` | 75 | 75 | 14 |
| `ratchet` | 35 | 35 | 5 |
| **total** | **192** | **192** | 26 |

**A claim is a BibTeX `@misc` entry; a test is a pytest function; the binding is 1:1 and the
pre-commit hook refuses a mismatch.** A new test without a warrant does not commit. This is the
strongest thing in the repo and it is the one I would ask peers to take.

**Is a test proven falsifiable, or only observed to pass?** ⚑ **Both, and the split is the finding.**
58 test docstrings name an arm explicitly (`F-arm`, `must NOT`, `refuses`), and three modules exist
solely to prove a gate can fail: `hooks/tests/test_bar_fires.py`, `mdstruct/tests/test_verify.py`,
`ratchet/tests/test_core.py`. **The remaining ~134 are observed-to-pass.** I do not have a mechanism
that proves falsifiability for all of them — paperkit's mutation approach is the thing that would,
and I have not built it.

### MT-07 — ⚑⚑ gate design: it has fired, on me, three times today (`§Q`-7)

**Class: citation.** `git config core.hooksPath` → `.githooks`. Installed, not merely present.

The run file asks *"has it ever fired? A gate that has never refused anything is a configuration,
not a gate."* **Yes — and the record is in the commit messages, because I made the gate refuse my own
work three times:**

| commit | what the gate caught |
|---|---|
| `e656485` | the baselines, at mint |
| `4d8120e` | an inline import taken as a PLC0415 escape; two docstring forms; a commented transcript ERA001 could not distinguish from dead code |
| `16f7f3b` | two pure-`partition` tests carrying an unused `tmp_path` fixture copied from neighbours |

⚑ **Every one was repaired at the source; none was waived.** The gate refuses on **missing tools**
rather than skipping:

> `bazel not found — cannot run the hermetic suite, commit refused`
> `$dist/.venv/bin/$tool not found — cannot run the gate, commit refused`

⚑ **That shape is deliberate and is `linux-sources`' contribution** (testimony, relayed today): the
inverse — a gate that self-skips to exit 0 when a tool is absent — is a green indistinguishable from
a non-executing check.

**What the gate reads:** the **staged index** via `git checkout-index`, not the working tree. They
diverge exactly when `git add` is partial, which is the normal case.

### MT-08 — what I re-derived (`§Q`-8) — ⚑ the run file calls this the highest-value item

**Class: citation + testimony.**

**`ratchet/` — 544 lines, 35 tests.** A paydown-only set-membership ratchet with four baseline
states and move detection. **`substrate` already had this**, and I knew it did — I built mine from
substrate's *docstring warning* without reading its code, because at the time its modules were
untracked and could not be depended on.

⚑⚑ **The re-derivation produced a measurable result rather than waste, and both halves matter:**

- **Every classification agrees.** Fan-out, 2-old→2-new reorganisation, and a shared rule at an
  unrelated path partition identically in both implementations — from two derivations sharing no
  author, no corpus and no key grammar (substrate keys `name::path` off a declared schema; mtools
  keys `path:rule` positionally). That is stronger evidence than either suite alone.
- **They differ on exactly one axis, and it is a defect.** Substrate's fan-out defence is a `strict=`
  parameter **defaulting off** — measured by running its own `classify`. Mine is unconditional.
  Substrate has confirmed this and reports that **nothing invokes the reporter at all**, so the
  exposure is zero today (**testimony**, relayed pre-freeze, disclosed).

⚑ **This is a defect report about the shared object, which is what `§Q`-8 says a re-derivation is.**
The mechanism was correct and *unreachable* — untracked, therefore undependable — so a second copy
was cheaper than waiting. **The fix for that class is packaging**, which is the `§X` ruling.

**Also re-derived:** `pytest_main.py` (a `py_test` entry point, because `main = <test module>` runs
the module as a script — measured: 23 targets reported green over zero assertions); `blockers.sh` (a
re-derivation procedure, because a claim with no command attached is never re-checked).

### MT-09 — ⚑⚑ what I declined, and the one I got wrong first (`§Q`-9)

**Class: citation + testimony.**

**Declined with reasons:**

| declined | from | reason |
|---|---|---|
| `SUBSTRATE_RATCHET_WRITE` env-var write switch | substrate | an ambient env var arming a write is "armed while refusing nothing"; `write=` is a required keyword argument here |
| `ratchet_legacy` + its pyproject exemption | substrate | it exists to be deleted |
| 3 shellcheck waivers | substrate | `EXCLUDE={}` is the correct starting state; waivers are measured here, not inherited |
| 3 more shellcheck waivers | cassian | same |
| `check_scratch_runtime.py` | substrate | prints `SKIPPED (no cupy/GPU)` and **exits 0** — the shape is refused, not just the gate |
| pre-commit singleton PID lock | cassian | cassian's own advice: membudget's block/noblock/timeout is strictly better |
| `noqa` line directives in shared code | substrate | a line directive travels with the code; a config entry does not |
| 4 `extend-exclude` entries | linux-sources | they exclude symlinks into another repo — **mtools has no symlinked tools, which is the point of mtools** |
| blanket ruff `--preview` | measured here | 115 findings, 85 of them `DOC201`; a separate decision from the one being made |

⚑⚑ **Declines do NOT union.** The construction rule I adopted: *an `ignore` is not a gate, so taking
the union of rules while also taking the union of exemptions produces something weaker than the
strictest input.* Default: **mtools does not adopt a peer's ignore.**

⚑⚑⚑ **The one I got wrong, disclosed because it is the useful one.** I declined to look for BUILD-file
*generation* on the belief that "Starlark cannot read a Python file to enumerate functions." **That
was an absence claim with no positive control** — it was a statement about where I had looked. The
operator corrected it from outside: the mechanism exists in **all four** peer repos. I was, at that
moment, about to check in a hand-written 38-node-id list. See `MT-12`.

### MT-10 — what binds me (`§Q`-10)

**Class: inference.**

⚑ **Not CPU, not memory, not the executor.** `§X` reports the host binds on CPU (~59.7% stall); my
full suite is 34 targets in **~16s wall**, mostly cache hits. The box is not my constraint.

**What binds me is that nothing outside this repo can depend on anything inside it.** No remote, no
published package, no install path. `hooks` declares a console script
(`mikemol-hook-structural-query`) that **no consumer consumes**. Peers hold my findings as *prose*
and re-implement, which is the exact failure `MT-08` documents from the other side.

⚑ **This is why the operator ruling matters more than any build improvement I could make today:**
packaging is the binding constraint, and every hermeticity or granularity item below it is a
refinement of a thing nobody can import.

---

## §5 Negatives — with positive controls

### MT-11 — no dependency-discovery tool exists in mtools

```
spelling searched : import_closure | closure | gen_build | gen-gate-build | *.bzl | genrule
denominator       : 123 tracked files
shapes read       : all 12 extension classes + 5 extensionless, whole-file
shapes empty      : none — every tracked file is UTF-8 text and decoded
reader            : git ls-files + grep 3.11 + Read (harness)
POSITIVE CONTROL  : the same reader, same spelling, on /home/mikemol/github/linux-sources
                    HITS: tools/import_closure.py, tools/gen_gate_build.py, tools/verb.bzl
```

⚑ **The control fires on a peer corpus the same reader reads**, per brief §5's fallback — proving
reader capability. The absence in mtools is real, not an artifact of my instrument.

### MT-12 — ⚑⚑ no BUILD-file generation exists here, and the absence is NOT benign

Same instrument and control as `MT-11`. **`bazel query kind(rule, //...)` = 42 targets, all
hand-written in 3 `BUILD.bazel` files.**

**Why this is a finding rather than a gap:** 34 test targets cover 192 test functions. Per-case
targets would need node-ids in Starlark, which cannot read Python. **I had already generated a
38-line `tests/CASES.txt` to check in** when the operator stopped me.

⚑⚑⚑ **Measured, and this is the part worth carrying:** `ratchet/tests/` has **35 `^def test_` lines
and collects 38 node-ids** — one parametrized case expands to four. **A list transcribed by reading
the source is wrong on its first day, by three cases, silently.** That is this repo's most-repeated
defect class (a hand-written 5-module blocker list against a population of 32) arriving in the
machinery meant to prevent it.

**Status: uncommitted and abandoned in that form.** `collect_check.sh` (a gate asserting declared ==
collected) is written and unwired. **I hold no verified knowledge of how peers solve this** — what I
have is one subagent's sweep, which is **testimony**, pre-freeze, and which I am not acting on.

### MT-13 — no CI exists

```
spelling searched : .github | .gitlab-ci | Jenkinsfile | .circleci | woodpecker | drone | *.yml | *.yaml
denominator       : 123 tracked files
shapes empty      : ZERO .yml/.yaml files are tracked in this repo at all
reader            : git ls-files
POSITIVE CONTROL  : same reader, same repo, finds 6 .toml and 6 .bazel — it can see config shapes
                    and returns them; and `git ls-files | grep yml` on linux-sources also returns
                    nothing, so this is an ecosystem property, not a mtools gap
```

⚑ **The gate is the pre-commit hook and nothing else.** There is no remote, so there is nowhere for
CI to run. Reported as a fact, not a deficiency — with no remote, CI would be a second local runner.

---

## Testimony held (brief §7) — pre-freeze contamination, disclosed

Per `§9`.3 I was in finding-traffic with two peers before this census existed. **I am not acting on
any of it for this filing**, but it is in my tree and must be declared:

- **`cassian-observability`**: metrics surface is `:31464`; `cquery` reaches the analysis phase so a
  platform question needs no `bazel clean`. **I reproduced the second independently** (rc=0 vs rc=1
  on `//ratchet:test_core`), so my copy is citation; the origin is testimony.
- **`substrate`**: the header census (431/568 conforming); the `strict=`-defaults-off disposition;
  `file_header.py` staged but not committed. **I verified the header figure independently against my
  own gate** — 137 refusals in 568, the exact complement — so that one is corroborated; the rest is
  testimony.
- **A subagent sweep of four peer trees for BUILD generation.** Held, unverified by me, **not used**
  in `MT-12`. Flagged for the apex as an artifact that exists.

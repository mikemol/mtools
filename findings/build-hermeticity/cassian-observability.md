# `CO-` — cassian-observability's leg, build-hermeticity census

**Filed against `CENSUS-build-hermeticity.md` rev 13** (read 2026-09-06 at mtools `0ef83a5`),
per the standing brief `CENSUS-BRIEF.md`. Prefix `CO-`, assigned in `§R`.

⚑ **THIS FILE IS NOT AT THE `§R` PATH, AND THAT IS A CONSTRAINT, NOT A CHOICE.** `§R` requires
`findings/build-hermeticity/cassian-observability.md` **in mtools**. This session holds a standing
operator limit: *"DO NOT WRITE INTO ~/github/mtools — cassian is holding until Ⓒ sets the floor;
mtools-05 owns that sequencing."* So the leg is authored here, in the repo it surveys, and the
dispatcher is told. **A leg at the wrong path is visible; a leg written past a hold is not
recoverable.** Adopt it by copying this file to the `§R` path, or tell me the hold is lifted.

## §9 Disclosures, first

- I **own and authored** the subject under survey. Every mechanism below is mine; none is
  third-party measurement.
- **My inputs differed from peers'.** I was dispatched by two messages (`read the brief and file
  your leg`, then `rev 13 — re-read §W`) rather than by the run file alone, and I had **already
  measured most of `§Q`-1/6/7** four commits earlier for a different purpose
  (`docs/build-census-leg.md`, `◆build-census-leg`, committed `51214d6`). That prior artifact
  exists and predates my reading of the run file; figures here were re-measured today, not copied
  from it.
- **Something I was told that others may not have been:** the operator's two framing quotes
  reached me directly in-session on 2026-09-06 before the run file existed. `§Q` quotes them
  verbatim, so I do not believe this is an asymmetry in content — only in timing.
- ⚑ I have **not** read any peer leg. `§2` binds until the freeze.

## §3 Inclusion predicate — stated as inclusions

```
A  gate driver + selftest driver + both git hooks                    -> 4
B  scripts/check.d/*.sh check slices                                 -> 43
C  projectors on host/projectors.tsv                                 ->  8
D  manifests (pyproject.toml, uv.lock, MODULE.bazel, mise.toml,
   .bazelrc, .bazelversion)                                          ->  6
E  none — no Makefile, no CI config, no Dockerfile (shapes checked,
   found to carry nothing; see CO-09)
                                                    TOTAL            -> 61
```

**Exclusions, counted separately:** `terraform/` (44 `tofu` sites are *invoked by* the gate and
counted in CO-05b, but infrastructure code is not build tooling) · `config/`, `units/`, `docs/`
(subjects of the gate, not the build) · `.git/`, `.venv/`, scratch mirrors.

## §4 Shapes, enumerated before filtering

| shape | count | read? |
|---|---:|---|
| bash driver (`scripts/check`, `check-selftest`, `projector-run`, `gen-playbook`, `gen-migration-dropins`) | 5 | yes |
| bash check-slice fragment (`scripts/check.d/*.sh`) | 43 | yes |
| bash selftest arm (`scripts/selftest.d/*.sh`) | 76 | yes |
| git hook (`.githooks/*`) | 4 | yes |
| python projector | 6 | yes |
| TOML manifest | 4 | yes |
| bazel file (`MODULE.bazel`, `BUILD.bazel`, `tools/*.bzl`) | 4 | yes |
| lockfile (`uv.lock`) | 1 | yes (hash count only; 1.1MB not read line-by-line) |
| **unparseable / unreadable** | **0** | — |

**Zero unreadable items.** Every file in the population above was opened by the reader that
produced its figure.

## CO-01 · `§Q`-1 — what cassian builds with

*Measured 2026-09-06, 16:2x local.*

| system | marker | version | how invoked |
|---|---|---|---|
| bash gate | `scripts/check` | — | `.githooks/pre-commit`, every commit |
| bazel | `MODULE.bazel` | `bazel 8.7.0` | **by hand only** — not in any hook |
| uv | `uv.lock` | `uv 0.11.12` | by hand (`uv sync`, `uv run`) |
| OpenTofu | `terraform/` | — | by hand; gate *reads* plans, never applies |
| make | — | **absent** | — |

⚑ **The gate that actually runs on every commit is bash, not bazel.** `BUILD.bazel` exists, is
freshness-gated, and mirrors the bash roster — but nothing invokes it automatically. That is
`◇19` Commit 1 of 3 (engine alongside the pool); Commits 2 (differential) and 3 (cutover) are
unbuilt. **A repo can hold a complete bazel gate and still have every commit gated by shell.**

## CO-02 · `§Q`-2 — measured off the live process

⚑ **PROBE INVALID for the bazel half, reported as such rather than answered.** `§Q`-2 asks for
`ps -o args=` on a real invocation. cassian's bazel gate is **not invoked by any hook**, so there
is no running bazel process to measure during a commit; producing one means running `//:gate`,
which `§X`'s cost discipline explicitly forbids doing *for the census*
(`1831s → 117s`, shared-fate machine, seven sessions). **Reported unmeasured.**

What I *can* measure off process rather than config, and did: the gate's interpreter resolution
(CO-06), because that is `which -a` plus the invocation strings, not a build.

## CO-03 · `§Q`-3 — work discovery: **DERIVED**, with drift checks, and one that was missing

cassian's work list is **derived**, in the `linux-sources` shape (script → checked-in artifact →
drift gate), and there are **eight** producers, not one.

| producer | input | output | fan-out | drift check |
|---|---|---|---|---|
| `tools/gen-gate-build.py` | `check --list` + `check-selftest --list-arms` | `BUILD.bazel` | 43 claims + 76 arms → **123 targets** | `gate-build-fresh` slice, **in pre-commit** |
| `scripts/gen-playbook` | `host/preparable.tsv` | `ansible/*.yml` | → **24** | `--check`, forward **and ORPHAN** |
| `scripts/gen-migration-dropins` | `host/store-migration.tsv` + `scripts/collectors/` + `units/user/` | `units/user/dropins/*.d/10-store-migration.conf` | 14 pairs → **12** | `--check`, forward **and ORPHAN** ⚑ *backward arm added today* |
| `dashboard/gen-grafana.py` | `dashboard/panels.tsv` | `config/grafana/dashboards/*.json` | → **5** | `--check`, forward **and ORPHAN** ⚑ *backward arm added today* |
| `dashboard/gen-panels-tsv.py` | `dashboard/warrants.bib` | `dashboard/panels.tsv` | → 1 | `--check` (forward) |
| `dashboard/gen-index.py` | `terraform/` | `docs/assets/index.html` | → 1 | `--check` (forward) |
| `dashboard/gen-dashboard.py` | `dashboard/panels.tsv` | `docs/assets/dashboard.html` | → 1 | `--check` (forward) |
| `practice/gen_ledger.py` | `scripts/check` | `docs/assets/ledger.md` | → 1 | `--check` (forward) |

**And the drift check runs in the hook**, not by hand: `.githooks/pre-commit` walks
`host/projectors.tsv`, asks each projector `--sources`, and **regenerates and stages** any whose
declared source is in the commit. Today's commits report `regenerated + staged 1..4 projector
artifact set(s)` — the hook does this on live commits, not in principle.

⚑⚑ **THE FINDING THIS QUESTION SHOULD CARRY, MEASURED TODAY AND NOT PRESENT A WEEK AGO: EVERY ONE
OF THOSE `--check`s WAS ONE-SIDED, AND ONE-SIDED IS THE HALF THAT GOES SILENT.** A projector's
`--check` walked what it *emits* and compared against what is committed — forward only. So when a
**source row vanished**, the generated artifact was never refreshed and never deleted, and the
check stayed green forever. Measured instance: `units/user/dropins/cassian-pg-metrics.service.d/
10-store-migration.conf` was committed at `4e5acfe`, carried the header *"GENERATED — do not
hand-edit"*, and its producer's `--list` had stopped emitting `pg-metrics` (14 pairs, none for
it). **Nothing was broken, which is exactly why nothing reddened.**

⚑ **This is `§X`'s one-sided-population finding independently, in a third substrate.** `§X`
records `rosettapkg`'s `cite-check` comparing `on_disk - covered` and not `covered - on_disk`, and
`mtools-2e`'s unadmitted-artifact check going quiet when admission removed its signal. **cassian
had the same shape in eight projectors and found it from the artifact side rather than the
checker side** — I was not looking for a one-sided check; I was looking at a file that should not
exist. *Three substrates, one shape, each party finding it in their own tree by a different route
and none finding it by reading their checker.*

⚑⚑⚑ **AND THE CENSUS I RAN TO CLOSE THE CLASS EXEMPTED A REAL INSTANCE — the sharper half.**
Having armed one projector, I asked each of the eight how many artifacts it declares, to find
which others could strand one. Answer: only **two** emit a *set* (24, 12), both armed; the other
six declare **one** artifact, where an orphan is impossible. Class closed.

**It was not.** `dashboard/gen-grafana.py` declares exactly one line — `-> config/grafana/
dashboards/` — **and that line is a directory**, holding five dashboards. *I counted declaration
LINES and called them ARTIFACTS.* The census was clean, confident, and asking the wrong key.
**And the grafana residue is worse than the one that opened the class:** the drop-in was inert
(it set a value equal to the default), while **Grafana serves whatever JSON is in that
directory**, so a dashboard stranded by removing a group keeps rendering panels from a projection
nothing regenerates. Fixed same-day; three set-emitting projectors, three armed.

**Take-away offered to the fleet:** *a one-sided check is a known class now; the harder problem
is the census that decides which subjects the class applies to.* Mine was wrong on the first run,
in the safe-looking direction.

## CO-04 · `§Q`-4 — specificity: the claim, and what it costs

**Grain: the CLAIM** — 43 of them, each a named slice with its own verdict line and its own
`--only <claim>` entry point.

| level | count | what it would mean |
|---|---:|---|
| coarser | **1** | one `scripts/check`; a red says "something drifted" |
| **chosen** | **43** | claim; a red names the subject and the tier that owns it |
| finer | **123** | bazel targets (43 claims + 76 selftest arms + 4) |
| finer still | ~**330** | individual assertions inside arms |

**What the choice costs, stated rather than implied:** a claim is coarse enough that
`--only pressure` re-runs *every* PSI horizon to answer one question, and fine enough that
`--only` is a real bisect tool (43 entry points, and `--only <unknown>` exits 2 rather than
falling back to a full run — measured, T9).

⚑ **The cost I actually paid, twice, is at the FINER grain and it is not a performance cost.**
Writing a selftest arm does **not** enrol it: `scripts/check-selftest`'s `ARMS` array does, and
the `PROVENANCE` block declares it, and **neither implies the other**. T133 was authored,
reported as passing, and was absent from `--list-arms` and from every full-suite run between its
commit and its discovery. A `--only tN` verification tests the **arm** and never its
**enrolment**, and the two look identical in the output. **At a fine grain, the roster becomes a
second artifact that can disagree with the population it names** — which is `§Q`-3's drift
question reappearing one level down, inside the test suite.

## CO-05 · `§Q`-5 — cross-repo edges, both directions

**CONSUME:**

| from | what | declared or ambient |
|---|---|---|
| `substrate` | 4 harness hooks (`hook_structural_query`, `hook_no_chaining`, `hook_shellcheck`, `hook_cmdparse`) | ⚑ **VENDORED as real files, not symlinks** — gated by the `routes` claim, which verifies each is a real local file and reports `VENDOR-STALE` on divergence **as a REPORT, not a failure** |
| `substrate` | `substrate-tooling` package (mdstruct/bibstruct/pycodemod) | **DECLARED** — `[tool.uv.sources] substrate-tooling = { path = "../substrate", editable = true }`, added `8e8f5ae` |
| `mat260` (via substrate) | `absence_audit.py` | **held as code**, gated |
| `paperkit` | the docs compiler, invoked as a CLI by `scripts/docs` | ⚑ **AMBIENT** — resolved as a sibling directory; no manifest names it |

⚑ **The vendoring decision is a `§Q`-9 answer too, and the reason is in the verdict string:** a
red on vendor-staleness *"would make cassian's board hostage to substrate's commits, the exact
coupling vendoring removes."* Four hooks currently report `VENDOR-STALE` and the board is green —
deliberately.

**EMIT — the direction `§Q`-5 says nobody records, and I could not have answered it a week ago:**

| to | what | declared or ambient |
|---|---|---|
| `paperkit` | bug reports via `~/github/paperkit/inbox/` — drove paperkit's `0da3d28` emit fix | **AMBIENT** (a directory drop) |
| `summit` | 14 registry entries (4 services + 10 capabilities), one floor use-case entry that a peer `rests-on` | **DECLARED** in summit's registry |
| `mtools` | ⚑ **this leg**, and the census-kit measurements | ambient — and see the header |
| the fleet | quoted measurements peers cite in their own findings (four-repo interpreter table, the layer-conflation finding) | ⚑ **AMBIENT and invisible from here** — I learned of these only because peers told me |

⚑⚑ **`§Q`-5's claim that the emit direction is unrecorded holds against my tree, and I can date
when it stopped being invisible: today.** Two peer sessions told me my measurements had been
filed into *their* ledgers (`gate-G76`, `gate-G77`, `gate-G79`). **Nothing in cassian records that
those edges exist.** A census of cassian's declared dependencies sees zero of them.

## CO-05b · `§Q`-5b — invoked executables

*Measured 2026-09-06 over 47 gate files (drivers, 43 check slices, both hooks).*

| binary | sites | on PATH | declared in any manifest |
|---|---:|---|---|
| `git` | 106 | yes | **NO** |
| `tofu` | 44 | yes | **NO** |
| `bazel` | 25 | yes | **NO** |
| `shellcheck` | 16 | yes | **NO** |
| `systemctl` | 16 | yes | **NO** |
| `curl` | 14 | yes | **NO** |
| `conftest` | 14 | yes | **NO** |
| `podman` | 8 | yes | **NO** |
| `kubectl` | 5 | yes | **NO** |
| `smartctl` | 2 | yes | **NO** |
| **total** | **250** | | **0 declared** |

⚑ **Eleven binaries, 250 invocation sites, zero declared anywhere a resolver reads.**
`pyproject.toml` declares Python packages only. `§Q`-5b's prediction — *an import-resolvability
predicate scores a repo clean while its gate shells out to undeclared binaries* — **holds exactly
here**: cassian's import story is now clean (`8e8f5ae`) and its binary story is entirely ambient.

⚑⚑ **And `§Q`-5b's sharpest instance applies to me verbatim.** `.claude/skills/struct-tools/
SKILL.md` is read **at call time** by the structural-query hook and names owning tools by path;
it refused three of my commands this session and named `uv run python scripts/mdstruct.py` as the
owner of `.md`. **A dependency artifact wearing policy's clothes**, in this tree too.

## CO-06 · `§Q`-6 — interpreter: **AMBIENT**, and pinned three ways

*Measured 2026-09-06.*

| where | value |
|---|---|
| `pyproject.toml` `requires-python` | `>=3.13` |
| `MODULE.bazel` `python_version` | `3.13`, `is_default = True` |
| `mise.toml` | `3.13` |
| **resolved** | `/home/mikemol/github/cassian-observability/.venv/bin/python3` · **3.13.11** |

```
which -a python3
  /home/mikemol/github/cassian-observability/.venv/bin/python3     <- wins
  /home/mikemol/.local/share/mise/installs/python/3.13/bin/python3
  /home/mikemol/.local/share/mise/shims/python3
  /usr/bin/python3
  /bin/python3
```

**Four resolutions, and my tooling depends on the ordering.** The venv wins *because mise
activated it in this shell*; in a shell where it did not, the gate runs under `/usr/bin/python3`.

**Per hook, gate and build step — does it name an interpreter?**

```
.githooks/pre-commit   : python3 -> 0 sites,  uv run -> 0     (names none; delegates to scripts/)
.githooks/commit-msg   : python3 -> 0 sites,  uv run -> 0     (control: file is 395 lines, reader works)
scripts/check          : python3 -> 0 sites
scripts/check-selftest : python3 -> 5 sites,  uv run -> 0
scripts/projector-run  : python3 -> 1 site (env --chdir=$REPO python3 "$REPO/$proj")
```

⚑ **Six bare `python3` invocations, zero `uv run`, and NO CHECK COMPARES RESOLVED TO PINNED.**
Three manifests state 3.13 and none is read by the thing that runs. **cassian is
bare-python-lucky rather than bare-python-dead** — worse than the dead case in one respect,
because it currently works and nothing measures the difference.

⚑⚑ **This is the same defect `§X` records in the dispatcher's own tree, minus the crash.**
`linux-sources`' hooks derive the wrong root and survive on a copied wheel; cassian's gate names
no interpreter and survives on PATH ordering. **Different mechanism, same predicate: the question
"which interpreter ran this gate" is unaskable from inside the gate.** And a hook census — which
I ran — reports *which hooks*, never *which interpreter*.

## CO-07 · `§Q`-7 — the `.venv`: a thing made once, and the lock axis split

| property | cassian |
|---|---|
| interpreter version pinned | `>=3.13` (pyproject) / `3.13` (mise, MODULE.bazel) ⚑ **MINOR, not patch** |
| dependency **set** pinned | `uv.lock`, tracked |
| dependency **content** pinned | ⚑ **YES — 1532 `sha256` hashes** |
| lock is build key material | ⚑ **NO** — the gate is bash; `uv.lock` is an input to nothing |
| lock **freshness gated** | ⚑⚑ **NO** — `grep -c uv .githooks/pre-commit` → **0** *(control: same reader returns 395 lines on that file and 1532 on `uv.lock`, so the zero is real)* |
| `.venv` reproducible from manifest | yes in principle (`uv sync`) |
| `.venv` **produced by a build rule** | ⚑⚑⚑ **NO** |
| `.venv` **verified by the gate** | ⚑⚑⚑ **NO** |

**cassian sits exactly where `§X` puts `linux-sources`: contents cryptographically pinned,
interpreter pinned only to a minor version, freshness ungated.** Independently reached — I
measured this at `51214d6` before reading the run file, and the agreement is convergence on a
shared tool (`uv`), not on a shared insight.

⚑ **The `.venv` is a thing I made once.** Nothing in `.githooks/` or `BUILD.bazel` produces or
verifies it; the gate runs *inside* it having never asserted what it is.

⚑⚑ **AND I HAVE NOT RUN `uv sync` TO "FIX" THIS, DELIBERATELY, BECAUSE `§X` CARRIES THE
REFUTATION.** summit's sync swept 95 undeclared packages including two load-bearing ones and went
green *by subtraction*. cassian's venv holds ~113 packages pulled in by declaring
`substrate-tooling`; a sync-to-green here would be the same experiment with the same hazard.
**Reported as a known-unsafe repair, not attempted.**

## CO-08 · `§Q`-8 — what is hermetic, and what fired

**Declared** in `tools/verb.bzl`, a three-tier ladder adopted from linux-sources (from paperkit):

| tier | cached | sandboxed | remote |
|---|---|---|---|
| `sandbox` | yes | yes | eligible |
| `local` | **no** | no | **no** |
| `toolchain` | yes | host-coupled | eligible |

Execution requirements actually declared: `no-cache`, `no-remote`, `no-sandbox`.
**`requires-network` is absent** — a fact about the roster, not a claim that nothing reaches the
network (14 `curl` sites say otherwise; they live in `local`-tier probes).

⚑ **What I would offer the fleet: `local` carries `no-cache` AND `no-remote` TOGETHER**, because
caching a verdict that read the live host and shipping a host-probe to a remote executor are
*the same defect wearing two coats* — both bank a reading of a world the cache or the executor
cannot see. That coupling is what makes cassian's RBE sound where `§X` reports linux-sources
declining remote on every tier.

**What has actually fired — and this is where the honest answer is short.** The checks that fire
constantly are the *gate's* checks, not hermeticity checks: today alone, the pre-commit refused a
half-open dart edge, `PROV-MISSING` on an unenrolled arm, `PROV-SHIPPED` on a witness that was
prose rather than bytes, `NO-DEFINITION` on a row citing a file I had deleted, and
`GATE-BUILD-STALE` on an unregenerated roster. ⚑ **But I cannot name a check that would go red if
*hermeticity* broke and say it has fired, because the sandboxed path is not on the commit
path.** `//:gate` exists; nothing runs it automatically. **`§X`'s finding that the hermetic arm
sees what the local one cannot is precisely the evidence I do not have for my own tree** — and
`◇19` Commit 2, the differential that would produce it, is unbuilt.

**Answer: hermeticity here is DECLARED, not PROVEN.**

## CO-09 · `§Q`-9 — solved, and declined

**SOLVED — offered, each with the measurement that made me trust it:**

1. **Regenerate-and-stage in the hook.** The projector roster is walked on every commit and stale
   artifacts are regenerated *and staged*, so a commit cannot land with a stale projection.
   Trusted because live commits print `regenerated + staged N projector artifact set(s)` and
   because removing it reddens `gate-build-fresh`.
2. **The two-sided projector `--check`** (CO-03), and more usefully **the finding that the census
   deciding where to apply it is the hard part**.
3. **The `local` tier coupling `no-cache` + `no-remote`** (CO-08) — the reason cassian's RBE is
   sound.
4. **`.githooks/commit-msg` binding asserted numbers to measurements.** A commit message may not
   assert a count the run did not produce; four-space-indented lines are exempt so a message can
   quote a transcript. ⚑ *A claim about a number a command emitted is not prose — it is a
   measurement restated at a consumer site.*
5. **Four-state verdicts.** pass / fail / **cannot-run (exit 2)** / **not-asked (exit 4)**. Built
   because `count-gate-inversion` reads gitignored terraform state, absent from the materialized
   index *by design*: a check that can never answer in the gate is not a gate check, and
   reporting clean with no state substitutes *"cannot evaluate"* for *"nothing wrong."*

**DECLINED — with the `HELD` / `UNEXAMINED` split `§Q`-9 requires:**

| declined | state | reason |
|---|---|---|
| bazel as the **commit gate** | ⚑ **HELD** | the differential proving bazel == pool is unbuilt (`◇19` Commit 2); cutting over first would trust an unproven equivalence |
| `uv sync` to close the undeclared-package gap | ⚑ **HELD** | `§X`'s summit result: green by subtraction, non-reproducible rebuild |
| a `sys.path` shim to make substrate's `mdstruct` resolve | ⚑ **HELD** | *"adding a shim here would be the tomfoolery being retired, applied to conceal its own last instance"* — reported upstream instead |
| **declaring the 11 invoked binaries** | ⚑⚑ **UNEXAMINED** | I never compared. CO-05b is the first time I counted them. `§Q`-5b is why this row exists — I would have filed a clean import story and not noticed |
| **timeout discipline on bazel** | ⚑ **UNEXAMINED until today** | `§X` carries the never-timeout instruction; I hold no measurement of my own and had no practice either way |
| `requires-network` declarations | ⚑ **UNEXAMINED** | 14 `curl` sites, none declaring network need; I had not asked the question |

## `§0` Roster nomination

**`memory-concepts` should be on the roster and is in the "no session, active" tier** — I hit it
today from the consuming side, which is the evidence `§R` says nomination needs. Attempting to
record a finding as a session memory, I found `MEMORY.md` states it is **projected from
`memory-concepts/warrants.bib`** and must not be hand-edited, with the generator at
`~/github/memory-concepts/gen_index.py`. ⚑ **That is a `§Q`-3 DERIVED work-discovery mechanism
with a `--check` drift gate, in a repo `§R` lists as unregistered with summit** — and its
docstring already names the shape: *"it was hand-maintained and drifted … this makes it a
PROJECTION instead."* **What it holds:** a bib→index projector, a byte-compare freshness gate,
and an explicit two-property split between *the projection is deterministic* (gateable there) and
*the deployed copy in `~/.claude` is stale* (**deliberately not gated**, because a gate reaching
into a tree it does not own would assert a property of a tree that changes between sessions by
design). That last distinction is a `§Q`-8 answer nobody on `§R` has, and I only saw it because I
tried to write a file it owns.

## `§6` Antecedent probe

Every artifact I cite was created **inside** the window (open, no deadline) except:

- `tools/verb.bzl`, `MODULE.bazel`, `.bazelrc` — the bazel gate, ported before this window.
  ⚑ **Load-bearing and outside**: CO-08's tier ladder is my main `§Q`-8 offer and predates the
  census.
- `.githooks/commit-msg` (`A51`), the four-state verdict work, the vendored hooks — all before
  the window, all load-bearing in CO-09.
- `docs/build-census-leg.md` (`51214d6`, today) — **inside** the window but **before I read the
  run file**, which is the disclosure in `§9`.

## `§10` Coverage, as a population

- **Files read:** 61 (the `§3` total), plus 76 selftest arm fragments consulted for CO-04.
- **Records per shape:** in `§4`.
- **Unparseable/unreadable:** **0**.
- **Not searched, and why:** `terraform/*.tf` beyond binary-invocation counting (infrastructure,
  not build tooling — a scoping choice, stated so a reader can disagree); `uv.lock` line-by-line
  (1.1MB; I counted `sha256` occurrences and did not read entries); `.venv/` contents (~113
  packages, not enumerated — CO-07 reports the count from the install, not from a tree walk).
- **Not measured, deliberately:** `§Q`-2's `ps -o args=` on a bazel invocation (CO-02, PROBE
  INVALID under `§X`'s cost rule).

## `§12` Termination test

**No — a reader of this file alone could not reconstruct what was asked of the other legs.**
`§R` names eight live parties, twelve no-session repos and an unrecorded retired set; this file
answers for **one** of them and deliberately does not read the others (`§2`). ⚑ Worse, my own
`§Q`-3 answer contains a census that exempted a real instance by counting the wrong key — **which
is direct evidence that a leg's self-assessment of its own coverage is the thing least worth
trusting in it.** That is the apex's job, and CO-03's exemption is offered as calibration for how
much to trust the rest of this file.

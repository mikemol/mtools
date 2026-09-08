brief:            CENSUS-BRIEF.md rev 1
run:              CENSUS-deps-build.md rev 6  (drafted against rev 1; re-read at rev 6 before filing — §V 2,3,4,5,6 all land on this leg)
surveyor:         rosettapkg            prefix: RP-
corpus:           8 files · 126,645 bytes · 6 commits (8a5fb1f..5c198a4) · all read in full
reader:           GNU grep 3.11 / find (findutils) / git 2.x / python3 3.13.11 (mise) — shell tools, no parser
reader-blind:     binary/compressed members (I read no .sqfs interiors); anything outside the git worktree.
                  ⚑ One self-inflicted blindness FOUND AND CORRECTED before filing: a `-maxdepth 3` bound
                  made me report a failed CI-shape control that was not failed. See RP-N3.
positive-control: manifest-shape → ~/github/linux-sources/MODULE.bazel ✓ ; python-import-shape →
                  linux_sources/corpus_fetch.py:32 `import hashlib` ✓ ; hook-shape →
                  ~/github/linux-sources/.claude/hooks/corpus-memory.py ✓ ; CI-workflow-shape →
                  ~/github/earley/.github/workflows/ci.yml ✓ (all four obtained; none failed)
unreadable:       0, none encountered; nothing unclaimed
disclosure:       ⚑ I authored part of the subject. See §D below — four asymmetries, one of them a vantage boundary inside this same session.
window:           UNBOUNDED, per §W. Antecedent probe run on every cited artifact (§A).
roster-nomination:⚑ **NONE — my intended nomination was already on the roster.** I drafted against rev 1 and
                  read `substrate` as absent from §R; it is present (§R line 15) and has filed. Recorded as a
                  read error of mine, not a roster gap. I nominate no party §R lacks. Separately: `linux-sources`
                  IS on §R but holds *my* dependency machinery — witness supplied at RP-W1 so the apex need not guess.
not-searched:     peer filings under findings/deps-build/ (brief §2 forbids before freeze; the directory was
                  empty when I began) · the 30 mounted .sqfs corpora themselves (cited BY rosettapkg, but they
                  are `linux-sources`' population, not mine) · rosettapkg's GitHub remote (created this session, no CI)

---

# rosettapkg — `deps-build` leg

## §D Disclosures (brief §9)

1. **I authored part of the subject under survey.** This same session published rosettapkg to GitHub
   (private) and delivered an opinion review of it earlier in this conversation. I am not a neutral
   reader of this repo.
2. **My dispatch differed in TIMING, and the run file says so at §V rev 2.** It arrived as a
   cross-session message from `linux-sources-d2`, not from the user, reading in part: *"Census run: read
   `~/github/mtools/findings/CENSUS-deps-build.md` and the brief it names, then file your leg."*
   [class: **citation**, cross-session message, this session]. My draft recorded suspected *content*
   drift; ⚑ **§V rev 2 resolves that and I defer to it** — *"`rosettapkg` dispatched later than the
   other five — no session existed at rev 1. **Byte-identical message, no substitution.**"*
   [class: **citation**, `CENSUS-deps-build.md` §V rev 2]. So: no content asymmetry, a real clock
   asymmetry. ⚑ **The measurable consequence is visible in this very file** — I drafted against rev 1
   and had to absorb five revisions before filing, four of which (§Y, §Z, §F, §N) are substantive and
   two of which (§Y, §Z) changed my findings. A leg dispatched at rev 1 wrote against a stationary
   brief; I did not.
3. ⚑ **Peer filings appeared while I drafted, and I did not read them.** When I began,
   `findings/deps-build/` was empty. On writing my file I found four peer legs present. Per brief §2 I
   opened none of them; I read only **file metadata** (names, sizes, mtimes) and the run file's own §R,
   §V, §Y, §Z, §N — the last four being dispatcher-authored sections that §V explicitly binds legs to,
   not peer findings. ⚑ **Two exceptions I must declare, because the run file quotes peers inside
   dispatcher sections:** §Y contains `mtools`' self-report and §N contains `linux-sources`' `LS-30`
   nominations. I read those *as they appear in the run file*, could not avoid doing so while reading
   the revisions binding on me, and treat them as **testimony via the dispatcher**, not as peer legs.
   They changed my §A and my roster-nomination line. This is disclosed rather than concealed because a
   reader comparing my filing to `LS-30` would otherwise find unexplained correlation.

4. ⚑ **A vantage boundary inside this session** (census-kit §B5). I read `README.md` and
   `lattice/pm-depsort.py` earlier in this conversation and formed conclusions about them. Between that
   read and this survey the working tree changed: `lattice/AUDIT.md` appeared, `pm-depsort.py` gained a
   `status_gate` knob, a `FUNCWHY` claim, and a space-manifest fingerprint (`S_8883c16a47cf`, 10 knobs /
   12 claims). **My earlier reading is testimony about a tree that no longer exists, not citation.**
   Everything below is re-read from the artifact. Where my earlier opinion and the current artifact
   conflict, the artifact wins and I say so (RP-08).

## §Q1 Dependency declaration — RP-01

**There is no dependency manifest of any kind.** No `pyproject.toml`, `requirements.txt`, `uv.lock`,
`MODULE.bazel`, `Makefile`, or `mise.toml`. Negative filed at RP-N1 with control.

What exists instead: **versions declared in prose, one per manager entry, in the entry's own header.**

> **Re-verified against `pacman v7.0.0` (git `138cbae58448`, libalpm 15.0.0)**, held in the pinned
> corpus — `linux_sources/corpora show pacman <path> <needle>`.

[class: **citation** — `managers/pacman.md:3-4`]

⚑ These prose pins are **real content-addressed pins**, not approximations — see RP-W1. The defect is
not the pinning; it is that the pin lives in a sentence that nothing can read.

## §Q2 Dependency discovery — RP-02

**A person, by eye.** There is no import scanner, no manifest reader, no tool. The mechanism by which
rosettapkg learns what it depends on is: an author opens `~/github/linux-sources/corpora.tsv` and reads
a row.

**Implicit dependencies — none of them named by any file in this repo** (§Q2's ⚑ item):

| implicit dep | evidence | class |
|---|---|---|
| `python3` ≥3.13 | `lattice/pm-depsort.py:1` `#!/usr/bin/env python3`; resolves to `/home/mikemol/.local/share/mise/installs/python/3.13/bin/python3` on this box | citation + inference |
| `~/github/linux-sources` **at that literal path** | `managers/pacman.md:4` invokes `linux_sources/corpora …` with no repo qualifier | citation |
| 30 live squashfs **mounts** | `mount` piped to `grep -c squashfs` → `30`; the corpora are mounts, not files in any repo | citation (machine) |
| `~/github/substrate` | `lattice/pm-depsort.py:6` names the ported original by path | citation |
| ⚑ **another repo's uv environment** | see RP-03 | citation |

## §Q3 Dependency acquisition — RP-03

**rosettapkg acquires nothing.** It vendors nothing, fetches nothing, has no lockfile and no fetch step.
Acquisition happens entirely in `linux-sources`, via `linux_sources/corpus_fetch.py`, whose own docstring
states the design:

> ⚑ AND THE REGISTRY'S DISTINCTION IS PRESERVED, NOT SMOOTHED. `ref` is WHAT WAS ASKED FOR and
> `revision` is WHAT WAS RECEIVED — a tag is a name and can move; a commit is a record.

[class: **citation** — `~/github/linux-sources/linux_sources/corpus_fetch.py:14-16`]

⚑ **RP-03a — the read path requires an environment rosettapkg does not name.** `managers/pacman.md:4`
tells a reader to run `linux_sources/corpora show …`. Measured:

```
$ python3 ~/github/linux-sources/linux_sources/corpora_lib/cli.py --help
ModuleNotFoundError: No module named 'PySquashfsImage'
$ cd ~/github/linux-sources && uv run python linux_sources/corpora list
name       ref          revision           image  store
systemd    259.5-0ubuntu3.4 md5:6ac65dfb      16.8MB  systemd-sources
...                                                    (exit 0)
```
[class: **citation**, measured this session]

The dependency **is** declared and locked — `~/github/linux-sources/uv.lock:2068` pins
`PySquashfsImage-0.9.0` with a sha256 — but in the *other* repo. rosettapkg records the invocation and
not the environment, so the instruction as written fails on a bare interpreter.

**Cold machine:** zero of the four manager entries are re-verifiable. Every citation resolves through a
mount that a fresh checkout of rosettapkg does not create, cannot create, and does not mention.

## §Q4 Hermeticity — RP-04

⚑ **The two halves of this repo have opposite hermeticity, and nothing marks the seam.**

- `lattice/pm-depsort.py` is **fully hermetic**: stdlib only (`sys`, `typing`, and a function-local
  `hashlib`), no file I/O, no network, output to stdout. Denominator: 1 of 1 `.py` files, all imports
  enumerated at RP-N2. Its result depends on nothing outside its own source.
- The **prose entries are maximally non-hermetic**: every claim reaches into a mounted corpus, and the
  reach is undeclared (RP-02).

⚑ **This is §Q4's "gate that passes by not running" in its purest form.** The hermetic half is the half
with no external claims to check; the half making 100% of the factual claims has no gate at all (RP-07).
A reader who runs the script and sees `all P: True` has verified the model's internal consistency and
**nothing whatsoever** about whether a single quoted byte still exists upstream.

## §Q5 Build design — RP-05

**There is no build.** One command, no arguments, no graph, no tiers, no cache:

```
$ python3 lattice/pm-depsort.py     # ~instant, stdlib only
SPACE MANIFEST  S_8883c16a47cf   (10 knobs, 12 claims)
```
[class: **citation**, measured this session]

Nothing is cached **because nothing is expensive** — that is the honest "why not" §Q5 asks for, and it
is a real answer rather than an omission.

⚑ **Not on the shared executor.** Per §X, "Some parties are on this config and some are not; that
difference is a finding, not an error to hide." rosettapkg is **not** on BuildBuddy, has no `.bazelrc`,
and has never contacted `grpc://127.0.0.1:31985`. It is also unaffected by the degraded scheduler §X
describes. Reported as the finding §X asks for, not concealed.

## §Q6 Test design — RP-06

**No test framework, no test directory, no assertion library** — and yet a falsifiability discipline
exists. This is an unusual shape and I state it precisely rather than filing "no tests."

What plays the role of a test is a **self-check on the instrument**:

> Every claim must show `P` on BASE (the header line asserts `all P: True`); a claim that does not is a
> modelling error, not a finding.

[class: **citation** — `lattice/FINDINGS.md:108-110`]

⚑ **What binds a claim to a test here is the break-matrix, and it is genuinely falsifiable**: each
capability declares a characteristic break, and the 12×12 matrix printed each run is a refutable
prediction — if `B` stayed `P` under `break(A)`, the presupposition edge would be *observed absent*.
So the model's *internal* claims are proven falsifiable and are observed to pass.

⚑⚑ **But the entries' claims about the world are neither.** No mechanism binds "`add.c:365-381` contains
this branch" to anything executable. The repo has a **proof discipline over its model and no test
discipline over its evidence** — and RP-07 is the consequence.

## §Q7 Gate design — RP-07

**Nothing refuses. There is no pre-commit hook, no CI, no selftest, no gate of any kind.** Negative at
RP-N3 (⚑ with a *failed* control — read it).

Per §Q7's ⚑ — *"Has it ever fired? A gate that has never refused anything is a configuration, not a
gate"* — rosettapkg does not even reach the configuration tier. There is nothing to fire.

⚑ **And the drift a gate would have caught has already happened, twice, in this repo's own history.**
Both are recorded by the repo against itself:

> ⚑ **THIS ENTRY WAS WRITTEN AGAINST A DIFFERENT VERSION THAN THE ONE THAT CAN CHECK IT.** It declared
> `pacman 7.1.0 / libalpm 16.0.1` at git `a6f7467d` (2026-01-25), from a clone that was discarded.

[class: **citation** — `managers/pacman.md:7-9`]

> **and one code block was a PARAPHRASE PRESENTED AS A QUOTE** — corrected.

[class: **citation** — `README.md:47`]

⚑ A paraphrase presented as a quote is precisely the failure a byte-level gate exists to prevent, and it
survived until a human re-read the entry. The repo's response was to invent a **three-state vocabulary**
in prose — `re-verified` / `located` / `pending` (`README.md:41-45`) — which is an honest and
well-reasoned mitigation **that no machine reads**. Stated as a §Q7 finding, not a recommendation:
naming residue is this filing's job; spending it is a separate act.

## §Q8 What was re-derived — RP-08 ⚑ (the census's highest-value item)

**RP-08a — a verified lockfile, re-derived as prose.** This is the leg's central finding; witness at RP-W1.
`linux-sources/corpora.tsv` is a content-addressed registry with resolved commit revisions, maintained by
a tool that separates ref-asked-for from revision-received. rosettapkg's four manager entries pin against
that registry **by hand-copying hex into sentences**, and name the registry nowhere. A lockfile existed;
a lockfile was re-derived, in a format nothing can verify.

**RP-08b — el-atlas's depsort mechanism, ported rather than imported.**

> A faithful port of substrate/el-atlas/tools/el-atlas-depsort.py to the package-manager
> install-lifecycle domain. The el-atlas MECHANISM is reused verbatim

[class: **citation** — `lattice/pm-depsort.py:6-7`]

⚑ Per census-kit §B4 I do **not** treat this as a duplicate to be collapsed. Two implementations are two
witnesses; what would be needed to merge them is a statement of whether the domain-specific claim set is
separable from the SCC/layer machinery — which nobody has written down. Recorded, not quotiented.

**RP-08c — a space-manifest + fingerprint discipline, re-implemented locally.**

> **Standing requirement adopted for this repo, from el-atlas v3.1:** every lattice run must print a
> **space manifest** (knobs + value sets) and a **fingerprint**

[class: **citation** — `lattice/AUDIT.md:163`]

Adopted from el-atlas and implemented independently in `pm-depsort.py:460-480` (a local `import hashlib`).
Third re-derivation of the same neighbour's work in one small repo.

**RP-08d — ⚑ my own earlier review re-derived two conclusions the repo already held.** Earlier this
session I told the user that `FUNCWHY` looked like a missing capability and that BASE-as-maximal needed
its reference arm stated. `lattice/AUDIT.md` had **already** reached both, and reached the first one more
sharply — reclassifying `FUNCWHY` from a missing *knob* to a missing *claim*, "a strictly cheaper closure
that FINDINGS.md's framing would have paid for with an unnecessary re-grounding." Filed as a re-derivation
because it is one, and because it is evidence that this repo's findings are not discoverable even to a
reader inside the same session (see RP-10).

## §Q9 What was declined — RP-09

**el-atlas's own v3.x successor line, declined with a stated reason** — the one decline here that is
properly recorded, and therefore a design constraint rather than fragmentation:

> The el-atlas ORIGINAL is the correct base: its v3.x successors deleted the dep-matrix/SCC/layer
> machinery in favour of a separator search over the full knob cube.

[class: **citation** — `lattice/pm-depsort.py:19-21`]

⚑ Note the asymmetry worth carrying: rosettapkg declined el-atlas v3.x's *architecture* while adopting
el-atlas v3.1's *manifest discipline* (RP-08c). A partial adoption with a recorded reason on one half and
silence on the other.

**Declined without a recorded reason** (fragmentation, by the skill's definition): the BuildBuddy
executor, `membudget`, `mtools` packaging, and `linux-sources`' `corpora` reader as a declared dependency.
⚑ I flag these as *undocumented declines* rather than *rejections* — I can find no record of anyone
considering and refusing them, which is different from refusing them.

## §Q10 What binds — RP-10

**Not CPU.** §X states the host's binding constraint is CPU (~59.7% stall). That measures the box, and
§X warns a per-repo answer is a measurement of the box rather than the repo. rosettapkg's entire compute
is one instant stdlib script; host CPU pressure does not reach it.

**The binding constraint is corpus read time — a human reading source through a mount.** One manager
entry costs one careful source read; the four entries are the output of four such reads, and the two
re-verification commits (`31b46e4`, `5c198a4`) are the cost of *re-*reading when pins drifted.

⚑ **The second-order binder, and the one I'd name if only one:** every finding in this repo is
undiscoverable from outside it. `AUDIT.md`'s residues, the three-state citation vocabulary, and the
`FUNCWHY`-is-a-claim correction are all real results that exist only as prose in a private repo — which
is why RP-08d happened *inside the same session*. Throughput is limited less by reading speed than by
the absence of any channel by which what this repo learns reaches the parties re-deriving it.

## §W1 Witness for the apex — RP-W1

⚑ Supplied so the apex need not guess an identification (census-kit §3: an identification with no witness
is the apex's convenience). **Witness type: byte-identity of quoted text, both sides.**

| hash | rosettapkg | linux-sources |
|---|---|---|
| `c8dc5ea575a2` | `managers/rpm-yum.md:3` | `corpora.tsv:70` → `…e9c1488036d12f4b75f6a5a49120` |
| `138cbae58448` | `managers/pacman.md:3` | `corpora.tsv:71` → `…b7fde90335526add3029875784ee` |
| `3da5d7434be3` | `managers/portage.md:3` | `corpora.tsv:78` → `…a4005bba96dff425dd330f12deeb` |
| `2c73b59da296` | `lattice/AUDIT.md:126`, `pm-depsort.py:49` | `corpora.tsv:69` → `…06068c0c98db015dd3a66955525d` |

Four for four; rosettapkg quotes a 12-char prefix of the registry's 40-char revision in every case.
**This identification is warranted.** ⚑ Two hashes that do **not** appear in `corpora.tsv` and must not
be glued to it: `a6f7467d` and `bd454e2c` — both from the discarded clone, and both explicitly marked by
rosettapkg as superseded coordinates (`managers/pacman.md:8`, `managers/rpm-yum.md:7`).

## §A Antecedent probe (brief §6, unbounded per §W) — ⚑ corrected under §Y

⚑ **§Y caught a defect in my draft's probe and I re-ran it.** My draft dated el-atlas's depsort to
`f374068cc3a1` (2026-06-17). That commit's own subject is *"refactor(el-atlas): migrate el-atlas out
of scratch/ to a root peer (el-atlas/)"* — **a move, not an authorship.** Per §Y, *"the antecedent
probe must find an artifact's origin in the tree that AUTHORED it, not the tree that currently holds
it"*; dating by the commit that relocated a file is the same error one directory down.

| artifact | origin (corrected) | witness | vs. my draft |
|---|---|---|---|
| el-atlas depsort | **2026-06-11**, substrate `fbbfd7591` *"Draft 16 state: the EL-Atlas at the codec turn"*, authored under `scratch/` | `git log --follow`; four same-day v3.x commits (`80a8f0201`, `394b67efb`, `ce5e65847`, `f0f9e09ee`) show it under active development that day | ⚑ **6 days earlier than I filed** |
| `corpora.tsv` / `corpus_fetch.py` | in `linux-sources`; `corpus_fetch.py`'s docstring cites `◆61` as its own antecedent, which I did not resolve | citation | unchanged; ⚑ **`◆61` is an unresolved antecedent I am not claiming to have chased** |
| rosettapkg itself | first commit `8a5fb1f`, 2026-09-02 16:21:28 -0400 | git log, authored here | unchanged — rosettapkg is not a consolidation repo; it authored its own prose |
| realizability-charter discipline | adopted 2026-09-05 (`README.md`), from el-atlas §0 | citation | unchanged |

⚑ **§W's justification is vindicated, and by more than I first measured:** the tool my only instrument
is a port of originates **~12 weeks** before this repo exists. A one-day window would have reported
rosettapkg as the origin of its own method — and my own uncorrected probe would have shifted the
origin by 6 days toward the mover.

⚑ **Where I am exposed to §Y in the other direction:** `pm-depsort.py` is a **port**, so rosettapkg is
a receiving tree for el-atlas's design. If an apex dates that design by rosettapkg's `git log`, it
attributes a June substrate design to a September repo. The witness against that is the port's own
docstring naming its source (`lattice/pm-depsort.py:6`) — an explicit cross-reference, which is one of
the four witness types `references/apex.md` accepts, and it is in the artifact rather than in prose
commentary.

## §N Negatives (brief §5 / leg-filing.md schema)

**RP-N1 — no dependency manifest.**
```
claim:            no dependency-manifest file exists in rosettapkg
denominator:      8 of 8 files; plus explicit probe for 16 manifest spellings
shapes read:      .md, .py, git-tracked paths, dotfiles, .github/, .claude/
shapes empty from my reader: none relevant — the shape is absent, not undecodable
reader:           GNU find/ls/git ls-files
positive control: ~/github/linux-sources/MODULE.bazel — same reader, other corpus ✓
```

**RP-N2 — no third-party Python dependency.**
```
claim:            lattice/pm-depsort.py imports no package outside the stdlib
denominator:      1 of 1 .py files; all 4 import sites enumerated
shapes read:      module-level `import`/`from`, plus one function-local import at :472
found:            sys · typing.TYPE_CHECKING · collections.abc.Callable · hashlib (local, :472)
reader:           GNU grep 3.11
positive control: linux_sources/corpus_fetch.py:32 `import hashlib` — same reader, other corpus ✓
```

**RP-N3 — no CI workflow.** ⚑ **This negative was filed weak in my draft on a FAILED control; the
control failure was my own error, not a property of the corpus. Corrected at rev 6 under §Z.**
```
claim:             no CI-workflow configuration exists in rosettapkg
denominator:       8 of 8 files; 0 of 8 are .yml/.yaml; no .github/ directory (full `ls -a` of root)
shapes read:       *.yml, *.yaml, and directories named `workflows`, unbounded depth under the worktree
shapes empty from my reader: none — the shape is absent here, and demonstrably decodable elsewhere
reader:            GNU find (findutils)
positive control:  ~/github/earley/.github/workflows/ci.yml — same reader, other corpus ✓
                   > name: CI
                   >
                   > on: [push, pull_request]
                   [class: citation, verbatim, `~/github/earley/.github/workflows/ci.yml:1-3`]
```
⚑ **§Z, applied to myself, and it changed a verdict.** My draft reported this control as FAILED and
filed the weak form (*"no such record appears among the shapes my reader decodes"*), attributing the
failure to the possibility that no repo here uses GitHub Actions. **That was wrong, and wrong in the
modest direction.** The cause was a `-maxdepth 3` bound in my own probe; `~/github/earley`,
`~/github/gabion`, `~/github/mat260`, `~/github/coneVM` and others all carry `.github/workflows/`.
Re-run unbounded, controls are abundant.

Per §Z — *"a leg that overstates its own weakness corrupts the span exactly as much as one that
overstates its strength"* — I record the correction rather than quietly filing the strong claim: an
apex reading my draft would have held and reasoned around a reader limitation that does not exist. ⚑
The withdrawal is left visible, following `mtools`' precedent at §Z, because the mis-grading is
itself the finding. **The strong claim now stands: rosettapkg has no CI, measured.**

## §C Coverage as a population (brief §10)

| | |
|---|---|
| files | 8 of 8 read in full (`README.md`, `lattice/{AUDIT,FINDINGS}.md`, `lattice/pm-depsort.py`, `managers/{dpkg,pacman,portage,rpm-yum}.md`) |
| bytes | 126,645 of 126,645 |
| commits | 6 of 6 (`8a5fb1f` 2026-09-02 → `5c198a4` 2026-09-05), messages read; diffs not read line-by-line |
| unreadable | **0** |
| untracked/ignored | 0 (`git status --porcelain --ignored` empty) |
| not searched | peer filings (§2) · .sqfs interiors · the GitHub remote |

⚑ **Denominator honesty:** this is a small corpus and I read all of it. The limit on this leg is not
coverage of rosettapkg; it is that most §Q items are absences, and one of three absences (RP-N3) has a
failed control.

## §T Termination (brief §12)

**No.** A reader of this file alone could not reconstruct what was asked of the other legs. This file
answers §Q for one repo, supplies one witnessed identification (RP-W1) and one roster nomination
(`substrate`), and adjudicates nothing. Assembling the span is the apex's job — and per §C of the run
file, publishing the span is not the deliverable either.

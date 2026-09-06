# `deps-build` — the apex. Prefix `AX-`.

**I hold no leg.** I am a subagent dispatched after `FREEZE CALLED` (`§V` rev 31), holding no
survey context, no prior turn of this census, and no repo under survey. Per `§R`'s wording — *"a
fresh session holding no leg"* — and rev 21(b)'s ruling that a subagent satisfies it, this is the
apex. I authored none of the seven legs and had read none of them before this pass.

**Written against:** `CENSUS-deps-build.md` rev 38 · `CENSUS-deps-build-ANALYSIS.md` (embargo
lifted at rev 31) · `CENSUS-BRIEF.md` rev 1 · `references/apex.md`.

---

## `AX-00` — Reference arms, instrument, and how I read each leg

### The two arms, declared per skill §4

- **Evidence arm.** The seven filed legs in `findings/deps-build/`, read **as documents**, whole,
  by the harness `Read` tool; plus the run file, the companion, the brief, and `apex.md`. Nine
  live re-derivations of my own are named in `AX-01`. Everything else is UNAVAILABLE, not absent.
- **Normative arm.** `references/apex.md` and `CENSUS-BRIEF.md`, as amended by `§V` revs 1–38.
  ⚑ **Audited before adoption, per §4's instruction, and one item did not survive:** rev 11/32/35's
  instruction to cross-check `mdstruct --headers` against `--budget` is **withdrawn by rev 36** —
  those are one binary in two modes, not two readers. I followed rev 37's replacement. A second
  normative item is *scoped* rather than adopted whole: `§X`'s executor-degradation **cause** was
  withdrawn at rev 23 and I treat only the **symptom and guidance** as normative (`AX-14`).

### ⚑ `§A6` — which legs I read as DOCUMENTS versus reconstructed

**All seven were read as documents. I re-swept no leg's corpus.** This is the strongest available
state for `§A6` and it is stated plainly because the alternative is the measured failure `apex.md`
records: *an apex identified its own re-sweep of a party's corpus with that party's own filing and
thereby resolved four of that party's measured absence claims in favour of the sweep.*

| leg | file | read as | my own instrument runs against it |
|---|---|---|---|
| `PK-` paperkit | `paperkit-deps-build.md` | **document**, whole | `mdstruct spans` (15 sections) |
| `SB-` substrate | `substrate-deps-build.md` | **document**, whole | `mdstruct spans` (16), `mdstruct grep` |
| `CO-` cassian-observability | `cassian-observability-deps-build.md` | **document**, whole | `mdstruct spans` (20) |
| `MT-` mtools | `mtools-deps-build.md` | **document**, whole | `mdstruct spans` (13 + prose) |
| `LS-` linux-sources | `linux-sources-deps-build.md` | **document**, whole | `mdstruct spans` (46), `mdstruct grep` |
| `RP-` rosettapkg | `rosettapkg-deps-build.md` | **document**, whole | `mdstruct spans` (17) |
| `SM-` summit | `summit-deps-build.md` | **document**, whole | `mdstruct spans` (21) |

⚑ **Nine `git` re-derivations of my own appear below** (`AX-01`, `AX-14`). They are **not** re-sweeps
of any leg's corpus; each is a **single-fact origin or count check** run in the tree that
**authored** the artifact, per `§Y`. Where one confirms a leg, I say **corroborated** and name it
as *my measurement agreeing with theirs* — two witnesses that could have disagreed. Where I ran
none, the leg's claim is **carried as testimony**, not upgraded.

### ⚑ The instrument, and the rev-36/37 trap I did not fall into

**I read `.md` structure with `mtools/mdstruct/.venv/bin/mdstruct spans`, per rev 37, which is
binding.** I ran substrate's copy **zero times** on any leg.

Rev 37 records that this repo's own `hook_structural_query` routes every `.md` to
`substrate/scratch/mdstruct.py` — **the defective copy** — and refuses `grep`/`cat`/`sed` as a
fallback. ⚑ **That hook fired on me once during this pass**, routing me to the copy rev 37 forbids;
I used mtools' binary by absolute path instead. **The census's sanctioned reader and the census's
binding instruction point at different binaries, and I resolved it in favour of the instruction.**

**Measured on my own reads, as a control on the control:** `mdstruct spans` gives `LS-` **46**
sections, of which `LS-09`, `LS-16c`, `LS-17` and the reader-blind coverage note — the four rev 34
names as dropped — are all **present and read**. `SM-` gives **21**, with `SM-03` and `SM-13`
present. ⚑ **`SM-13` is summit's `§Q`-8 answer and `LS-17` is an instrument-integrity finding; both
are in the glue below.** Had I used the routed reader, both would be silently absent from this
document and nothing would have shown a gap.

⚑ **And rev 38 is why I did not treat rev 36 as a retraction of rev 34/35.** The two spellings
differ — substrate's takes flags (`--headers`), mtools' takes subcommands (`spans`) — so a
subcommand run against substrate's copy returns *does not exist* and reads as *the mode is absent*.
**Rev 34/35 stand as true facts about substrate's copy; rev 36 scopes them to that implementation.**
Both are carried. I resolved nothing between them because rev 38 already did.

---

# PHASE 1 — THE SPAN `A`

⚑ **`A` is the index, not the answer.** It is published here in full, and phase 2 follows it. Per
`apex.md`, every row carries a **witness**; a row without one is my convenience and is not written.

**Witness types used below**, exactly the four `apex.md` admits:

- **`byte`** — byte-identity of quoted text across legs (strongest)
- **`third-party`** — the same third-party prose quoted in each leg as the block being answered
- **`xref`** — an explicit cross-reference by one leg to another's locator
- **`clock`** — matching timestamps within a plausible single pass
- **`apex-measured`** — ⚑ a fifth kind I add and label distinctly: **my own single-fact
  re-derivation in the AUTHORING tree**, per `§Y`. It is not one of `apex.md`'s four; it is
  stronger than three of them for *origin* questions and weaker for *identity* questions, and it is
  never used alone to identify two legs' entries with each other — only to confirm an origin both
  legs already assert.

## `AX-01` — The span `A`: 18 witnessed rows

| # | item | PK | SB | CO | MT | LS | RP | SM | witness |
|---|---|---|---|---|---|---|---|---|---|
| **A1** | ⚑ **the `verb.bzl` three-tier model** (`sandbox`/`local`/`toolchain`) | `PK-05` | — | `§Q-5` | — | `§Q-4` `_tier_exec` | — | — | **`apex-measured` + `xref`.** All three name the same three tier words. Origin re-derived by me in each authoring tree: paperkit `99cde55` **2026-06-27**; cassian `cde668d` **2026-09-03** (*"port the verb.bzl/verdict.py engine"*); linux-sources `2315c2c` **2026-09-03**. `CO-`'s `§6` states paperkit's date **independently and identically**; `LS-19` names paperkit as source. Two legs and my measurement agree on one origin. |
| **A2** | ⚑⚑ **`execution_requirements` is fingerprinted TWICE, so a tier marker is part of action identity** | `PK-05` | — | `§Q-5` | — | `LS-09` | — | — | **`xref` + `byte`.** `PK-05` marks it **TESTIMONY (linux-sources, read from Bazel 8.7.0 source)** — an explicit cross-reference to `LS-09`'s locator. `LS-09` quotes `ActionEnvironment.java:128-131` from the pinned bazel corpus. `CO-`'s `§Q-5` states the same property (*"`execution_requirements` are fingerprinted"*) from its own `cquery` run. ⚑ **`LS-09` is one of the four headings substrate's mdstruct drops.** |
| **A3** | ⚑⚑⚑ **a version BANNER is not the bytes — a toolchain verdict survives a replaced tool** | `PK-04`.1 | — | — | — | `LS-07` | — | — | **`byte` + `xref`.** Both quote a `--version` banner **identical across two different sha256 payloads**. `PK-04`: `STABLE_TOOLCHAIN_PANDOC pandoc 3.1.11.1` across `6dd4b433… → d7c283e5…`. `LS-07`: `STABLE_TOOL_RUFF ruff 0.16.5` across `024cdfbb… → 94fde127…`. ⚑ `LS-07` **names the direction**: *"the arm was run here after paperkit ran it in theirs"* — a cross-repo defect propagation with a witness, `LS-22` calling it *"the ARM propagated from paperkit; the FIX was re-implemented here."* |
| **A4** | ⚑⚑ **`--remote_local_fallback` — the live policy split on one shared executor** | `PK-09` **SETS it, both configs** | `SB-09` n/a, no bazel | `§Q-5` **sets it nowhere**, operator ruling 2026-09-04 | `MT-04` **not set**, F-armed | `LS-12` **removed**, quoting the operator | `RP-09` undocumented decline | `SM-10` n/a, no bazel | **`byte` (the flag spelling) + `apex-measured`.** I counted `remote_local_fallback` in paperkit's `.bazelrc`: **4 occurrences** — corroborating `PK-09`'s *"sets it on both remote configs"* and `CO-`'s pre-freeze testimony. ⚑ **Carried to the divergence register, `AX-20`, unresolved.** |
| **A5** | ⚑ **`--remote_local_fallback` HID a defect: green with zero remote actions** | `PK-09` (*"precisely what would prevent me noticing I am not on the sanctioned config"*) | — | `§Q-5` sub | — | `LS-12` | — | — | **`xref`.** `CO-`'s `§Q-5` sub-section quotes `LS-12` **by locator, class `testimony`**, then tests it against its own tree. `PK-09` reaches the same property independently from the other side. ⚑ Three legs, one mechanism, **and they disagree on whether it applies** — see `AX-20`. |
| **A6** | ⚑ **remote execution had never worked while reporting success** | — | — | `§Q-5` sub | — | `LS-11` | — | — | **`xref` + `clock`.** `LS-11` is three-armed on a clean tree, *"it took three attempts to make honest… GREEN both times, having never contacted the executor."* `CO-` ran `bazel test //:gate --config=remote` **explicitly because `LS-12` reached it as testimony**, in the same 2026-09-06 pass, and reports the shape **does not hold there**. Both dated 2026-09-05/06. |
| **A7** | ⚑ **the gate that passes by NOT RUNNING** (`§Q`-4's named case) | `PK-04` (2 instances) | `SB-04` `check_scratch_runtime.py` exits 0 | `§Q-4` LOAD-BEARING CAVEAT | `MT-09` **declines substrate's** | `LS-07`, `LS-18` | `RP-04` | `SM-09` (3 instances) | **`byte`.** ⚑ **`MT-09` quotes substrate's artifact by name and behaviour** — *"`check_scratch_runtime.py` | substrate | prints `SKIPPED (no cupy/GPU)` and **exits 0**"* — and `SB-04` quotes the same file with the same two facts. **The identification is byte-witnessed by the declining party naming the declined artifact.** `MT-07` adds the general rule and credits `LS-` for it. |
| **A8** | ⚑⚑ **`[[tool.mypy.overrides]]` declined, same reason, three legs** | — | `SB-09` | — | — | `LS-` `§Q-9` | — | `SM-14` | **`byte`.** `SB-09` and `LS-`'s decline table carry the **same sentence**: *"If something cannot be typed, that is a FINDING ABOUT THE DESIGN, not a category of code."* `SM-14` declines it on an **operator ruling that the bar is universal**, having carried **four** override blocks. ⚑ Rev 27(b) adds the fourth face: summit's two remaining blocks **measured DEAD** at install. |
| **A9** | ⚑ **`membudget`: built by one party, needed by four, not installable** | `PK-09` declined by deletion `95d12ad`; `PK-08` re-derived its lease primitive unknowingly | `SB-08` **authored it**; `SB-03` *"untracked in git… a peer cannot fetch it"* | `§Q-8` `resource-lease`, *"membudget is **not installable**; consumers vendor it"* | `MT-09` declined cassian's PID lock **for membudget** | `LS-27` declined, with a §5 control | `RP-09` undocumented decline | — | **`third-party` + `byte`.** ⚑ **The operator's own prose is quoted verbatim in two legs**: `CO-`'s `§Q-8` — *"I can't tell how many times I've told all of you to improve on and genericize that machinery, and had you not share the improvements back"* — and the same sentence is the `census-kit` skill's originating grievance. `SB-03` and `CO-` state the **same mechanical cause** (untracked/not installable). ⚑ **Six of seven legs hold a membudget entry.** |
| **A10** | ⚑ **`--remote_local_fallback` is ruled out by `§X`** as ecosystem guidance | `PK-09` cites `§X` | `SB-09` *"Recording it as `§X`-supplied rather than as my decision"* | `§Q-9` | `MT-04` *"per the `§X` ruling"* | `LS-12` quotes the operator | `RP-05` cites `§X` | — | **`third-party`.** Six legs quote or cite **the same run-file `§X` bullet** as the block being answered. `LS-12` and `CO-`'s `§Q-9` carry the operator's reason **byte-identically**: *"it evades the scheduler and consumes resources on/against the [very same] machine the scheduler is protecting."* |
| **A11** | ⚑⚑ **a gate has FIRED, on the surveyor, DURING this survey** | `PK-07` **twice today** | `SB-07` *"~a dozen commands"*, per-file gate, polarity probe ×2 | `§Q-7` **3 named, `structural-query` ~a dozen** | `MT-07` **3 commits**, each repaired at source | `LS-24` **12 refusals**, ×3 hooks | `RP-07` ⚑ **ZERO — no gate exists** | `SM-12` **6 + 4 + 11**, three real defects | **`third-party`.** All seven answer the **same run-file `§Q`-7 prose**, quoted as the block in `SM-12`, `LS-24` and `RP-07`: *"Has it ever fired? A gate that has never refused anything is a configuration, not a gate."* ⚑ **`RP-07`'s zero is the load-bearing row** — it does not *"even reach the configuration tier."* |
| **A12** | ⚑ **the harness `PreToolUse` hooks (`structural-query` / `no-chaining` / `shellcheck` / `pycheck`) refuse the surveyor's own commands** | `PK-` — | `SB-07` all four armed | `§Q-7` *"constantly"* | `MT-09` declines waivers | `LS-24`/`25`/`26` | — | `SM-12` five armed, one summit-authored | **`byte`.** The **same four hook names** appear in `SB-07`, `LS-24`, `SM-12` and `CO-`'s `§Q-7`. `LS-28` records the adoption route: *"the established adoption route (freecell, el-openglo and gabion took the same one), not a copy."* ⚑ **`LS-06` and `SM-08` are the same measured failure of that route** — see `A13`. |
| **A13** | ⚑⚑⚑ **an unguarded `substrate.*` import at module scope took a borrower's whole gate down** | — | `SB-` (owner; not reported as a defect in its own leg) | — | — | `LS-06` | — | `SM-08` | **`byte`.** Both name **`substrate.ratchet_flags` / `arg_after`** as the exact import. `LS-06`: *"substrate moved arg_after behind `substrate.ratchet_flags`, `_ROOT` through the symlink resolved to THIS repo… the hook exited 0 = ALLOW — a gate that had silently stopped gating."* `SM-08`: *"`hook_cmdparse.py:437` reads `from substrate.ratchet_flags import arg_after` — unguarded, at module scope… 19 slices to a traceback."* ⚑ **Rev 26 rules that `§Q`-3 decided `§Q`-4 here**: linux-sources installs `substrate-tooling` as a package and survives; summit vendors copies and does not. **The symlink/copy distinction was irrelevant to the import.** |
| **A14** | ⚑ **the interpreter is pinned in a second file, and the two pins are different claims** | `PK-02` mise-managed | — | `§Q-1` *"match the mise pin, or uv builds the venv on the floor (3.10)"* | — | `LS-` `§Q-1` `mise.toml` + `pyproject.toml` | `RP-02` `python3` ≥3.13 via a mise shim | `SM-02` **3.14 vs `>=3.11`** | **`byte`.** Four legs name **`mise.toml`** and **`pyproject.toml`** as two surfaces carrying different claims. ⚑ `SM-02` and `CO-`'s `§Q-1` reach **opposite resolutions from the same premise** — summit refuses to raise the floor (*"would assert that summit's modules need 3.14, which is false"*), cassian raises it (*"match the mise pin"*). **Not a divergence — different facts about two repos.** |
| **A15** | ⚑ **BUILD-file GENERATION: the roster is the source, there is no second place to update** | `PK-09` fetch-time generation, 117.5 MB | `SB-05` `agda/Flat.mk` generated; `bazel_emit` **never wired** | `§Q-5` `tools/gen-gate-build.py` from `check --list` + arm set | `MT-12` ⚑ **ABSENT, and not benign** | `LS-04`/`LS-21` `gen_gate_build.py`, 1,905 lines | — | `SM-10` slices **discovered** from a directory | **`byte` + `xref`.** ⚑ **`MT-12`'s positive control is the identification**: *"POSITIVE CONTROL: the same reader, same spelling, on `/home/mikemol/github/linux-sources` — HITS: `tools/import_closure.py`, `tools/gen_gate_build.py`, `tools/verb.bzl`"* — **mtools names linux-sources' filenames from linux-sources' tree**, and `LS-04`/`LS-21` name the same file. `MT-09`'s third disclosure records the operator correcting mtools: *"the mechanism exists in **all four** peer repos."* |
| **A16** | ⚑ **a test binds 1:1 to a CLAIM in a `.bib`, and the gate refuses a mismatch** | `PK-06` 49 warrants, 9 `.bib` | `SB-06` arms + warrant ledgers | `§Q-6` 42 claims / 76 arms, 3 provenance kinds | `MT-06` **192 tests : 192 warrants, 1:1** | `LS-` `§Q-6` 42 `@misc` → 35 fact modules | `RP-06` a break-matrix, **no framework** | `SM-11` witnesses, not tests | **`byte`.** Five legs name the **`@misc{` BibTeX entry** as the claim unit and a checker binding it to executable evidence. `MT-06`: *"A claim is a BibTeX `@misc` entry; a test is a pytest function; the binding is 1:1."* `LS-`: *"42 `@misc`, each `check = {corpus:…}` or `{gate:…}`."* ⚑ **The shared ancestor is paperkit's `warrants.bib` + `paper.toml` → gate.** |
| **A17** | ⚑⚑ **FALSIFIABILITY IS PROVEN BY MUTATION, not observed by passing** | `PK-06` mutation sweep, **8,114 `Ζ·eval` cells**; ladder `broken −1 … imported 4` | `SB-06` polarity probe at registration | — | `MT-06` ⚑ **explicitly HAS NOT built it**: *"paperkit's mutation approach is the thing that would, and I have not built it"* | `LS-16` `--mutate`, *"a predicate no mutant breaks is decoration"* | `RP-06` break-matrix, internal only | `SM-11` F-arms | **`xref` + `byte`.** ⚑ **`MT-06` names paperkit's mechanism by owner while declaring its own absence** — an explicit cross-reference that identifies `PK-06` and `LS-16` as the same mechanism from the party that has neither. `LS-16` and `PK-06` independently reach *a claim whose verdict does not change under mutation is indeterminate, not passing*. |
| **A18** | ⚑ **the antecedent probe corrected a self-attributed origin, in FOUR legs** | `PK-13` membudget → **11 turns, 2026-08-22/25**, *"retired two of my own findings' novelty"* | `SB-` probe: the per-file gate config is *"ADOPTED FROM linux-sources' MEASURED CONFIG, NOT INVENTED"* | `§6` verb.bzl → paperkit `99cde55`, **68 days** | `MT-01` ⚑ *"this repo's git history systematically misdates its own designs"* | `LS-01` gate is **17 days older** than the build system | `RP-§A` ⚑ corrected **6 days** toward the mover | `SM-17` `hook_structural_query` *"adopted from substrate, not authored here"* | **`third-party`.** ⚑ **Six legs quote or cite `§Y`'s rule as the block being answered**, and `§Y` is itself sourced from `MT-01`. `RP-§A` and `CO-§6` both quote `§Y`'s *"find an artifact's origin in the tree that AUTHORED it"* and **each changed a filed date because of it**. `SM-17` reaches the same shape unprompted. |

**Span size: 18 rows.** Coverage: every one of the seven legs appears in at least six rows;
`RP-` appears in 8, `SM-` in 10, `MT-` in 12, `SB-` in 12, `CO-` in 13, `PK-` in 14, `LS-` in 16.

## `AX-02` — ⚑ NON-IDENTIFICATIONS: things that look like one row and are not

**`apex.md` calls this table not-optional politeness.** Each of these was a candidate row I built
and then refused, because the witness `A` requires was absent or pointed the other way.

| looks like | is NOT identified with | because |
|---|---|---|
| `LS-` `§Q-10` **six `local`-tier targets, host-coupled tail** | `CO-` `§Q-10` **the co-sign / `sudo` boundary** | ⚑ **`§T` binds: these are TYPES, not magnitudes.** Both answer `§Q`-10 and the answers are **incommensurable**. `CO-` states it in its own leg: *"a 0.36 s critical path over 8 actions against a 400 s+ one over 17 is not a faster version of one graph — it is a different graph."* Identifying them would produce *"a number describing no repo."* **Carried separately at `AX-19`.** |
| `SB-08` **`membudget`'s load-average predicate** | `CO-` `§Q-8` **`scripts/resource-lease`** | Same subject, **different objects**. `SB-` authored membudget; `CO-` built a *pool lease over interchangeable members*, generalizing *exclude-a-named-artefact* to *allocate-from-a-pool*. `CO-` says so explicitly: *"I needed a shape it did not offer."* ⚑ **Per census-kit §B4 these are two witnesses, not a duplicate to collapse.** Both stand in `AX-17`. |
| `PK-08` **an action-idempotent scratch claim** (`.cellvenv.<pid>.tmp` → `os.rename`) | `SB-08` / `CO-` membudget's `claim:<tag>` | ⚑ **`PK-08` itself supplies the near-identification AND its limit:** *"This is a lease, hand-rolled, and `membudget`'s `claim:<tag>` is the same primitive. **I did not know that when I wrote it.**"* The **primitive** is shared; the **implementations** are independent and share no code, author or key grammar. Identifying the artifacts would erase the re-derivation, which is the finding. **The primitive is row `A9`; the implementations are three separate `AX-17` entries.** |
| `MT-08` **`ratchet/`** | `SB-`'s ratchet machinery | ⚑ **The strongest non-identification in the run, and `MT-08` argues it against its own convenience.** They **agree on every classification** — *"from two derivations sharing no author, no corpus and no key grammar (substrate keys `name::path` off a declared schema; mtools keys `path:rule` positionally)"* — and **differ on exactly one axis**, substrate's fan-out defence being a `strict=` parameter **defaulting off**. Collapsing them destroys the only evidence of the defect. **Both carried, `AX-21`.** |
| `LS-06` **the symlink-adoption failure** | `SM-08` **the shared-body import failure** | ⚑ **Identified as ONE MECHANISM at `A13` and NOT as one event.** Different dates, different importing files (`hook_cmdparse.py` vs. the four symlinked hooks), different acquisition routes (package-install vs. vendored copy), and **opposite outcomes** — `LS-` survives today, `SM-` does not. Rev 26 rules the discriminator is `§Q`-3, not `§Q`-4. **The mechanism is a span row; the two incidents are separate glue entries.** |
| `RP-08b` **`pm-depsort.py`** | substrate's `el-atlas-depsort.py` | ⚑ **`RP-08b` refuses the collapse itself, citing census-kit §B4**, and names what would be needed to merge: *"a statement of whether the domain-specific claim set is separable from the SCC/layer machinery — which nobody has written down."* ⚑ **substrate's leg does not mention el-atlas-depsort at all**, so this is a one-sided relation: `RP-` is a documented adopter of a substrate artifact **substrate did not report holding**. Carried at `AX-24`. |
| `MT-11`/`MT-12`'s **positive controls, run on linux-sources' tree** | `LS-03`/`LS-04`/`LS-21`'s **own account of those files** | ⚑ **This is `apex.md`'s over-glue trap and I decline it.** `MT-`'s control is a **filename-existence sweep by a foreign reader** — it establishes that `tools/import_closure.py` exists; it says nothing about what `LS-03` reports the file *does*. **A control is not a survey.** `MT-` says so: *"I hold no verified knowledge of how peers solve this."* The two are `A15` neighbours, not one entry. |
| `SM-13`.3 **summit's `stubs/paperkit/`** | substrate's `stubs/paperkit/bib.pyi` | ⚑ **A re-derivation whose duplicate the re-deriver found and reported, and the shapes DIFFER**: *"mine is differently shaped because summit imports `bib` bare where substrate imports `paperkit.bib`."* Same absence answered twice, two non-interchangeable artifacts. ⚑ **substrate's leg does not report holding stubs**, so I hold only summit's testimony. Carried unadjudicated at `AX-17`. |
| `CO-01`'s **withdrawn Valkey ghost-shard cause** | `SB-01`'s **`valkey` python package** | ⚑ **A false span row my instrument nearly manufactured.** `mdstruct grep -i valkey` hits three legs. `SB-01`'s is the *pip package* `valkey`, installed by hand and named in no manifest — **an unrelated `§Q`-1 finding sharing one word.** Recorded because a term-filtered sweep would have glued them. See `AX-14`. |
| `PK-11`'s **`~/.claude/skills/` nomination** | `CO-`/`SB-`/`LS-30`'s **`summit` nomination** | Both are *"the missing party is an index, not a builder"* — and they name **different artifacts** (a skills tree on this machine vs. a repo with a capability registry). No leg cross-references the other. ⚑ **`PK-11` is a nomination NO other leg made and it is the only one naming a non-repo.** Carried whole at `AX-22`. |

⚑ **`A` too small vs. `A` too large — both directions, stated.** I judge `A` at **18 rows** to be
**mildly under-glued rather than over-glued**, deliberately, and the specific unpaid cost is the
`AX-17` re-derivation table: I could not witness whether `SB-08`'s *"~100 tools, ~619 modes"* of
structural readers identify with `CO-`'s *"a structural-query toolkit (`mdstruct.py`,
`pycodemod.py`, …)"* or `LS-23`'s borrowed-by-path copies of the same filenames. **`SB-08` names
this as the bound the glue was supposed to resolve** — *"This is the largest re-derivation in the
leg and I cannot bound it: I do not know which of these a peer already had."* ⚑ **I cannot resolve
it either without a re-sweep, which `§A6` forbids me from counting as a second witness. It stands
open at `AX-25`.**

---

# PHASE 2 — THE GLUE

⚑ **Phase 1 is finished and is not the answer.** What follows carries **every leg's contribution**,
including the ones only one leg holds. **No admission bar.** Nothing is dropped for being unshared,
unverifiable, or inconvenient.

## `AX-10` — `§Q`-1 Dependency declaration: seven repos, seven shapes, and the shapes do not converge

| leg | surfaces | pinning | ⚑ vantage-local finding |
|---|---|---|---|
| `PK-01` | **4** — `MODULE.bazel` (lock **874,561 B**), two hashed `requirements_*.txt`, `paper.toml` `pydeps` | `--hash=sha256:` per line | ⚑ **`pydeps` is the deliberately non-Bazel surface** — it declares the **closure, not the imports**, so a non-Bazel consumer can read what a project's checks need |
| `SB-01` | **1** — `pyproject.toml`, floating, `uv.lock` generated | names without bounds | ⚑ **Every entry carries a prose rationale and several carry an INCIDENT.** Three record a dependency *deleted as unused and load-bearing*: `SQLAlchemy` (*"a red gate that looks like a finding and is a missing package"*), `sympy`, and `pygit2`/`valkey` installed by hand so `uv sync --dry-run` **would uninstall a live dependency** |
| `CO-§Q-1` | **4 independent systems, no unifying manifest** — Python, Bazel, 10 `.container` quadlets, OpenTofu (47 `.tf`) | ⚑ **`Image=…@sha256:` — the digest IS the lock** | ⚑ **`requires-python` carries its own reason inline**: *"match the mise pin, or uv builds the venv on the floor (3.10)"* — *"The pin is not a preference; it is a defect report with a version number"* |
| `MT-02` | **3 layers** across 3 distributions | `uv pip compile` | ⚑ **Every lock's line 2 is BYTE-IDENTICAL** — *"a hand-edited or differently-generated lock would diverge on line 2. It is checked by eye, **not by a gate**"* |
| `LS-`§Q-1 | **5** + `corpora.tsv` for **28 source corpora** | floors in `pyproject`, pins in `uv.lock` | ⚑ **`LS-02`: TWO LOCKS THAT MUST AGREE BY HAND.** *"a bare `mypy==2.3.1` re-resolves ast-serialize to a NEWER version than uv.lock pins (measured: 0.9.0 vs 0.8.0)"* — *"a real un-gated dependency edge in a repo that gates almost everything else"* |
| `RP-01` | ⚑ **ZERO. No manifest of any kind** | **prose sentences** | ⚑ *"These prose pins are **real content-addressed pins**… The defect is not the pinning; it is that the pin lives in a sentence that nothing can read"* |
| `SM-01` | **1** + a second interpreter pin | floors, `uv.lock` | ⚑⚑ **Six of the seven runtime deps are NOT summit's — they are gabion's**, inherited whole because one witness imports gabion's live tree. *"a consumer that imports a peer's live tree inherits that peer's entire runtime closure, and no manifest anywhere records that relation"* |

### ⚑ `AX-10a` — `LS-02b` — the `ref`/`revision` distinction, and the only leg that consumes it

`LS-02b`, `citation` from `corpora.tsv`'s header:

> ⚑ A tag is a NAME and can move (measured: a repo whose only "release" tag pointed at a
> three-year-old tree). A commit is a RECORD. Where they differ the revision governs, and a ref of
> `master` is a SNAPSHOT honestly labelled — **not a pin, and it must not be quoted as one.**

⚑ **`RP-03` quotes the same docstring from the other side of the boundary**, and `RP-W1` supplies
the **only leg-authored witness table in the entire census** — four byte-identical hash prefixes
tying rosettapkg's prose pins to linux-sources' registry rows:

| hash | rosettapkg | linux-sources |
|---|---|---|
| `c8dc5ea575a2` | `managers/rpm-yum.md:3` | `corpora.tsv:70` |
| `138cbae58448` | `managers/pacman.md:3` | `corpora.tsv:71` |
| `3da5d7434be3` | `managers/portage.md:3` | `corpora.tsv:78` |
| `2c73b59da296` | `lattice/AUDIT.md:126`, `pm-depsort.py:49` | `corpora.tsv:69` |

⚑ **And `RP-W1` states the NON-identification too**, unprompted: `a6f7467d` and `bd454e2c` are from
a discarded clone and **must not be glued** to `corpora.tsv`. *A leg that supplies both halves of a
witness is doing the apex's phase-1 work for it, and it is the only leg that did.*

### ⚑ `AX-10b` — `SM-03`: a declared floor unsatisfiable by three of the versions it admits

**Vantage-local to summit, and it is a defect report about a party on nobody's roster.** gabion
declares `requires-python = ">=3.11"` and references `ast.Interpolation`, a node CPython added in
**3.14**. ⚑ *"the failure is invisible from any tree running 3.14, which is every tree where
gabion's own suites pass."*

⚑⚑ **The generalisation is summit's and it is carried verbatim because it is sharper than the
instance:**

> *a dependency list built by repeated failure records the ORDER OF DISCOVERY, not the
> requirement*, and it terminates only by accident.

Three unrelated defects sat behind **one** UNAVAILABLE, *"each invisible from in front of the one
before it."* The repair was to **stop reading tracebacks and read the declaration**.

## `AX-11` — `§Q`-2 Dependency discovery: mechanised in three legs, a PERSON in four

⚑ **The split is the finding, and it is clean.**

**Mechanised:** `LS-` (three layers), `PK-02` (`closure.py`/`sites.py`/`def_sites.py` + a
watching module extension), `SB-02` (`import_manifest.py` → **MISSING: 15**).

**A person, by eye:** `MT-03` (⚑ *"Discovery is: I read the code"*), `CO-§Q-2` (*"no import scanner
and no manifest reader"*), `RP-02` (*"an author opens `corpora.tsv` and reads a row"*), and `SM-04`
partially.

### ⚑ `AX-11a` — `LS-03`: the closure is a CORRECTNESS requirement, not an optimisation

Vantage-local to linux-sources and, per `LS-20`, the largest single re-derivation in the census.

> A per-file check caches correctly only if its cache key covers everything the result depends on.
> For mypy that is the file PLUS its transitive first-party import closure … Running mypy on A
> alone, with B stubbed to `Any`, silently SUPPRESSES that error. **So the closure is not an
> optimization; it is what makes per-file caching correct rather than fast-but-wrong.**

The return type is **three-state deliberately** — `first_party` / `unresolvable` / `dynamic` — and
the docstring names the trap:

> ⚑ THE UNDER-COVER IS A TYPED, VISIBLE STATE -- NOT A SWALLOWED ONE. The trap for a closure tool
> is not "the closure is wrong"; it is "the closure dropped an unresolvable import and returned
> success", so the caller reads absence-of-error as coverage.

⚑ **And the hermetic reader found what the host reader hid**: *"the hermetic sandbox mypy reported
`Module "linux_sources" has no attribute "corpus_census"` because the submodule was unstaged -- the
toolchain-tier host mypy hid it… **only a hermetic reader surfaces it.**"*

⚑ **`LS-20` credits substrate for the measurement that justifies it** (`type_scope.py`: 3 findings
→ 231) and calls that **a defect report about substrate**: *"substrate held the number; the closure
computer did not exist."*

### ⚑ `AX-11b` — `LS-04`: seventeen numbered adversaries, and it refuses a graph it cannot prove complete

**`LS-04` is nominated by its own leg as *"the most transferable artifact here."*** 1,905 lines,
three exception classes, three exit codes: `_STALE = 3`, `_UNDERCOVER = 4`, `_OPAQUE = 5`.

> `UnderCoverError`: Raised, never papered over. A whole-tree fallback would cache-bust the world on
> any edit … and hide that the closure was indeterminate. The honest response is a HARD FAIL naming
> the file and its gap -- **fix the import, not the key.**

Three of the seventeen, carried because each names a distinct stale-green class:

- **Stub files** — *"reached by runtime `sys.path` insertion -- so they are in no first-party import
  closure and were in no slice's `data`. A `.pyi` edit flipped the stubs verdict while invalidating
  no key: a stale-green."*
- **Roster tool contents** — *"**the set-vs-content gap** -- the roster tracks WHICH tools carry a
  selftest, never WHAT the selftest does."*
- **Second artefact of one generator** — *"**the drift-detector cache-hit green over the very file
  it exists to check.**"*

⚑ **The subprocess net is fail-closed over a bounded set, and the reason ends a treadmill:**
*"Unlike argv SHAPES (unbounded), the spawner FUNCTIONS are a finite, stable set -- so enumerating
them is bounded and **ends the treadmill.**"*

### ⚑ `AX-11c` — the implicit set, unioned across seven legs

**No manifest anywhere names any of these.** Carried as a union because `§Q`-2 asks for it by name
and **no single leg holds more than a third of it**:

- **Binaries on `PATH`** — `git`, `bash`, `python3`, `uv`, `bazel`, `shellcheck`, `sqlite3`, `curl`,
  `systemctl`, `k3s`, `tofu` (`CO-`); `pandoc`, `verapdf`, `lualatex`, `soffice` (`PK-02`); `agda`,
  `ruff`, `mypy` (`SB-02`); `mksquashfs` (`LS-`); `mise` itself (`SM-04`). ⚑ **`MT-03` counted its
  own by occurrence: `git 13 · realpath 9 · grep 9 · python3 7 · bazel 7 · shellcheck 5 · diff 5 ·
  sed 2 · pandoc 1 · kubectl 1` — ten host binaries, zero in any manifest.**
- **⚑ `pandoc` is named by FOUR legs and is in no lockfile on either side** (`SM-04` states it in
  exactly those words; `PK-02`, `SB-02`, `MT-03` name it too).
- **Peer trees at fixed relative or ABSOLUTE paths** — `SM-04`'s fourth row, ⚑ *"discovered by
  **nothing**, noticed by **nothing until it crashes**"*: `../substrate/scratch/pycodemod.py`,
  `../substrate/scratch/mdstruct.py`, `../gabion/src`, `../paperkit/tools/bibstruct.py`.
  `MT-03` is worse: **hardcoded absolutes** — `blockers.sh:24 sub=/home/mikemol/github/substrate`
  and `hooks/tests/test_adoption.py:33 _ADOPTER = Path("/home/mikemol/github/substrate")`. ⚑ *"A
  test asserts against a path in another repo."* `LS-` names `../substrate` as a hard build edge and
  `../summit` as a live read. `RP-02` names `~/github/linux-sources` **at that literal path**.
- **Services on loopback ports** — BuildBuddy `:31985`/`:31080`/`:31464` (five legs); VictoriaMetrics
  `:30828`, VictoriaLogs `:30928`, VictoriaTraces `:30428`, Valkey `:30637` (`CO-`).
- **A live kernel interface** — `/proc/pressure/{cpu,memory,io}`, `/sys/block/zram0/*`, cgroup
  `memory.stat` (`CO-`). ⚑ *"the host's kernel config is a build dependency of the test suite."*
- **A live postgres with `keyring` credentials** (`SB-02`); **systemd `--user` unit state** (`CO-`);
  **30 live squashfs MOUNTS** (`RP-02`, *"the corpora are mounts, not files in any repo"*).
- **⚑ THE OPERATOR** — `CO-§Q-2`: *"`scripts/apply` does not exist and cannot: applying requires
  root and this repo's agent cannot `sudo`. **A human is a declared dependency of the co-sign
  protocol.**"*
- **Env vars** — five `*_HOOK_BLOCK` (`LS-`); `PAPERKIT_BES` from a **gitignored** `.githooks/local.env`
  (`PK-02`); `PAPERKIT`/`PAPERKIT_ENGINE`/`PAPERKIT_HOME` (`SM-04`); `CHECK_FIXTURE_ROOT` (`CO-`).

### ⚑⚑ `AX-11d` — `SM-05`: EVERY MISE SHIM ON THE MACHINE WAS A DANGLING SYMLINK

**Vantage-local to summit, measured 2026-09-01, and it is a fact about the shared host that six
other legs depend on and none detected.** ~170 shims — `python`, `uv`, `node`, `cargo`, `java`,
`bazel`, `pytest`, `shellcheck` — each hardcoded `/snap/mise/203/bin/mise`, a revision snap had
replaced with 207 then 209.

⚑ **The damage was silent and selective**: everything through a login shell kept working, because
`PATH` also carried the real installs. **The breakage appeared only where the environment is
stripped** — and summit's `routes` probe deliberately runs hooks under `PATH=/usr/bin:/bin`, *which
is the arm that saw it.*

⚑⚑ **One dangling symlink presented as three independent instrument failures.** *"The hook was
behaving exactly as designed — announcing itself inert and failing open because its dependency was
unreachable."*

⚑ **And the repair reproduces the defect one revision later**: `mise reshim` repointed all ~170 at
`/snap/mise/209` — a revision, not `/snap/mise/current`. Summit's own generalisation:

> this is the dual of `SM-06` — a *pinned path* fails when the file moves; a *floating alias* fails
> when the name is repointed. **Neither is safe alone.**

⚑ **This is carried as testimony I cannot verify** (the shim state at that date is gone) **and it
bears directly on `RP-02`'s `python3` claim, `MT-03`'s ten binaries, and `SB-02`'s shellcheck
fallback** — none of which knew.

### ⚑ `AX-11e` — `SM-06`: a venv pins an ALIAS, and the instrument built to measure it was blind BY CONSTRUCTION

> ⚑ **Venvs do not vendor python.** `.venv/bin/python` was stored as a link to
> `.../mise/installs/python/3.14/bin/python` — an alias to `./3.14.5`.

When the alias moves: the venv runs a **new** interpreter, `site-packages` still holds C extensions
compiled against the **old** one, and `pyvenv.cfg`'s `version_info` keeps reporting the version
captured at **creation** — *which is the field tools read*.

⚑⚑ **`scripts/slices/interpreter.py` compares `mise which python` against `.venv/bin/python`, and
both sides dereference the same alias**, so the comparison is satisfied whatever it points to. *"It
read green across the entire episode."*

⚑ **And the first witness written to catch it PASSED against the live defect**, because it called
`resolve()` — measuring where the alias points *today* rather than the link **as stored**. Corrected
to `readlink()`, then armed both ways.

⚑ **`--copies` is the near-miss and not the escape**: uv exposes no `--copies`; `python -m venv
--copies` copies the **binary** (three real 32 MB files, measured) but `pyvenv.cfg` still names
`home`, so **the binary is vendored and the stdlib is not.**

⚑⚑ **This corroborates `PK-11`'s nomination from inside a leg** — `project-tooling`'s measured trap
list names *"`.venv/bin/python` being a symlink so interpreter-path comparison cannot detect env
activation"*, and `SM-06` is that trap firing on a party who then built the missing instrument
(`SM-13`.4: *"nothing in the ecosystem measures whether a venv is built from the interpreter its
config pins"*). **Neither leg cites the other.**

## `AX-12` — `§Q`-3 Acquisition, and what a cold machine does

| leg | routes | ⚑ cold-machine verdict |
|---|---|---|
| `PK-03` | Bazel fetches all; ⚑ **the engine itself is a WHEEL built in-tree and extracted into a per-cell venv** | ⚑ *"Extraction is a **complete** install only because the engine declares `dependencies = []`; with real deps this technique would silently skip resolution."* Four `PATH` toolchain programs **not acquired by the build** — a cold machine without `pandoc` **degrades rather than failing** |
| `SB-03` | `uv` + **one PEP 508 direct reference** (`paperkit @ git+https://…@main`) | ⚑ The manifest records **why that spelling and not `[tool.uv.sources]`** — the latter is uv-only and **dropped from wheel metadata**, so an adopter would inherit a bare name the resolver cannot satisfy. ⚑ **membudget is vendored-shaped but NOT vendored** — untracked, *"a peer cannot fetch it"*. Agda, pandoc, shellcheck, postgres **acquired by nothing** |
| `CO-§Q-3` | `uv sync`, bazel, `tofu init`, podman by digest | ⚑ **What does NOT survive a cold clone: the git hook wiring.** *"`git config core.hooksPath .githooks` must be run once per clone, because **git cannot enable a hook from a commit**"* — and *"an unarmed gate is indistinguishable from a passing one without that check"* |
| `MT-` | `uv pip compile` locks; `MODULE.bazel.lock` **tracked deliberately** | *"registry hashes only, no host paths, so a peer's first `bazel` invocation cannot silently re-resolve against a live BCR"* |
| `LS-`§Q-3 | **six routes, deliberately not unified** | ⚑ **`substrate wheel` is pinned by NOTHING — it tracks the sibling's HEAD.** `LS-05` records the trade as a trade (below) |
| `RP-03` | ⚑ **acquires NOTHING** — no lockfile, no fetch step | ⚑ **Zero of four manager entries are re-verifiable.** *"Every citation resolves through a mount that a fresh checkout of rosettapkg does not create, cannot create, and does not mention"* |
| `SM-07` | **vendored, not symlinked**, 12 shared bodies with sha256 | ⚑⚑ *"What was vendored was **never a committed upstream state**… at copy time substrate's `git status` read `??` for several of these files. **These digests pin a WORKING TREE, not a revision.**"* |

### ⚑ `AX-12a` — `LS-05`: a hermeticity trade recorded AS a trade

> ⚑ NOTHING IS COMMITTED AND NOTHING IS STALE. The wheel is built from ../substrate's CURRENT
> sources every fetch … **no vendored binary in this librarian's ledger** (which would merge the
> ledger with its subject, the distinction this repo is organized around) … The cost is the honest
> one: ../substrate must be present beside this repo, and this build reaches into it -- **a real
> cross-repo build edge, chosen deliberately over a committed artifact.**

⚑ **`LS-05`'s own inference is carried unadjudicated:** *"the build is hermetic **given
`../substrate`**, and not otherwise. Neither vendoring nor a registry — a third thing, **and it has
no pin.**"*

### ⚑⚑ `AX-12b` — `SM-07` vs `LS-05` vs `SB-03`: three routes to one shared body, all reasoned, none agreeing

**This is the census's central `§Q`-3 result and no leg could hold it.**

| party | route to substrate's shared code | stated reason | measured cost |
|---|---|---|---|
| `SM-07` | **vendored copies + sha256** | ⚑ *"a symlink crosses a VCS boundary, so a peer's **UNCOMMITTED** edit is executable here at write time"* | ⚑ **detection moves from immediate to opt-in** — *"Vendored, an upstream fix does not arrive at all"* |
| `LS-06`/`LS-28` | **symlink**, then `substrate-tooling` **installed as a package** without un-symlinking | *"the established adoption route (freecell, el-openglo and gabion took the same one), not a copy"* | ⚑ **`LS-06`: the route FAILED and the gate exited 0 = ALLOW** |
| `SB-03` | ⚑ **neither** — untracked in its own tree, *"peers reach it by reading substrate's working tree"* | not a decision; a state | ⚑ *"**a peer cannot fetch it**, which is the specific problem the mtools ruling exists to solve"* |
| `MT-08` | **re-derived from a docstring**, without reading the code | ⚑ *"at the time its modules were untracked and could not be depended on"* | 544 lines, 35 tests, duplicated |

⚑⚑ **`SM-07` records BOTH halves of its trade, which is what makes it a decline with a reason
rather than a preference** — and the sharper half runs against its own choice:

> The same write-time reach that made an in-flight peer regression redden summit's board **is what
> let `--only routes` catch that regression in minutes, while the owning repo's selftest
> structurally could not.**

⚑ **So the symlink's defect and the symlink's value are the same property**, measured from two
sides by two parties who chose oppositely. **Neither is wrong. Both are carried.**

### ⚑ `AX-12c` — `RP-03a`: the read path requires an environment the citing repo does not name

Vantage-local to rosettapkg, and it is the cleanest instance of a class four legs gesture at:

```
$ python3 ~/github/linux-sources/linux_sources/corpora_lib/cli.py --help
ModuleNotFoundError: No module named 'PySquashfsImage'
$ cd ~/github/linux-sources && uv run python linux_sources/corpora list
... (exit 0)
```

⚑ **The dependency IS declared and locked** — `linux-sources/uv.lock:2068` pins
`PySquashfsImage-0.9.0` with a sha256 — **in the other repo.** *"rosettapkg records the invocation
and not the environment, so the instruction as written fails on a bare interpreter."*

## `AX-13` — `§Q`-4 Hermeticity: the gate that passes by NOT RUNNING, found by six of seven legs

⚑ **`§Q`-4 named one shape to look for and every leg with a gate found at least one.** Eleven
distinct instances, carried whole:

| # | leg | the instance |
|---|---|---|
| 1 | `SB-04` | ⚑ **`check_scratch_runtime.py` opens with `import cupy`, prints `SKIPPED (no cupy/GPU)`, exits 0.** A declared Phase A gate that **always passed without executing**. *"A GATE THAT SELF-SKIPS TO EXIT 0 IS WORSE THAN A RED ONE: the roster counts it green, and non-execution is indistinguishable from a clean pass."* |
| 2 | `SB-04` | ⚑ Under `uv run --with mypy`, a bare `python3` subprocess is a **different interpreter** — mypy existed for one and not the other, the parse found no error lines, **and zero keys was banked as clean** |
| 3 | `PK-04` | ⚑⚑ **the execroot's `paperkit/` is a SYMLINK TO THE LIVE CHECKOUT**, so `PYTHONPATH="$PWD"` reads **unstaged sources** — a sandbox escape that passes green |
| 4 | `PK-04` | **73 hand-declared `reads = {…}` fields across 16 `.bib` files** — a closure wrong toward *too small* is a stale green |
| 5 | `LS-07` | **a toolchain-tier verdict survived a changed linter binary** (`A3`) |
| 6 | `LS-08` | ⚑ the same defect one layer up: *"apt overwrites its tarball in place on upgrade, so a same-version security respin can serve NEW bytes under an UNCHANGED `7.0.0-30.30` label"* |
| 7 | `LS-18` | ⚑⚑ *"until now **every commit this hook gated ran LOCALLY SANDBOXED with no BES record: measured, the runs reported `246 linux-sandbox` and zero remote actions**… **THE CONFIG BEING CORRECT AND THE GATE USING IT ARE TWO DIFFERENT FACTS**… A configuration nothing invokes is a claim, not a control"* |
| 8 | `SM-09` | **a hook whose dependency is absent fails OPEN and says so once on stderr** — so an absent `shellcheck` reads identically to a clean tree to anything checking only the exit code |
| 9 | `SM-09` | ⚑ **three `govdoc/*` witnesses ERRORED through fourteen hours of green boards**, while the `capabilities` slice excused them as *"gated elsewhere, run by another slice"* — **and no slice ran them.** *"A deferral is a claim about a runner, and nothing checked the runner existed"* |
| 10 | `SM-09` | ⚑ **`FLOOR.md` generated, ungated, twelve days stale** — *"the carve-out was drawn around the VERDICT and silently carried the PROJECTION CHECK out with it"* |
| 11 | `RP-04` | ⚑ **the purest form**: the hermetic half is the half with **no external claims to check**; the half making **100% of the factual claims has no gate at all** |

### ⚑ `AX-13a` — how each leg KNOWS, and the two methods differ

- **`SM-09`: `env -i`.** `citation`, summit's `CLAUDE.md`: *"Verify with `env -i .venv/bin/python
  library/concepts.py --list`, never from an interactive shell, **whose ambient path is the thing
  that hides it.**"*
- **`CO-§Q-4`: the instrument states its own denominator, unprompted, on every run.** `scripts/check
  --only <claim>` prints a **LOAD-BEARING CAVEAT**: *"this run evaluated ONE claim (pressure) of 42.
  It is silent on every other claim, and on any subject absent from `host/*.tsv`."*

### ⚑⚑ `AX-13b` — `CO-`'s fixture seam, and the OVERCLAIM it corrected mid-session

**Carried in full because the correction is the finding.** `CHECK_FIXTURE_ROOT` redirects
*declaration* reads to a fixture tree while the *instrument* keeps resolving against the real repo:
`case "$defined" in scripts/*) base="$REPO" ;; *) base="$ART" ;; esac`.

⚑ **`CO-` first read the `scripts/` carve-out as a surviving escape and proposed narrowing it.** The
operator's correction, quoted: *"Sounds like an overclaim ignorant of bootstrapping."*

> **The maxim "a guard that consults the world it is isolated from is vacuous" is scoped to the DATA
> UNDER TEST, not to the instrument.** Stated without that scope it forbids the bootstrap every
> fixture-based test needs.

⚑ **This is a scoping correction to a maxim three other legs operate under**, and no other leg
carries it.

### ⚑ `AX-13c` — `LS-`'s tier model, its ARMED post-filing append, and my ruling on `§D`.2

**The leg offers this block for refusal. ⚑ I ACCEPT IT, and here is the reasoning.**

`§D`.2 forbids **rewriting** a filed leg after the freeze roster accounted it, because *"rewriting a
filed leg after the roster has accounted it is amending the record behind the accounting."* The
block itself states the test and volunteers the adverse reading:

> ⚑ **Stated rather than assumed, because I am the party who wrote `§D`.2 and the party it would
> now inconvenience.** If the apex judges an append to be an amendment, **discard this block and the
> leg stands exactly as filed** — the finding it supports was already there, unwarranted.

**My ruling: this is an APPEND, not an amendment, on four measurable grounds.**

1. **No prior text is altered.** I read the leg whole; `_tier_exec`'s citation, the 261/246/9/6
   counts, and every `LS-` number are unchanged.
2. **No finding changes, and the change is in the WRONG DIRECTION for an amendment.** The append
   does not strengthen a claim — it supplies a warrant to one that had none, and **the first
   measurement in it CONTRADICTED the leg**: `grep -c 'no-cache' BUILD.bazel → 0`. An amendment
   behind an accounting would not publish its own counter-evidence.
3. **No `LS-` identifier moves**, so no citation into this leg resolves differently.
4. ⚑ **The rule's harm is that a reader cannot tell what was accounted. Here they can** — the block
   is fenced, dated, self-labelled, and states its own prior state (*"correct claim with no warrant"*).

⚑⚑ **And the substance vindicates the acceptance, because the append is a `§Q`-4 finding in its own
right.** The markers are applied inside `_tier_exec` at **rule evaluation**, not written into the
BUILD file — *"so a reader checking the generated graph for them finds nothing and would be right to
doubt the leg."* Armed at the action, which is the interface that decides:

```
ExecutionInfo: {local: 1, no-cache: 1, no-remote: 1, no-sandbox: 1}
```

> ⚑⚑ **But it held on a source quote until now** — `_tier_exec`'s body is the *producer*;
> `ExecutionInfo` on the action is the *consumer*… **A correct claim with no warrant is
> indistinguishable from a lucky one until someone runs the query.**

⚑ **This is `A2`'s mechanism arriving as a method**, and it is the third leg (with `PK-05` and
`CO-`'s `cquery` note) to reach *the action is the interface that decides*.

**Bound on my ruling:** ⚑ **I am ruling on ONE append whose author labelled it and offered
refusal.** This is **not** a general licence to append to filed legs, and I record that an
unlabelled append discovered later would be indistinguishable from an amendment — which is exactly
`§D`.2's point. **The rule is unweakened.**

### ⚑ `AX-13d` — `MT-04`: the sandbox is hermetic AND mounts five host directories

```
build --experimental_use_hermetic_linux_sandbox
build --sandbox_add_mount_pair=/bin   /usr   /lib   /lib64   /etc
```

⚑⚑ *"This is the honest answer to 'what can your build reach that it does not declare': `/usr` and
`/bin`. That is how `pandoc` and `shellcheck` are found."*

⚑ **And the reason the flags are UNCONDITIONAL is a finding no other leg holds:** *"sandbox flags
are **not part of the action cache key**, so a config-gated hermeticity setting would let a
differently-configured peer populate the cache with verdicts computed under different rules."*

⚑ **The gap `MT-04` has not closed, declared deferred:** `pandoc`/`shellcheck` should be a toolchain
tier, *"and adding a stamped toolchain now would either force a premature `--stamp` or produce an
input nothing keys on."*

## `AX-14` — ⚑⚑ `§J`: DID ANY LEG REASON FROM THE WITHDRAWN CAUSE? — MEASURED, and the answer is ONE

**`§J` binds me to check this and the run file says it could not**: *"this dispatcher cannot
enumerate who read what… so the population that may have acted on it cannot be measured, only
warned."* ⚑ **I can measure it, because I hold all seven legs and they do not.**

**Instrument:** `mdstruct grep -i 'valkey'` and `-i 'ghost'` over each leg, plus a `grep -ril` sweep
of the directory. **Denominator: 7 of 7 legs. Reader: `mtools/mdstruct/.venv/bin/mdstruct` (grep
mode) + GNU grep 3.11. Positive control: the sweep returns three files, so the reader sees the
spelling in this corpus.**

| leg | hit | verdict |
|---|---|---|
| `LS-` `§Q-10` | ⚑ **YES** — *"Per §X the executor is degraded (**ghost Valkey shard**)"* | ⚑ **THE ONE INSTANCE. See below.** |
| `SB-01` | `valkey` — **the pip package**, installed by hand, named in no manifest | ⚑ **NOT an instance.** Unrelated `§Q`-1 finding sharing one word. A term-filtered sweep would have glued them; see `AX-02` |
| `CO-01` | the withdrawal itself, with the measurement | **the source of the correction, not a consumer** |
| `PK-`, `MT-`, `RP-`, `SM-` | none | clean |

### ⚑ The single instance, read precisely — and `§J`'s own distinction holds

`LS-`'s `§Q-10` secondary paragraph:

> ⚑ **Secondary, and possibly dominant right now:** the pre-commit runs `--config=remote` with **no
> local fallback**, so an executor outage makes every commit **refuse**. Per §X the executor is
> degraded (ghost Valkey shard). `inference`: **this repo is fail-closed onto a known-degraded
> shared service, by deliberate design** — and per §X that is environmental, not evidence about this
> configuration.

⚑⚑ **`§J` asks whether a leg reasoned FROM THE CAUSE or FROM THE GUIDANCE. This leg reasoned from
the GUIDANCE and cited the cause parenthetically.** The load-bearing clauses are *"the executor is
degraded"* (the **symptom**, which stands) and *"that is environmental, not evidence about this
configuration"* (the **guidance**, which stands and is quoted almost verbatim from `§X`). ⚑ **The
words "ghost Valkey shard" appear inside a parenthesis and no inference depends on them.**

**Therefore:** the finding is **unaffected**; the **citation** is stale. ⚑ **Per `§D`.2 the leg is
not to be amended, and it does not need to be** — the correction belongs in how the apex reads, and
it is here: *read `LS-`'s parenthetical as naming the withdrawn cause, and read the surrounding
inference as resting on the symptom, which `CO-01` re-measured and confirmed.*

⚑ **`§J`'s bound was honest and slightly pessimistic.** The run file said the population *"cannot be
measured, only warned."* **It can be measured — from the apex, and only from the apex, because the
apex is the first party to hold every leg at once.** *That is a small vindication of running phase 2
at all: the census's own unmeasurable remainder was measurable from the glue.*

## `AX-15` — `§Q`-5 Build design: four graphs, two boards, and one repo with neither

| leg | the unit | cached? | remote? |
|---|---|---|---|
| `PK-05` | ⚑ **126,657 actions configured**, MEASURED from a live run | records-as-deps: a child's verdict is a **File**, so an action input | **BES only.** `--config=mutant` is one line and pulls in neither cache nor executor |
| `SB-05` | ⚑ **TWO builds, and they are unrelated** — Agda: one flat import-DAG makefile over ~3.5k modules, `make -j` self-throttling through `membudget run`. Python: **no build graph at all** | `.agdai` mtime; **nothing else caches** | ⚑ **none.** `bazel_emit.py` emits calls loading a `//bazel:agda.bzl` **that does not exist** — *"Whether the emitted text builds is UNMEASURED"* |
| `CO-§Q-5` | 2 `BUILD.bazel`, **projected** from `check --list` (42 claims) + 76 arms | 3 tiers | **yes**, fail-closed |
| `MT-05` | **42 rules, 34 test targets** | ⚑ *"nothing is deliberately uncached"* | unconditional `build` lines, not `--config` |
| `LS-`§Q-5 | ⚑ **`BUILD.bazel` is 456,436 bytes and GENERATED** — 261 `pk_cmd`, 13 slices, 3 staleness checks | 246 sandbox / 9 toolchain / 6 local — **94% hermetic** | yes; `LS-11` witnessed it |
| `RP-05` | ⚑ **no build.** One command, no arguments | ⚑ *"Nothing is cached **because nothing is expensive**"* — the honest "why not" | not on the executor, **and unaffected by its degradation** |
| `SM-10` | ⚑ **no build. A BOARD, discovered rather than declared** — 19 slices, one file each, from a directory | ⚑ **nothing, deliberately** | ⚑ **nothing to submit** — *"it has no unit of work larger than a subprocess"* |

### ⚑⚑ `AX-15a` — `SM-10`: the cost of not caching, priced by nobody

Carried verbatim because summit **states the trade and refuses to defend it**:

> ⚑ **Nothing is cached, deliberately.** Every slice recomputes from the tree on every run, because
> **this repo's governing rule is that nothing records status** — an ask is OPEN exactly when its
> check exits non-zero, recomputed every run. **A cache is a recorded status with a shorter
> half-life.**

> ⚑⚑ **The cost is real and I state it rather than defend it:** a full board takes minutes, most of
> it subprocess spawns, and it is run dozens of times a session. **`§X` says the binding constraint
> on this host is CPU.** So summit's design *converts the machine's scarcest resource into the
> property it values most*, and it does so without measuring what that costs. **inference: I do not
> know whether that trade is correct; I know it was never priced.**

⚑ **This is the only leg to name a cost it imposes on the SHARED host and decline to justify it**,
and it lands directly against `§X`'s CPU finding and `PK-10`'s 2h28m gate. **Carried unadjudicated.**

### ⚑ `AX-15b` — `PK-05`: the heap ceiling tracks GRAPH SIZE and nobody re-derived it

> **CITATION:** *"the ceiling tracks GRAPH SIZE and **nobody re-derived it when the graph moved**.
> The next arc that adds modules moves it again."*

⚑ **The graph SHRANK ~17%** against the last recorded figure (126,657 measured vs. 152,367 recorded
2026-08-31), **and the comment predicted growth.** *"A ratchet that only clicks upward records a
high-water mark, not a size."*

⚑ **Cause deliberately unattributed by the leg** — *"attributing the delta would repeat the
inference being corrected."* **Carried as an open question; I resolve nothing.**

### ⚑ `AX-15c` — `LS-11`: remote execution witnessed for the first time, and it had never worked

```
  P  --config=remote                          -> 11 processes: 9 internal, 2 REMOTE
     (re-run)                                 -> 3 processes: 2 REMOTE CACHE HIT
  F  --config=remote --remote_executor=:39999 -> Connection refused, exit 34
  C  no --config=remote                       -> 1 linux-sandbox
```

> ⚑ THE F-ARM IS WHAT MAKES THE P-ARM MEAN ANYTHING, and it took three attempts to make honest: at
> a dead endpoint bazel first reported `12 action cache hit` and then `1 internal` — **GREEN both
> times, having never contacted the executor.**

⚑ **`MT-04` F-armed the same property independently** — *"a dead cache endpoint produces `Failed to
query remote execution capabilities: Connection refused` — it refuses rather than degrading"* —
**and `CO-§Q-5` ran the third arm**, `bazel test //:gate --config=remote --nocache_test_results`,
witnessing attempt 1 fail and attempt 2 pass with 3 remote. ⚑ **Three legs, three independent
F-arms, on one shared executor.**

### ⚑ `AX-15d` — `LS-13`, `LS-14`, `MT-05`: three vantage-local build findings

- **`LS-13`** — `--remote_instance_name` partitions the cache; **four-armed with a control** proving
  the probe *can* detect a hit under the same foreign name. *"Without a control … 're-executed' and
  'my probe is broken' are indistinguishable."* ⚑ `testimony`: *"MTOOLS MEASURED THE OPPOSITE AND
  HAS SINCE REVERSED IT … **NEITHER OF US CAUGHT OUR OWN** — which is the argument for publishing a
  rule where a DIFFERENT party reads it."* ⚑ **`MT-`'s leg does not report this reversal**, so I
  hold one side only. Carried as testimony, `AX-23`.
- **`LS-14`** — ⚑ **a null result from a well-run probe.** *"I built an instrument to detect a
  distinction that does not exist, then reported the null result as a bound on my ACCESS rather than
  on the QUESTION … **a null result from a well-run probe is evidence the QUESTION is wrong at least
  as often as it is evidence the ACCESS is short. Ask what would DIFFER before building the arm.**"*
- **`MT-05`** — ⚑ **granularity is the open defect.** 34 test targets cover **192 test functions**.
  *"An action's verdict should range over exactly its declared inputs; a module-grained test target
  violates that."*

## `AX-16` — `§Q`-6 Test design: what a test IS, seven answers

| leg | a test is | falsifiable? |
|---|---|---|
| `PK-06` | ⚑ **a CLAIM in a `.bib`** — 49 warrants, 9 files | ⚑⚑ **MECHANISED: a mutation sweep, 8,114 `Ζ·eval` cells.** A claim whose verdict does not change under mutation is **indeterminate, not passing.** Ladder: `broken −1 · vacuous 0 · indeterminate 1 · existence 2 · behavioral 3 · imported 4`. ⚑ Every tool ships ⟨P, F, δ⟩ |
| `SB-06` | an **arm**: `def <name>(out: list[str]) -> int`; 409 suites, **1,909 arms** across 189 | ⚑ **a three-way split, honestly.** `1,277 one-claim · 616 several · 11 silent · 5 UNDECIDED`. Registration **probes polarity** — a `refuses:` witness exiting 0 today is refused at filing. ⚑ **But `standing` witnesses remain unfalsifiable by construction, and they are the largest kind** |
| `CO-§Q-6` | a **claim with a tier**, 42 of which 35 can set nonzero exit | ⚑ **fixtured, 76 arms in three provenance kinds**: `shipped` 15 (git-verified) · `guard-added` 19 (git-verified) · `process` **42 (declared, NOT git-verifiable)**. ⚑ *"The `process` tier is the honest one and it is the largest… rather than borrowing the verified column's credibility"* |
| `MT-06` | ⚑ **192 tests : 192 warrants, 1:1, gate-enforced** | ⚑ **both, and the split is the finding.** 58 docstrings name an arm; 3 modules exist solely to prove a gate can fail. **The remaining ~134 are observed-to-pass** |
| `LS-16` | a **warrant** (42 `@misc`) · a **gate slice** (13) · a **tool selftest** | ⚑ **PROVEN by mutation**: *"`--mutate` re-runs each predicate where its claim is FALSE and reports any mutant that SURVIVED — **a predicate no mutant breaks is decoration.**"* Two mutation kinds: corpus bytes **and this repo's own tool source** |
| `RP-06` | ⚑ **a break-matrix**, no framework, no assertion library | ⚑ **internally yes, externally no.** The 12×12 matrix is a refutable prediction. ⚑⚑ *"the entries' claims about the world are neither… a **proof discipline over its model and no test discipline over its evidence**"* |
| `SM-11` | ⚑ **a witness, not a test.** *"A scan whose all-clear has never been shown to differ from its found-something is not a measurement"* | every slice carries a T-arm **and an F-arm**, and the F-arm is the one that matters |

### ⚑ `AX-16a` — `LS-16`'s no-op mutant, and the state that reads as DETECTED

> ⚑ A MUTANT WHOSE `old` IS ABSENT IS A SILENT NO-OP, and it reads as DETECTED … Either way the line
> claims a discrimination never exercised. **Cheap to decide here and impossible to notice from the
> output.**

Verdict vocabulary is **five-valued**: `HOLE`, `INVALID`, `SKIP`, `UNAVAIL`, `ok`; an uninterpretable
arm is refused — *"SKIP — fails unmutated, so mutants are uninterpretable."*
⚑ **`LS-16b`: every slice refuses an empty population** — *"a search that found nothing is BROKEN,
not clean. Each slice states `n of m` and fails when m is zero."*
⚑ **`LS-16c`** — one of the four headings substrate's mdstruct drops: the build system's own
documentation is gated by the build system, via `traces:<path>#<needle>`, **declaring its own
honesty tier**: *"a `traces:` check proves the claim is RECORDED where it says, **NOT that the
mechanism is globally proven**."*

### ⚑⚑ `AX-16b` — `SM-11`: three consequences, and one is a comparison against a peer

- ⚑ **A gate that only ever catches other people is a gate nobody has tested.** Three of summit's
  gates caught *summit* in one session. ⚑ **The contrast is measured, and it names a party on this
  roster:** *"paperkit's 21 boundary suites were green for their entire existence **and could not
  fail**."* ⚑ **`PK-`'s own leg does not report this**, so it is carried as **one-sided testimony**
  in the divergence register at `AX-20`.
- **The linter caught a tautology in one of summit's own T-arms** — `same == same`, PLR0124. *"A
  T-arm that cannot fail is the same defect as an F-arm that cannot fail, and easier to write by
  accident."*
- ⚑⚑ **A witness of summit's PASSED against a live defect** (`SM-06`).

⚑ **And `SM-11` names a population it refuses to estimate**, which is `§10` discipline applied to
its own strength: *"I do not know how many of summit's 19 slices have F-arms that have ever fired on
a real defect rather than a synthetic one. I know several have; I have not censused it, and 'I
checked and found none' is a count of what the query could see. **Naming it rather than estimating
it.**"*

## `AX-17` — ⚑⚑ `§Q`-8 WHAT WAS RE-DERIVED — the census's own highest-value question

**`§Q` calls this *"the highest-value item in the whole census and the one nobody records."* All
seven legs recorded it.** Carried whole, by leg, with nothing dropped.

### `PK-08` — paperkit

- **A per-cell venv + wheel install** — built because `pk_cmd` runs *arbitrary user-authored shell
  strings* where no runfiles tree exists. ⚑ **A peer read this and correctly declined it**:
  `py_binary` is the stronger form where you have one, and wheel-extraction-as-install holds only
  under `dependencies = []`. *"The re-derivation is real and the shared alternative did not cover my
  case — that is the honest shape of this answer."*
- **An action-idempotent scratch claim** — ⚑ *"This is a lease, hand-rolled, and `membudget`'s
  `claim:<tag>` is the same primitive. **I did not know that when I wrote it.**"*
- ⚑ **A liveness discipline in PROSE where an instrument exists** (`dont-edit-during-build`:
  *"check `pgrep bazel` before ANY edit"*) — *"**It failed today, by its own author** — I edited
  `tools/wheel.py` 70 seconds into a live gate. **A rule obeyed by remembering is not a mechanism.**"*
- **A stale-pointer class, twice**: `.githooks/local.env` asserting *"BES (:1985) did NOT move;
  verified open"* while `:1985` measured **closed** — ⚑ **a stale claim carrying its own
  verification**, *"which is why it survived a reader applying verify, don't trust."*

### `SB-08` — substrate

- **`membudget`'s load-average predicate** — built because `make` has no load-aware throttle. ⚑ *"It
  is untracked, so the other three could only vendor or re-derive it."*
- **A licence-header reader** (`file_header.py`) — *"No reader owned header presence, and the reader
  I reached for could not see comments."*
- **A cross-module constant resolver** (`imported_constant.py`) — the insert-target resolver
  followed intra-file bindings only.
- **A claim counter** (`arm_claims.py`) — the arm-shape reader answers rewrite cost, not claim count.
- ⚑⚑ **Structural readers generally — ~100 tools, ~619 modes.** *"This is the largest re-derivation
  in the leg **and I cannot bound it**: I do not know which of these a peer already had."*
  **→ `AX-25`.**

### `CO-§Q-8` — cassian-observability

- **`scripts/resource-lease`** — a pool lease generalizing membudget from *exclude-a-named-artefact*
  to *allocate-from-a-pool*. ⚑ Re-derived because *"membudget is **not installable**."*
- **A structural-query toolkit** (`mdstruct.py`, `pycodemod.py`, …) plus harness hooks — ⚑ *"this is
  precisely the `mtools` intake case."*
- **`scripts/actions-tsv2jsonl`** — a TSV↔JSONL converter with a round-trip oracle.
- **A cocycle checker over a half-edge dependency graph** (`scripts/actions-cocycle`).
- **`cputimeout`** — CPU-time-based timeout, `timeout(1)`-compatible.

### `MT-08` — mtools

- **`ratchet/`, 544 lines, 35 tests.** ⚑ **substrate already had it and mtools knew** — built from
  substrate's *docstring warning* without reading its code, *"because at the time its modules were
  untracked and could not be depended on."* **→ `AX-21`, the divergence register.**
- **`pytest_main.py`** — because `main = <test module>` runs the module as a script; ⚑ **measured: 23
  targets reported green over ZERO assertions.**
- **`blockers.sh`** — *"a re-derivation procedure, because a claim with no command attached is never
  re-checked."*

### `LS-19`–`LS-23`, `LS-28`, `LS-29` — linux-sources

| # | artifact | status |
|---|---|---|
| `LS-19` | `tools/verb.bzl` | **Adopted from paperkit, reduced** — `pk_file`/`pk_result`/`pk_agree` declined by scope. ⚑ *"But `_tier_exec`'s three tiers are this repo's own. **Apex: does any peer have a tier model, and is it these three?**"* ⚑⚑ **ANSWERED at `A1`: YES — paperkit and cassian both, and they ARE these three. The tier model is paperkit's, 68 days older.** |
| `LS-20` | `import_closure.py` | **Re-derived**, crediting substrate for the measurement; *"substrate held the number; the closure computer did not exist. **That is a defect report about substrate.**"* |
| `LS-21` | `gen_gate_build.py` | Re-derived from substrate's makefile-generator pattern. ⚑ *"The 1,905-line completeness net is entirely local… **If any peer has a subprocess-completeness net, that is ~1,900 duplicated lines.**"* ⚑⚑ **ANSWERED: no peer reports one. `CO-`'s and `PK-`'s generators emit from a roster; none enumerates subprocess spawners. The net is unduplicated — and therefore unshared.** |
| `LS-22` | `check_status.sh` bytes-stamping | ⚑ **The ARM propagated from paperkit; the FIX was re-implemented here.** Rule: *"Run the arm PER KEY, not per mechanism."* |
| `LS-23` | `mdstruct.py` / `pycodemod.py` | **Borrowed by path.** ⚑ *"A hard cross-repo path dependency **inside a hook's routing table**, unpinned. A peer moving `scratch/` makes this repo's guard name a tool that does not exist."* ⚑⚑ **`SM-04` measured exactly this happening to a different file — see `AX-22`.** |
| `LS-28` | the four hooks | **Adopted by symlink** — *"the established adoption route (freecell, el-openglo and gabion took the same one)."* ⚑ **Three repos on that route are not on `§R`.** |
| `LS-29` | `hook_gate_running`, `hook_pycheck` | **Held as CODE deliberately** — *"mat260's ruling is that residency of a capability whose tree may be erased means holding the CODE."* ⚑⚑ **`mat260` is RETIRED per `§X`, and its ruling is load-bearing in this repo's gate today.** |

### `RP-08` — rosettapkg

- **`RP-08a` — ⚑ A VERIFIED LOCKFILE, RE-DERIVED AS PROSE.** *"A lockfile existed; a lockfile was
  re-derived, in a format nothing can verify."* Witness at `RP-W1` / `AX-10a`.
- **`RP-08b`** — el-atlas's depsort, **ported rather than imported**; refuses the collapse per §B4.
- **`RP-08c`** — a space-manifest + fingerprint discipline, re-implemented locally. *"Third
  re-derivation of the same neighbour's work in one small repo."*
- ⚑ **`RP-08d` — MY OWN EARLIER REVIEW RE-DERIVED TWO CONCLUSIONS THE REPO ALREADY HELD.** *"…and
  reached the first one more sharply."* **Filed as a re-derivation because it is one, and because it
  is evidence that this repo's findings are not discoverable even to a reader inside the same
  session."*

### `SM-13` — summit ⚑ *(invisible to the routed reader; recovered per rev 37)*

1. **`vendor_hooks.py --diff`, built today.** The manifest header had always ended *"Regenerate with
   `--apply` after reviewing the upstream diff"* — ⚑ **and the tool had three modes, none of which
   showed a diff.** *"So the instruction routed its reader to `diff`, which summit's own hook refuses
   over a `.py`."* ⚑⚑ **A documented precondition with no mode behind it is an instruction to break a
   rule** — *"and the rule held: four files sat drifted while the decision waited on a review nothing
   could produce."*
2. **A note-tail parser, THREE times.** ⚑ *"The type checker is what surfaced it, not review… **a
   type error over a duplicated parser points at the duplication.**"*
3. **`stubs/` for paperkit** — ⚑ *"Two repos wrote stubs for one engine, in different shapes, neither
   knowing."* **→ `AX-02`, non-identified.**
4. **`scripts/slices/interpreter.py`** — *"nothing in the ecosystem measures whether a venv is built
   from the interpreter its config pins."*

### ⚑⚑ `AX-17a` — what the glue makes visible that no leg could see

**Three cross-leg results, computable only from the union:**

1. ⚑ **`membudget` is held by six of seven legs and NONE of them has it as a dependency.** One
   authored it and cannot ship it (`SB-03`, untracked); one generalized it not knowing
   (`CO-§Q-8`); one re-derived its primitive not knowing (`PK-08`); one deleted it with a reason
   wrong on one axis (`PK-09`); one declined it with a mechanism argument and a §5 control
   (`LS-27`); one declined a peer's *replacement* for it (`MT-09`); one declined it with no record
   at all (`RP-09`). **Seven relationships to one artifact, six of them undocumented on the
   artifact's side.**
2. ⚑ **A structural-query toolkit was built or borrowed by FIVE legs** — `CO-` (re-derived),
   `SB-08` (~100 tools/~619 modes, unbounded), `LS-23` (borrowed by path), `SM-04` (reached by
   relative path), `MT-` (**owns `mdstruct/`, a third implementation**). ⚑⚑ **And revs 16/36/37
   establish that TWO of these implementations diverged in capability AND in defect, mid-census, in
   the instrument every reader was routed to.** **→ `AX-18`.**
3. ⚑ **`[[tool.mypy.overrides]]` was declined by three legs on one argument** (`A8`) — and rev 27(b)
   measured summit's two remaining blocks **DEAD**, their premise having expired at install without
   announcing it. *"An override whose premise expires does not say so; only re-measuring does."*

## `AX-18` — ⚑⚑⚑ THE CENSUS'S OWN INSTRUMENT IS A `§Q`-8 ANSWER, GENERATED WHILE THE CENSUS RAN

**`§G` says: *"For the apex: this is evidence, not an aside."* I carry it as a first-class glue
entry.** Two implementations of one tool, diverging in **both directions at once**:

| | `substrate/scratch/mdstruct.py` | `mtools/mdstruct/` |
|---|---|---|
| **who routes to it** | ⚑ `hook_structural_query`, fleet-wide, as *"the tool that owns"* any `.md` | `mtools` itself |
| **spelling** | flags (`--headers`) | subcommands (`spans`) |
| **column-scoped predicate** (rev 16/17) | ⚑ **absent** | ⚑ **present**, built mid-census |
| **apostrophe heading drop** (rev 34–37) | ⚑ **PRESENT — 42 of 46 on `LS-`, 19 of 21 on `SM-`** | ⚑ **absent — 46 and 21** |

⚑⚑ **One split, both halves measured, both found by the census while it ran.** `§G` records a
**capability** living in the copy the routing does **not** name; rev 37 records a **defect** living
in the copy the routing **does** name.

⚑ **The cost, had rev 37 not landed:** `LS-09`, `LS-16c`, **`LS-17`**, `LS-`'s reader-blind note,
`SM-03` and **`SM-13`** would be absent from this document with no gap visible. **`SM-13` is
summit's `§Q`-8 answer** — the question `§Q` calls the highest-value in the census — **and `LS-17`
is an instrument-integrity finding.** Both are in the glue above only because the instruction was
followed.

⚑ **And rev 35 records that BOTH of the tool's own guards certify the corrupted output**: `lint`
reports no shape findings, `roundtrip` reports it round-trips identically. **A short file that
parses looks exactly like a correct one.**

⚑⚑ **Rev 38 is the methodological finding and I carry summit's formulation verbatim:**

> **when two careful parties contradict each other flatly, the likeliest explanation is that they
> measured different objects**, not that one was sloppy.

⚑ **`mtools` measured its own binary, found zero drops, and asked `summit` to retract — including
asking that the dispatcher not be told.** Summit measured before complying and found the cause. *A
true measurement of one binary became a false inference about another, in the direction that would
have retracted a real finding.*

## `AX-19` — ⚑⚑ `§Q`-10 WHAT BINDS: SEVEN ANSWERS, **FIVE TYPES**, AND THE ARITHMETIC IS UNDEFINED

**`§T` binds me: these are TYPES, not magnitudes. I do not rank, average, or max them.** `§T`'s own
escalation rule: *"If a third leg answers with a third type, that is probably the finding rather
than the outlier."*

⚑⚑ **There are FIVE types across seven legs. `§T` anticipated a third and got five.**

| leg | the answer | ⚑ TYPE |
|---|---|---|
| `LS-`§Q-10 | six `local`-tier targets — the uncacheable, unremotable serial tail. `gate_differential.py` **122s**, `participants` **60s**; `//:gate` critical path a single action at **407s** | **CORPUS** — *"six verdicts are definitionally host-coupled, and this repo has correctly refused to cache or remote them. The constraint is a consequence of a correctness decision"* |
| `CO-§Q-10` | ⚑ **the co-sign boundary.** No `sudo`; root work is prepared here and executed by a human. Gate: **`Critical Path: 0.36s`**, 8 processes | **PERMISSIONS** |
| `SM-15` | ⚑ **summit's instruments and its subjects are the same objects**, so a defect in a shared body takes down the instrument that would report it. *"one unguarded import in a peer's file made 19 slices into a traceback — and the slice whose job is reporting that hooks are armed was itself unable to load"* | ⚑⚑ **REFLEXIVITY** — *"Every other constraint I have is recoverable by running something; this one removes the ability to run the thing that would tell me"* |
| `MT-10` | ⚑ **nothing outside this repo can depend on anything inside it.** No remote, no published package, no install path. `hooks` declares a console script **no consumer consumes** | **DISTRIBUTION** — *"packaging is the binding constraint, and every hermeticity or granularity item below it is a refinement of a thing nobody can import"* |
| `SB-10` | ⚑ **the per-file gate's all-or-nothing grain over three monolith files.** `findings.py` carries **8,169 ruff findings**; **four correct repairs were blocked today** | **GRAIN** — a fifth type, and it is *"the gate is right and the constraint is real"* |
| `PK-10` | ⚑ **the commit queue.** 46 files staged, gate takes **2h28m+**, every defect restarts it. **Three runs today; zero commits.** `HEAD` is from 2026-09-02 | **QUEUE / LATENCY** — arguably `LS-`'s CORPUS type at a different magnitude, ⚑ **but the second-order binder is DIFFERENT in kind**: *"I cannot read my own build's outcome reliably"* |
| `RP-10` | ⚑ **corpus read time — a HUMAN reading source through a mount** | **HUMAN THROUGHPUT**, and its second-order binder is **DISCOVERABILITY**: *"every finding in this repo is undiscoverable from outside it… which is why `RP-08d` happened inside the same session"* |

⚑ **Five of seven legs explicitly say NOT CPU** — `SB-10`, `MT-10`, `CO-`, `PK-10`, `RP-10` — and
`§X` says the host binds on CPU. ⚑⚑ **That is not a contradiction: `§X` warns that a per-repo answer
to "what does my build need" is a measurement of the BOX, not of the repo, and five legs
independently refused to report the box.** `RP-10` states it most directly: *"§X states the host's
binding constraint is CPU… That measures the box, and §X warns a per-repo answer is a measurement of
the box rather than the repo."*

⚑⚑⚑ **AND THE ONE LEG THAT DOES CONVERT CPU INTO ITS OWN CONSTRAINT IS `SM-10`, WHICH PRICES IT AT
ZERO AND SAYS SO** — *"summit's design converts the machine's scarcest resource into the property it
values most, and it does so without measuring what that costs."* **A leg reporting the box would be
an error; a leg spending the box unpriced is a finding, and only the glue holds both.**

### ⚑ `AX-19a` — how the type-distinction was FOUND, carried because it is the transferable half

**`CO-`'s account, which `§T` calls the part that generalises:**

> `linux-sources` measured a 400s tail and read it as its own binding constraint — correctly.
> `cassian` measured 0.36s and, **rather than concluding one repo was slow and the other fast, asked
> what kind of thing each number was.**

⚑ *"would not have had it without your answer differing from mine."* **The finding is a property of
the RELATION between two legs, and no single-vantage census could hold it.**

### ⚑ `AX-19b` — a capability recorded and DELIBERATELY NOT exercised

`CO-`'s 15s gate **could** run the post-test-failure arm `LS-15` could not reach. It **declined**:

> Doing work in my tree at a peer's suggestion is fine; doing it **AS a test bench for another
> repo's config question** is outward-facing work that belongs to my operator, not to me.

⚑ **A declined-and-named capability is a different artefact from an unnoticed one.** Carried; **I do
not act on it either** — I hold no leg and no operator's authority, and `§I` is about capabilities
one holds, not authorizations one lacks.

## `AX-20` — ⚑⚑ THE DIVERGENCE REGISTER — both branches standing, denominators and instruments named

> ⚑ **Resolve nothing that the witnesses do not resolve.** — `apex.md` §A2

### `AX-20a` — ⚑⚑ `--remote_local_fallback`: opposite policies, one shared executor

| branch | leg | denominator | instrument | reader-blind |
|---|---|---|---|---|
| **SET, both configs** | `PK-09` | `.bazelrc:247`, `:283` | `grep -rn` (ugrep 7.x); ⚑ **`apex-measured`: I counted 4 occurrences in paperkit's `.bazelrc`** | ⚑ `PK-` declares a `//:hook` was **running throughout the filing**; two figures read from a live run |
| **SET NOWHERE**, by an operator ruling of 2026-09-04 | `CO-§Q-5` | `.bazelrc:43` | `grep`; the setting's absence F-armed by a live `--config=remote` run | `scripts/mdstruct.py` **broken in that checkout** (`ModuleNotFoundError: climode`) — all markdown facts from `Read` |
| **REMOVED**, and the removal was the instrument | `LS-12` | `.bazelrc` | three-armed live bazel | no bazel invocation during the survey except the named ones |
| **NOT SET**, F-armed | `MT-04` | `.bazelrc`, 123 tracked files | dead-endpoint probe | untracked tree not searched |
| **n/a — no bazel** | `SB-09`, `SM-10` | — | — | `SB-09`: *"not declined by me; substrate has no bazel config to decline it in"* |
| **undocumented decline** | `RP-09` | 8 of 8 files | `find`/`grep` | ⚑ *"I can find no record of anyone considering and refusing them, which is different from refusing them"* |

⚑ **THE DISCRIMINATOR IS A DATE AND NOBODY HAS IT.** `CO-` states the limit: *"I cannot tell from
here whether paperkit's setting predates the ruling."* **A setting that predates a ruling is a stale
config; one that postdates it is a divergence — different findings, different repairs, and nothing
available to a surveyor distinguishes them.**

⚑⚑ **I did not resolve it, and I record WHY, because I could have been tempted.** `§Y` binds: the
origin must be found in the authoring tree, and `git log` on `.bazelrc` would date the **line's last
touch**, not the **decision** — a consolidation-trap at the granularity of a hunk. ⚑ **`PK-09`'s own
framing makes the resolution moot for the repair anyway:** *"Removing it is not one change. paperkit
declares **zero `platform()` targets**, so `--config=remote` resolves against the default host
platform. The fallback must come off **last**, after a platform is declared, or a red gate gets
attributed to the wrong cause."*

⚑⚑⚑ **AND THE STAKE IS NAMED BY `§P`, WHICH I CARRY:** *"if paperkit's fallback is live, that repo's
remote-execution greens are subject to the same doubt"* — because `LS-12` measured that the flag
**caught the analysis failure and returned green with zero remote actions**. ⚑ **`PK-10` reports
`HEAD` at 2026-09-02 with zero commits today across three gate runs, so no green from that config
has landed in the window either way.** *Both branches stand. Neither is preferred.*

### `AX-20b` — ⚑ paperkit's boundary suites: could they fail?

| branch | source | class |
|---|---|---|
| ⚑ *"paperkit's 21 boundary suites were green for their entire existence **and could not fail**"* | `SM-11`, stated as a measured contrast | **one-sided.** Summit's instrument and denominator are not given for this claim; it is offered as a contrast, not a census of paperkit |
| `PK-06`: falsifiability is **mechanised** by a mutation sweep, **8,114 `Ζ·eval` cells** measured from a live run; a claim whose verdict does not change under mutation is graded **indeterminate**, not passing | `PK-06` | **the owning party, with a denominator** |

⚑ **These are not necessarily contradictory** — `SM-11` names *21 boundary suites*, `PK-06` names
*49 warrants in `boundaries/warrants.bib`* and a ladder that **explicitly grades some claims
`vacuous 0` and `indeterminate 1`.** ⚑ **A ladder with a `vacuous` rung is a mechanism for finding
exactly what `SM-11` alleges**, so the two could both be true of different populations at different
times. **I resolve nothing: `§D` says the filing parties are unreachable, and no witness in either
leg pins the population or the date.** Both stand.

### `AX-20c` — ⚑ `--remote_instance_name`: mtools measured the opposite and reversed

| branch | source | class |
|---|---|---|
| `--remote_instance_name` **partitions** the cache; four-armed **with a control** | `LS-13` | `citation` + `machine`, four arms, control named |
| *"MTOOLS MEASURED THE OPPOSITE AND HAS SINCE REVERSED IT"* | `LS-13`, `testimony` | ⚑ **`MT-`'s own leg does not report this measurement or its reversal at all** |

⚑ **I hold one side.** `MT-`'s leg is silent on instance-name partitioning; I did not re-sweep its
tree, and `§A6` forbids counting a re-sweep as a second witness. ⚑ **`LS-13`'s own conclusion is the
one worth carrying and it is about the census, not the flag:** *"**NEITHER OF US CAUGHT OUR OWN** —
which is the argument for publishing a rule where a DIFFERENT party reads it."*

### `AX-20d` — ⚑ the two mdstruct implementations (`AX-18`)

**Formally a divergence and formally resolved — by rev 36/38, not by me.** Both branches were true
measurements of **different binaries**. ⚑ **Carried in the register anyway**, because the *resolution
mechanism* is the transferable finding and because rev 38 records how close it came to going the
other way.

### `AX-20e` — ⚑ the `strict=` fan-out default (`MT-08` vs substrate)

Carried at `AX-21`; it is a divergence **between two implementations of one design**, which is a
different shape from a divergence between two legs' claims. **Both stand.**

## `AX-21` — ⚑⚑ `MT-08`: THE MODEL CASE — a re-derivation that produced evidence rather than waste

**Carried whole and separately, because `apex.md` §A3 says an item one leg holds is the highest-value
content in the glue, and this one argues against its own author's convenience.**

> - **Every classification agrees.** Fan-out, 2-old→2-new reorganisation, and a shared rule at an
>   unrelated path partition identically in both implementations — from two derivations sharing **no
>   author, no corpus and no key grammar** (substrate keys `name::path` off a declared schema; mtools
>   keys `path:rule` positionally). **That is stronger evidence than either suite alone.**
> - **They differ on exactly one axis, and it is a defect.** Substrate's fan-out defence is a
>   `strict=` parameter **defaulting off** — measured by running its own `classify`. Mine is
>   unconditional.

⚑ **Substrate confirmed and reported that nothing invokes the reporter at all**, so the exposure is
zero today (**testimony, relayed pre-freeze, disclosed by `MT-`**). ⚑ **`SB-`'s own leg does not
mention this exchange**, so I hold one side; carried unadjudicated.

⚑⚑ **The mechanism was correct and UNREACHABLE — untracked, therefore undependable — so a second
copy was cheaper than waiting.** *"The fix for that class is packaging, which is the `§X` ruling."*

⚑ **This is `LS-10`'s warning satisfied rather than violated**, and the contrast is exact:

> **AGREEMENT BETWEEN TWO INSTRUMENTS THAT SHARE A BLIND SPOT IS THE BLIND SPOT, TWICE** — the same
> shape as the bare platform, which was one habit propagated by copying rather than two independent
> bugs.

⚑⚑ **`MT-08`'s two ratchets share no author, no corpus and no key grammar, so their agreement IS
corroboration; `LS-10`'s two probes shared a habit, so theirs was not.** **The discriminator is
whether the witnesses could have disagreed** — `census-kit` §I2's rule, arriving as a measured
instance in two legs pointing opposite ways. ⚑ **`LS-10` addresses this directly to me:** *"this is a
direct warning to the apex about its own span. Two legs agreeing is not corroboration when both
inherited the same habit."* **Applied: `A1`, `A2`, `A3`, `A9` and `A18` are annotated with whether
the agreeing parties could have disagreed.**

## `AX-22` — ⚑ `§A4` ROSTER: accounting first, then nominations

### `AX-22a` — Freeze accounting, reproduced from `§S` (rev 31)

| party | status | evidence |
|---|---|---|
| `paperkit` | **filed** | `paperkit-deps-build.md` |
| `substrate` | **filed** | `substrate-deps-build.md`, `SB-01`–`SB-10`, against rev 1 |
| `mtools` | **filed** | `mtools-deps-build.md`, `MT-01`–`MT-13`, against rev 1 |
| `rosettapkg` | **filed** | `rosettapkg-deps-build.md`, against rev 6 |
| `linux-sources` | **filed** | `linux-sources-deps-build.md`, `LS-01`–`LS-30`, against rev 5 |
| `summit` | **filed** (rev 30) | `cf69c3a`, `SM-01`–`SM-17`, against rev 21 |
| `cassian-observability` | **filed** (rev 29) | `e21e7f2`, against rev 6 |
| **apex** | this document | holds no leg |

**7 of 7 filed. Zero `declined`, zero `no response`.** ⚑ **`A` is computed over a complete roster as
`§R` stood at rev 31** — and `§N` states the bound on that roster below.

⚑ **Four non-terminal states this run had to invent, and `§S`'s vocabulary could express none of
them** — carried because they are census-methodology findings: `in progress` collapsing *work
incomplete* with *location held* (rev 18); **`STAGED`** — done, permitted, one green gate away (rev
25); a party whose seat existed in a message before it existed in `§R` (rev 22, `SM-`'s `§9`); and
a party absent from `§S` entirely reading as terminal (rev 15's count identity).

### `AX-22b` — ⚑ Nominations, carried as a FIRST-CLASS REMAINDER

**`§N` and `apex.md` §A4: nominations are *"the only mechanism by which the survey discovers its own
index was incomplete."* Nothing here is resolved.**

| nominated | by | reason | ⚑ apex note |
|---|---|---|---|
| `summit` | **`LS-30` · `CO-§R` · `SB-`** — **three legs, three non-overlapping reasons** | live uncacheable build input · the index that answers *"does this already exist elsewhere"* · the only party who can say whether a re-derived capability was already registered | ⚑⚑ **DISPATCHED at rev 21 and FILED.** The nomination mechanism worked end-to-end, once. ⚑ **And `SM-`'s leg vindicates all three reasons**: `SM-13`.3 is a re-derivation summit found by *"going looking"*, exactly the index-shaped gap `CO-` predicted |
| `gcalculus` | **`SB-` · `LS-30`** — two legs | ⚑ *"it rebuilt a pristine copy of substrate's `agda/` tree… and died in substrate's `Foundation` on a `ClashingDefinition` before reaching anything of its own. **A party that builds another party's tree from scratch holds the coldest-start dependency evidence in the ecosystem**"* | ⚑⚑ **THE SHARPEST UNDISPATCHED NOMINATION.** `§Q`-3 asks what happens on a cold machine, **and every leg answered by reasoning about its own tree rather than by HAVING a cold machine.** ⚑ **I confirm this from the glue: all seven `§Q`-3 answers in `AX-12` are counterfactual.** The gap is a property of the roster |
| `earley` | `LS-30` | ⚑ the house lint/type standard `linux-sources` **adopted verbatim** — `[tool.mypy]` and `[tool.ruff]` copied, not an ad-hoc subset | ⚑ **`§N` says weigh this hardest**, as *"the same shape as `§Y`'s consolidation-repo trap, one layer up."* ⚑⚑ **Corroborated from a second leg, which `§N` asked for**: `LS-`'s decline table names *"pylint — **adopted `earley`'s config verbatim instead**"*, and `RP-N3`'s positive control **found `~/github/earley/.github/workflows/ci.yml`** — ⚑ **so `earley` is the only nominated party any leg exhibits an artifact from.** Still one nominating leg |
| `freecell`, `el-openglo`, `gabion` | `LS-30` | the three other repos on the **same hook-adoption-by-symlink route** | ⚑⚑ **`gabion` is independently corroborated twice, neither from `LS-30`**: `CO-§R` names it *"the canonical case of machinery built, then forgotten by its own author"*, and ⚑ **`SM-01`/`SM-03` measure gabion as a live dependency** — six of summit's seven runtime deps are gabion's, and `SM-03` files a defect against its declared floor. **Its nomination is now three-legged** |
| `mat230` / `mat260` | `LS-30` | retired per `§X` — ⚑ **but `mat260`'s ruling on capability residency is load-bearing in `LS-29`'s gate today** | ⚑ **A retired party's directive in force.** `§X` says do not report as live; `LS-29` reports it as load-bearing. **Both stand; I resolve nothing** |
| ⚑⚑ **an EDGE, not a party** — `SM-16` | `SM-` | **No leg was asked: *"what does another repo's build depend on that YOU own and did not tell them?"*** | **See `AX-22c` — the finding, not a dispatch** |
| ⚑ **`~/.claude/skills/`** — `PK-11` | `PK-` | ⚑ **not a repo.** `project-tooling` is a machine-wide statement of which interpreter and package manager a repo should use, **with a measured trap list** | ⚑⚑ **THE SECOND NON-PARTY NOMINATION, AND NO LEG CROSS-REFERENCES IT.** `PK-11`: *"this census will compute its span over six repos while a **seventh document already states the dependency-tooling convention they are all supposed to follow**."* ⚑ **Corroborated from inside a leg without either knowing** — `SM-06` independently measured one of `project-tooling`'s named traps (`AX-11e`) |
| **none** | `MT-`, `RP-` | `MT-`: ⚑ *"`rosettapkg` is a party I have **never interacted with and cannot see**… That is a statement about my reader."* `RP-`: ⚑ **withdrew** its intended nomination — it had read `substrate` as absent from `§R` and corrected itself | ⚑ **Both are honest non-nominations and `RP-`'s is a `§Z` self-correction** |

⚑ **`§N`'s stated weakness is now partly discharged, and I record exactly how much.** `§N` said all
six original nominations came from **one leg** (`LS-30`), *"the weakest possible warrant."* Against
the full seven: **`summit` has three legs, `gcalculus` two, `gabion` three (two of them measured
rather than asserted), `earley` one leg plus two artifacts.** ⚑ **`freecell`, `el-openglo`,
`mat230`/`mat260` remain single-leg, single-party claims.**

### `AX-22c` — ⚑⚑⚑ `SM-16`: THE ROSTER HAS NO SHAPE FOR AN EDGE

**The most structurally important remainder in the census, and it dispatches nobody.**

> ⚑ **The party I would add is `paperkit`, and it IS on `§R` — so my nomination is not a party but a
> CAPACITY nobody was asked for.** No leg was asked *"what does another repo's build depend on that
> you own and did not tell them?"*

**Measured, not hypothesised:** paperkit moved `bibstruct.py` from `paperkit/paperkit/tools/` to
`paperkit/tools/` and **summit's `edges` slice went red with `no such file`** — *"with nothing on
either side declaring the relation. paperkit cannot know who reaches into its tree by relative path,
and I cannot know when it will move."*

> ⚑⚑ **`§R` enumerates *parties*; the missing thing is an *edge*.** A roster of surveyors computes a
> span over what each party holds; **it computes nothing over what each party's holdings depend
> on.** That is `§Q`-2's implicit dependencies at the census's own level.

⚑⚑⚑ **THE GLUE CORROBORATES IT FROM THREE MORE VANTAGES, NONE OF WHICH KNEW:**

- **`LS-23`** predicted this exact failure for a different file: *"A peer moving `scratch/` makes
  this repo's guard name a tool that does not exist."* ⚑ **`SM-16` measured the same class landing on
  `bibstruct.py`** — and `PK-`'s leg **does not mention moving it**, because from paperkit's side
  nothing happened.
- **`MT-03`** holds two **absolute** paths into substrate, one of them in a **test assertion**.
- **`RP-02`/`RP-03a`** depend on `~/github/linux-sources` **at a literal path**, and `LS-`'s leg
  does not report rosettapkg as a consumer. ⚑ **`RP-`'s roster line says so**: *"`linux-sources` IS
  on `§R` but holds **my** dependency machinery — witness supplied at `RP-W1` so the apex need not
  guess."*

⚑ **So the census measured, from four independent legs, that its own index shape cannot express the
relation the subject is about.** *A dependency census whose roster enumerates parties rather than
edges is the finding, and it was found by the survey.*

## `AX-23` — ⚑ CARRIED UNCHECKABLE TESTIMONY — tagged with witness and leg, NOT adjudicated

> **Unverifiable ≠ false.** Each of these is carried because a leg holds it and I cannot verify it
> from the documents I read. **I did not re-sweep any tree to check.**

| claim | leg | its witness | why I cannot check it |
|---|---|---|---|
| ~170 mise shims all dangling at `/snap/mise/203` | `SM-05` | machine, 2026-09-01 | ⚑ the state is gone; `mise reshim` repointed them. **`§D` says the filing party is unreachable** |
| *"MTOOLS MEASURED THE OPPOSITE AND HAS SINCE REVERSED IT"* on `--remote_instance_name` | `LS-13` | testimony | ⚑ `MT-`'s leg is silent on it. `AX-20c` |
| paperkit's 21 boundary suites *"could not fail"* | `SM-11` | offered as a contrast | ⚑ no denominator or date given; `PK-06` reports a mechanism that would find it. `AX-20b` |
| substrate's `strict=` defaults off; *"nothing invokes the reporter at all"* | `MT-08` | testimony, relayed pre-freeze, **disclosed** | ⚑ `SB-`'s leg does not mention it. `AX-21` |
| substrate's header census 431/568 conforming | `MT-`'s testimony section | ⚑ **`MT-` verified the complement independently** (137 refusals in 568) — *"so that one is corroborated"* | the origin figure is still substrate's |
| `mat260`'s ruling on capability residency | `LS-29` | citation appearing in `LS-`'s bytes | ⚑ **the party is retired per `§X`** and cannot be asked |
| the operator's *"I can't tell how many times I've told all of you to improve on and genericize that machinery"* | `CO-§Q-8` | quoted; ⚑ **the same sentence is `census-kit`'s originating grievance** | ⚑ **two independent appearances**, so it is well-witnessed as an utterance; I cannot date it |
| gabion's `ast.Interpolation` / `>=3.11` defect | `SM-03` | machine, 2026-08-31, filed as a friction | gabion is not on `§R` and filed no leg |
| the `//:hook` running throughout paperkit's filing (2h28m at start) | `PK-` disclosures | self-reported | ⚑ **`PK-` marks which two figures came from the live run** — the disclosure is the mitigation |
| ⚑ **a subagent sweep of four peer trees for BUILD generation** | `MT-12` | ⚑ *"Held, unverified by me, **not used** in `MT-12`. Flagged for the apex as an artifact that exists"* | ⚑⚑ **An artifact this census knows exists, has never read, and cannot cite.** Carried as an existence claim only |

⚑ **`MT-`'s testimony section is a model and I say so**, because `§Z` binds me to grade
self-reports in both directions: it **separates what it reproduced from what it relays**, item by
item, and marks two as independently verified. *"Corroboration between witnesses that could not have
disagreed is decoration; the apex needs to know which of mine are which."* **It is the only leg that
did this as a structured section.**

## `AX-24` — ⚑ `§Z` APPLIED: self-grading, verified in BOTH directions

**`§Z` binds: *"a leg may mis-grade itself in EITHER direction; verify self-reported weaknesses on
the same terms as self-reported strengths."*** Five instances found in the legs, and one I add.

| leg | the self-grade | direction | ⚑ verdict |
|---|---|---|---|
| `MT-` `§9`.2 | claimed a **brief §2 violation** that had not occurred; **withdrew it, left it visible** | ⚑ **understated its own standing** | **The withdrawal is correct** (`§Z` rev 4 records the dispatcher's correction). *"A rule cannot be violated by conduct that precedes it, and grading a leg down against one is not rigor — it manufactures a defect the apex must then carry and discount."* ⚑ **I carry NO discount** |
| `CO-§Q-5` | claimed *"the RBE half is cassian's own extension"*; **withdrew on checking the authoring tree** | ⚑ **overstated a strength** | ⚑ **Corroborated by my own measurement**: paperkit's `.bazelrc` carries `remote_local_fallback` **4×** and `CO-`'s `§6` dates `verb.bzl` to `99cde55` 2026-06-27, which I confirmed. **The withdrawal was warranted** |
| `RP-N3` | filed a negative on a **FAILED control**, attributing it to the corpus | ⚑ **understated**, and it *"changed a verdict"* | ⚑ **The correction is right and the cause was `-maxdepth 3` in its own probe.** *"an apex reading my draft would have held and reasoned around a reader limitation that does not exist."* ⚑ **I carry the STRONG claim: rosettapkg has no CI, measured** |
| `CO-§Q-4` | proposed narrowing the `scripts/` carve-out as an escape | ⚑ **overstated a weakness** — a defect that was not one | ⚑ **The operator's correction stands and is the finding** (`AX-13b`): the maxim is scoped to the DATA UNDER TEST, not the instrument |
| `MT-` `§9` | *"I cannot distinguish 'my repo does X' from 'I decided X eight hours ago'… Discount accordingly"* | **understated** | ⚑⚑ **I decline the requested discount for `MT-08` and `MT-12`, and I say why.** Those two are **measurements, not decisions** — 35 `^def test_` lines collecting **38 node-ids**, and 23 targets green over **zero assertions**. ⚑ *"A list transcribed by reading the source is wrong on its first day, by three cases, silently."* **An 8-hour-old repo's measurement is as old as the measurement.** *The disclosure is correct about `MT-02`/`MT-05` and over-broad about `MT-08`/`MT-12`* |
| ⚑ `LS-` `§9` | discloses being **both surveyor and dispatcher**, and that it authored `§X` | correctly stated | ⚑ **`AX-14` is where this bites and it bit in the leg's own favour**: `LS-`'s `§Q`-10 cites the withdrawn cause **its own author had written into `§X`**. `§Z` cuts both ways and I applied it: **the citation is stale, the inference is not** |

⚑ **Four of six self-grades in this census were WRONG IN THE MODEST DIRECTION**, and every one was
caught by its own author before or shortly after filing. ⚑⚑ **That is the strongest evidence in the
run that `§Z` is a real class and not a hypothetical**, and it inverts the assumption `§Z` records
the skill as having held — *"the skill assumes the risk runs one way: a leg overstating its
independence or coverage."* **Measured here: 4 understatements to 2 overstatements.**

## `AX-25` — ⚑ THE UNBOUNDED REMAINDER: what the glue could NOT resolve

**`apex.md`'s termination test is that every leg entry is placed. It is. But three questions the
legs explicitly handed to the apex are NOT answered, and I name them rather than let the document
imply closure.**

1. ⚑⚑ **`SB-08`'s structural-reader bound is UNRESOLVED.** *"~100 tools, ~619 modes… I do not know
   which of these a peer already had."* **I cannot resolve it either.** Doing so requires sweeping
   five trees for tool-name and mode overlap — ⚑ **and `§A6` says a leg I re-sweep is one witness,
   not two**, so a sweep would give me a number I could not corroborate against any leg's own
   account. **What I CAN say from the documents:** five legs hold a structural-query toolkit
   (`AX-17a`.2), and **two implementations of one of them diverged in both capability and defect
   mid-census** (`AX-18`). **That is a lower bound of two on duplication within a single tool, and
   it says nothing about 619 modes.**
2. ⚑ **`LS-19`'s question is ANSWERED; `LS-21`'s is answered NEGATIVELY.** Does a peer have a tier
   model, and is it these three? **Yes — `A1`, and it is paperkit's, 68 days older.** Does a peer
   have a subprocess-completeness net? **No leg reports one**, so `LS-04`'s 1,905 lines are
   unduplicated **and therefore unshared** — which is `MT-10`'s DISTRIBUTION constraint from the
   supply side.
3. ⚑ **`RP-08b`'s merge question is unanswered by construction.** *"whether the domain-specific
   claim set is separable from the SCC/layer machinery — which nobody has written down."* ⚑ **And
   substrate's leg does not mention `el-atlas-depsort.py` at all**, so the census holds a documented
   adopter of an artifact the owning party did not report holding. **Carried; §B4 forbids
   collapsing it.**

⚑ **A fourth, which is mine and not a leg's:** `AX-20a`'s discriminator is a **date**, and `§Y`
forbids the cheap way of getting it. **The divergence stands open, correctly.**

## `AX-26` — ⚑ `§A6` BOUNDS: the union of the legs' own, and what it means that they overlap

**`apex.md`: *"if all legs excluded the same region by construction, that is ONE unexamined region
measured N times, not N confirmations."*** ⚑ **Three such regions, and they are not independent:**

1. ⚑⚑ **Nobody had a cold machine.** All seven `§Q`-3 answers are counterfactual reasoning about
   what a cold clone *would* do. **`SB-`'s and `LS-30`'s `gcalculus` nomination is precisely this
   region's owner** (`AX-22b`). ⚑ **One unexamined region, measured seven times.**
2. ⚑ **Every leg excluded peer legs pre-freeze** (brief §2) — correct and by design, **and it means
   no leg's cross-repo claim was checkable by its author.** Every such claim in `AX-23` inherits
   this. ⚑ **`RP-`'s `§D`.3 is the sharpest disclosure of it**: it read `§Y` and `§N` *"as they
   appear in the run file"*, could not avoid the peer quotes inside them, and **declared the
   correlation a reader would otherwise find unexplained.**
3. ⚑ **Instrument-shaped coverage, and `LS-`'s is the inverse of a normal reader-blind statement** —
   one of the four headings substrate's mdstruct drops, recovered here:

   > `grep`/`cat`/`wc` over `.py` and `.md` were **refused**; `.bazel`, `.bzl`, `.bib`, `.tsv`,
   > `.sh`, `.json`, `.toml` were **unguarded** and read textually. So my coverage is
   > **systematically deeper on unguarded suffixes** and **forced through whole-file `Read` on
   > guarded ones** … ⚑ **the shapes my reader could not see are the shapes it was *forced to see
   > whole*.**

   ⚑ **`CO-`'s is the ordinary form and it lands on the same tool**: *"`scripts/mdstruct.py` — the
   owning tool for `.md` structural queries — is **broken in this checkout**
   (`ModuleNotFoundError: climode`), so every markdown fact above came from `Read`."*
   ⚑⚑ **Three of seven legs report the routed `.md` reader failing or distorting** — `LS-26`
   (coverage boundary), `CO-` (broken in checkout), and rev 34/37 (dropping headings). **My own read
   makes four.**

**Other declared bounds, carried:** `SB-` excluded the Agda tree (~3.5k modules) and declared
`drain_leverage` **16 unnameable insert sites** and `arm_claims` **5 unmodellable arms**, counted and
claimed for nothing. `CO-` excluded 6 worktree clones (⚑ *"Counting them inflates every dependency
figure roughly 6×"*) and 3,625 lines of curriculum notes. `LS-` excluded `CLAUDE.md` (77,524 B) and
`NEXT.md` (133,764 B) as *"this repo's claims ABOUT itself; citations-of-the-repo, never
verification"*, plus ~383 lines of `gen_gate_build.py`. `MT-` excluded ~99M of untracked tree.
`RP-` read **8 of 8 files, 126,645 of 126,645 bytes** — ⚑ the only complete-corpus leg. `PK-`
started no bazel invocation (server lock held). **Unreadable/unparseable across all seven: `SB-`
declares 21 counted items; every other leg declares 0.**

⚑ **`SM-`'s coverage carries a bound no other leg has, and it is a `§F` finding:**

> ⚑⚑ **THESE FIGURES WERE RE-MEASURED IMMEDIATELY BEFORE FILING, AND FOUR OF THE SEVEN HAD MOVED.**
> … ⚑ **The corrected `89 parse` moved AGAIN while I was correcting it**, because the probe
> verifying my own commit form is itself a `.py` under summit.

> ⚑ **This is not tidiness; it is the census's own `§F` at the level of the figures.** *A filing is
> an artifact, not an event* — **a leg surveying a live tree cannot hold a still population**, and
> the honest form is to state when the count was taken rather than to imply the tree stopped.

⚑ **`CO-§3` reports the same class independently** — *"an earlier draft said 659 files / 596 commits
/ 74 arms… ten commits of my own work later they read 664 / 611 / 76"* — and its repair is to
**print the command beside each figure so a reader re-derives rather than trusts.** ⚑⚑ **Two legs,
two vantages, one finding: a census figure is a measurement restated in prose, and prose does not
re-run.**

## `AX-27` — ⚑ `§A5` THE MAP FROM ASKS TO ARTIFACTS

**Which filing answers which revision of `§Q`.** ⚑ **This matters because `§Q` itself never changed
— but `§V` revisions 3, 4, 9, 11, 19 and 23 changed *how legs were required to answer it*, and a
reader cannot otherwise tell which sections answer the original ask and which answer its
replacement.**

| leg | filed against | ⚑ which binding revisions it could NOT have read |
|---|---|---|
| `SB-` | **rev 1** | 3 (`§Y`), 4 (`§Z`), 9 (`§T`), 11/34–37 (the reader), 19 (`§D`), 23 (`§X` withdrawal) |
| `MT-` | **rev 1** | same — ⚑ **yet `MT-01` IS `§Y`'s source.** It reached the finding rev 3 then made binding, from its own probe, before the rule existed |
| `PK-` | **rev 1** | same — ⚑ **yet `PK-13` runs the antecedent probe `§Y` would later require, and it *"retired two of my own findings' novelty"*** |
| `LS-` | **rev 5** | 9 (`§T`), 11+, 19 (`§D`), 23 — ⚑ **`AX-14`: it cites the cause rev 23 withdrew.** ⚑ It later **appended** a `§Q`-4 arm post-freeze; ruled ACCEPTED at `AX-13c` |
| `RP-` | **rev 6**, drafted against rev 1 | 9, 11+, 19, 23 — ⚑ **and it is the only leg to absorb revisions BETWEEN drafting and filing and to report the cost**: *"A leg dispatched at rev 1 wrote against a stationary brief; I did not."* Two revisions (`§Y`, `§Z`) **changed its findings** |
| `CO-` | **rev 6** | 9, 11+, 19, 23 — ⚑ **it is the SOURCE of rev 23's withdrawal and of `§T`**, both arriving in the run file after its leg was drafted |
| `SM-` | **rev 21** | 23 (`§X` withdrawal), 26–38 — ⚑ **it is the source of revs 26, 32, 33 and 38**, and rev 32 (its own `--headers` measurement) is what made the reader instruction binding on me |

⚑⚑ **The pattern is worth naming: FOUR legs are the SOURCE of a revision that later became binding
on legs filed earlier.** `MT-` → `§Y`; `CO-` → `§T` and rev 23; `SM-` → revs 26/32/33/38;
`SB-` → `§G`/`§H` (the file split). ⚑ **A census whose legs generate its own controlling procedure
mid-run cannot have a single "the ask" — and `§A5` exists because the apex is the only party who can
see that.**

⚑ **`§D` applies to every one of these documents.** Per rev 19, *"this session"*, *"me"*, *"I"* and
*"this survey"* in any leg name **the filing party at filing time, no longer reachable**. `LS-24`'s
heading — *"FOUR GATES FIRED ON ME DURING THIS SURVEY"* — still parses and **points at nobody**.
⚑ **I read every first-person claim in this document that way, and I asked no filing party
anything, because `§D`.3 makes that unexecutable.**

## `AX-28` — ⚑ `§I`: the finding I inherited rather than made, and what I did with it

**`§I` is the run's largest recorded finding and it is about the apex seat:** two blockers stood for
hours and neither existed — *"a SUBAGENT holds no leg"*, and *"the operator was reachable."*

> ⚑⚑⚑ **A capability you hold and do not consider is indistinguishable, from inside, from one you do
> not have.**

⚑ **I exist because that was dissolved**, so I cannot claim the finding. **What I can report is the
one instance of the same shape I met in this pass:** rev 37 told me the sanctioned reader is
defective and the correct one is reachable by absolute path into another repo's venv. ⚑ **The
routing hook fired on me once, naming the defective copy as *"the tool that owns"* the file.** The
frame arrived attached to the work; **the instruction to disregard it arrived in `§V`, which is
where `§G` says corrections live, and it is the only reason this document contains `SM-13` and
`LS-17`.**

⚑ **`§I`'s operational test, applied honestly:** *when a blocker has stood for more than a few
ticks, check whether it is a fact or a frame.* **I hit no blocker in this pass** — every instrument
I needed was reachable and every leg was in `HEAD`. ⚑ **I record that as a fact about this pass, not
as a strength**, because `§I`'s whole point is that the absence of a felt blocker is not evidence
that none is operating.

---

## `AX-29` — Termination, sizes, and what I was told to do that I could not

### Termination test

**Every leg entry is placed.** Each is either in `A` (`AX-01`, 18 rows), in the glue (`AX-10`
through `AX-22c`), in the divergence register (`AX-20`), in carried testimony (`AX-23`), or in the
named remainder (`AX-25`). **Finite and checked.**

### Sizes, per `§C`'s test

| artifact | lines |
|---|---|
| largest leg — `linux-sources-deps-build.md` | **643** |
| second — `cassian-observability-deps-build.md` | 495 |
| **this document** | ⚑ **1,309 — 2.04× the largest leg. Phase 2 ran.** |

**Measured with `mtools/mdstruct/.venv/bin/mdstruct spans`: 72 sections.**

⚑ **The span alone (`AX-01` + `AX-02`) is ~30 lines. Had I stopped there, this document would be
smaller than five of the seven legs**, which is `§7`'s named symptom of stopping at the span.

### ⚑ What the run file told me to do that I could NOT do

1. ⚑⚑ **`SB-08`'s `~619 modes` remains unbounded** (`AX-25`.1). `§Q`-8 is the census's highest-value
   question and its largest single answer is the one the glue cannot close. **Resolving it needs a
   five-tree sweep, and `§A6` says a re-swept leg is one witness, not two** — so the sweep would
   produce a number no leg could corroborate. **I declined it and named the bound.**
2. ⚑ **`AX-20a`'s discriminator is unobtainable.** *A setting that predates a ruling is a stale
   config; one that postdates it is a divergence.* `§Y` forbids taking the date from a `git log` on
   a consolidated or hunk-level artifact, and `§D` makes asking `PK-`'s filing party unexecutable.
   **Both branches stand.**
3. ⚑ **`§N`'s six nominations are carried, not dispatched** — correctly, per `§N`'s own ruling that
   dispatching now *"changes what the filed legs mean without changing their text."* ⚑ **A
   second-round census over the nominated set is a separate run with its own run file. This document
   does not pretend to cover it.**
4. ⚑ **I could not verify most cross-repo testimony** (`AX-23`), and **I did not try**, because
   trying means re-sweeping a peer's corpus and `§A6` makes that a *degradation* of the witness
   count, not an improvement.
5. ⚑ **`§Q`-3's cold-machine question is answered by nobody.** All seven answers are counterfactual
   (`AX-26`.1). **The party who could answer it is `gcalculus`, nominated by two legs and
   undispatched.**

### ⚑ What this document does NOT do

- **It does not supersede any leg.** Each leg remains the primary citation for its own content.
  A reader tracing any item should read the leg.
- **It does not adjudicate divergences the witnesses do not settle** — `AX-20` a, b, c and e all
  stand open.
- **It does not renumber legs into its own namespace.** Every citation above is in the leg's own
  prefix. ⚑ `AX-` numbers name **apex sections**, never leg findings.
- ⚑ **It resolves no roster nomination and dispatches nobody.**

---

⚑ **The span is 18 rows with 10 stated non-identifications. The glue carries every entry of all
seven legs. Four divergences stand unresolved; three remainders stand open; one post-filing append
was ruled admissible and one withdrawn `§X` cause was traced to its single consumer and found
non-load-bearing.**

⚑⚑ **The one thing this census found that no leg could have: `§R` enumerates parties, and the
subject is edges.** `SM-16` named it; `LS-23`, `MT-03` and `RP-02` each measured a different
instance of it without knowing; and the census's own instrument split into two diverging
implementations of one tool **while the survey ran, in the reader every party was routed to.**
*A dependency census discovered that its index had the wrong shape for dependencies.*

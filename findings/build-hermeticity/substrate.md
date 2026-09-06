# substrate — build-hermeticity census leg

**Prefix:** `SB-` · **Filed against:** `CENSUS-build-hermeticity.md` **rev 13** · **Measured:**
2026-09-06, in `~/github/substrate` unless stated.

⚑ **Self-survey.** Every figure below names the command that produced it. Where I could not
measure something I say UNMEASURED rather than estimating, and where a figure is a floor I say so.

⚑⚑ **EVERY FIGURE IS STAMPED `[2026-09-06]` AND THAT IS NOT CEREMONY HERE — `§W` rev 13.** This
leg's own `SB-05` is the argument for it: **three peer trees changed state under me today**, and
one figure I reported about a peer was refuted within the hour by the peer measuring it. A census
over live trees dates its own findings or it cannot be read later.

⚑ **THE MOVING FIGURES ARE MARKED `⏱` SPECIFICALLY.** Anything that is a property of another
tree, of a `.venv`, or of an uncommitted working state can move without anyone editing this file.

⚑⚑ **AND THE DISPATCHER ALREADY MEASURED THREE OF MY MECHANISMS CORRECTLY** (`§Q`-3 rows
`substrate` i/ii/iii). I re-ran what I could and confirm them; this leg adds what only I can
answer and corrects nothing in that table.

---

## SB-01 · What I build with (`§Q`-1)

    find . -maxdepth 1 \( -name uv.lock -o -name pyproject.toml -o -name MODULE.bazel
                          -o -name WORKSPACE -o -name .bazelrc -o -name Makefile
                          -o -name mise.toml \) -printf '%f\n'
      -> uv.lock, pyproject.toml

**No bazel. No root Makefile. No `mise.toml`.** Python packaging plus a generated Agda build:

- `uv` + `pyproject.toml` + `uv.lock` for the Python side.
- `agda/Flat.mk` + `agda/Makefile`, both **generated** by `scripts/gen_build_makefiles.py`, driven
  by `make -C agda -j`.
- **37 declared gates** (`build_census.py --gates`) across two phases, invoked by
  `.githooks/pre-commit`.

⚑ **I am on this roster as a no-bazel party and that is the position I answer from.** What I can
say that a migrated repo cannot: **what the pieces cost when you build them without bazel**, which
is most of `SB-05` and `SB-09`.

## SB-02 · Measuring off the live process (`§Q`-2)

⚑ **PARTIALLY ANSWERED, AND I SAY SO RATHER THAN SUBSTITUTING THE CONFIG READING.** The method
transfers: a config file is what you declared, the process is what ran. My gates are invoked by
`.githooks/pre-commit`, so a live `ps -o args=` capture requires a commit in flight, and I have
none this tick. **UNMEASURED at the process layer.**

⚑⚑ **BUT THE ONE PROCESS FACT I DID MEASURE INVERTED WHAT I WOULD HAVE REPORTED FROM CONFIG** —
see `SB-06`. That is the census's own point arriving on my leg: I would have filed my interpreter
as declared, and the resolution order says otherwise.

## SB-03 · Work discovery — I hold THREE, and they are not variants (`§Q`-3)

The dispatcher's table is right. Confirmed and detailed:

| # | mechanism | derived from | drift check |
|---|---|---|---|
| i | **`gen_build_makefiles.py`** → `Flat.mk` + `Makefile` | the Agda **import DAG**, source-parsed | `--check`, reports `stale:` |
| ii | **censuses + ratchet baselines** (`gate_census`, `build_census`, `paydown_census`) | populations they enumerate | the ratchet itself; a new key refuses |
| iii | **the worklist** — `catalog/worklist/` as a gated paperkit project | ⚑ **nothing** — AUTHORED | a **red claim**, not a drift report |

⚑ **(i) IS STRUCTURALLY LINUX-SOURCES' BAZEL GENERATOR WITHOUT BAZEL.** Derive from a source of
truth, emit a checked-in artifact, gate the drift with `--check`. The shape is the answer, not the
build system underneath it.

⚑⚑ **AND (iii) IS THE ROW `§Q`-3 WAS REPHRASED TO SEE — I CONFIRM `gabion-e5`'s CATCH LANDED ON
ME.** Under rev 1–10's *"where does your work list come from"*, my honest answer is **nowhere**,
which scores as absence-of-mechanism. It is the opposite: the work list is itself a warranted
artifact, so **going stale is a failing claim rather than a drift report.** Gated rather than
checked. Had the question not been rephrased, this leg would have under-reported my strongest row.

## SB-04 · Specificity — the unit is a KEY, and the tolerance is a SET (`§Q`-4)

    gate_census.py --baselines                           ⏱ [2026-09-06]
      19 ratchet(s): 7 ok · 11 EMPTY · 0 ABSENT · 1 UNREAD

**The grain is a ratchet KEY against a baseline SET.** One level coarser is a COUNT; one finer is
a per-site annotation nothing here carries.

⚑ **WHAT THE SET GRAIN BUYS, NAMED BY THE FAILURE IT PREVENTS:** a COUNT baseline passes when one
key leaves and another arrives — *six names versus six names, with different sets* — and this repo
has that recorded as a measured defect. A SET catches the swap; a COUNT cannot.

⚑⚑ **WHAT IT COSTS, WHICH THE CENSUS IS RIGHT THAT NOBODY WRITES DOWN.** Three costs, measured:

1. **11 of 19 baselines are `EMPTY`** — zero-tolerance, which the legend calls the strongest
   setting. It is also the one that fires on unrelated work: every new key is a refusal, so a
   paydown-shaped session pays for keys it did not create.
2. **A key is not a location.** When a drain moved substrate's write paths, a witness keyed on
   `scratch/bibstruct.py` reported *"no write path found — UNMEASURED, not clean"*. Correct, and
   the subject had moved out from under it. **Set-grain does not survive relocation.**
3. **`1 UNREAD`** — `ratchet_legacy.py` has no baseline literal any call site declares. That is a
   fact about the reader, and it has sat unresolved.

## SB-05 · Cross-repo edges (`§Q`-5)

**EMIT — and this is the direction the census correctly says nobody records.** Measured today,
partly by peers reporting into me:

| consumer | what they take | edge ⏱ `[2026-09-06]` |
|---|---|---|
| `gabion` | `hook_cmdparse`, `hook_no_chaining`, `hook_structural_query` | ⚑ **AMBIENT** — 3 symlinks into `../../substrate/scripts/` |
| `cassian-observability` | the same hooks | **vendored copies**, 8 regular files, 0 symlinks |
| `linux-sources` | the same hooks | symlinks **plus** a wheel-installed `substrate` in its venv |
| `paperkit` | `bibstruct.py`, `edit_snapshot.py`, `vfs.py`, `cgroup-scope`, `absence_audit.py` | vendored |

⚑⚑ **⏱ EVERY ROW ABOVE IS A PEER-TREE STATE AND CAN MOVE WITHOUT ANYONE EDITING THIS FILE.**
`cassian` was symlinked until `72d1b70` on 2026-08-30 and is vendored now, so **this table would
have been wrong a week ago and nobody would have known.** ⚑ I asserted the pre-migration state
today and cassian refuted it by measurement within the hour.

⚑⚑⚑ **THE CONTROLLED COMPARISON NOBODY BUILT DELIBERATELY, VERIFIED IN BOTH TREES:**

    find ~/github/linux-sources/.venv/lib -name ratchet_flags.py -path '*substrate*'
      -> .../site-packages/substrate/ratchet_flags.py        A REAL FILE
    find ~/github/gabion/.venv/lib -maxdepth 3 -name 'substrate*'
      -> (nothing)

**Identical symlinks, identical hashes, identical wrong `_ROOT` — opposite outcomes, decided only
by whether a resolver placed the package.** linux-sources' hooks fire; gabion's two armed hooks
crash with `ModuleNotFoundError`. So `sys.path.insert` is **dead code in one adopting tree and
load-bearing in another, and nothing in the file distinguishes them.**

⚑ **AND THE EMITTED SURFACE IS PARTLY UNCOMMITTED.** `scratch/mdstruct.py` is untracked (`??`);
peers invoking it by path run a file that exists in **no commit anywhere**. My hooks' arming
configuration is likewise uncommitted (`SB-08`).

**CONSUME:** `paperkit` as a PEP 508 direct git reference in `pyproject.toml` — **DECLARED**. That
one is clean.

## SB-05b · Invoked executables (`§Q`-5b)

| binary | site | declared? | behaviour when absent |
|---|---|---|---|
| `pandoc` | `mdstruct.py:339` | ⚑ **no manifest** | `_pandoc` raises |
| `shellcheck` | `hook_shellcheck.py`, mise shim path hardcoded at `:118` | ⚑ **no manifest** | ⚑ **reports UNKNOWN, states the gap, names the install** |
| `agda` | via the membudget PATH shim | ⚑ **no manifest** | the build fails |
| `git` | throughout the gate layer | no manifest | — |

⚑ **THE `shellcheck` PATH IS THE CORRECT SHAPE AND STILL AMBIENT.** It refuses to report a false
green — *"ARMED BUT INERT — no shellcheck"* — which is the third outcome done right. **It does not
make the dependency declared**, and the census's framing of mtools' equivalent applies here
unchanged.

⚑⚑ **AND MY `SKILL.md` IS THE GOVERNED-DOC INSTANCE gabion NAMED.** `.claude/skills/struct-tools/
SKILL.md` is the structural-query hook's live routing table, read **at call time**, naming the
tools that own each artifact — **dependencies declared in a file no resolver reads.** Confirmed as
the same shape gabion reported in their own tree.

## SB-06 · Interpreter — AMBIENT, and I would have filed it as declared (`§Q`-6)

    which -a python3                                        ⏱ [2026-09-06]
      /home/mikemol/github/substrate/.venv/bin/python3      <- FIRST
      /home/mikemol/.local/share/mise/installs/python/3.13/bin/python3
      /home/mikemol/.local/share/mise/shims/python3
      /usr/bin/python3
      /bin/python3

⚑⚑⚑ **BARE `python3` RESOLVES TO MY OWN VENV BECAUSE OF PATH ORDERING.** Every hook and gate that
invokes `python3` — which is essentially all of them — **works ambiently**. There is no
`mise.toml` here, so the interpreter *version* is pinned nowhere; cassian reports a three-way pin
enforced nowhere, and I have **no pin at all**, enforced nowhere.

⚑ **This is bare-python-LUCKY, and I only know it because I ran the census's own command.** From
the config I would have reported *"the venv is the interpreter"*, which is true today and true for
a reason no artifact records.

## SB-07 · The `.venv` — a thing I made once (`§Q`-7)

    git check-ignore -v .venv    -> .gitignore:51        ⏱ [2026-09-06]
    grep -c 'hash = ' uv.lock    -> 1049                 ⏱ [2026-09-06]

The two independent properties the census asks for:

| property | state |
|---|---|
| set pinned | ✅ `uv.lock` |
| content hash-pinned | ✅ **1049 hashes** ⏱ `[2026-09-06]` |
| lock freshness **gated** | ⚑ **NO** ⏱ `[2026-09-06]` |

⚑ **NOT ONE OF THE 37 GATES CHECKS THE LOCK AGAINST `pyproject.toml`.** Confirmed against
`build_census.py --gates` ⏱ `[2026-09-06]`; the roster is the hook's own `run` call sites, so it
moves whenever a gate is added. That is gabion's *consumed twice, verified never* in a tree whose lock
is otherwise stronger than theirs — **content-hashed and ungated is a real combination, and the
hashes do not compensate**, because nothing notices a manifest edit that should have moved them.

**The `.venv` is gitignored, produced by `uv` on demand, and is not a build output.** Its content
is a fact about this machine's history.

## SB-08 · Hermetic — and what I proved (`§Q`-8)

**Proved, with a check that has fired:**

- **`membudget`** — a cgroup `MemoryMax` + `memory.swap.max=0` lease per Agda compile. It **kills
  and retries at the next power-of-two bucket**; exit 137 is observed routinely. This is
  enforcement, not declaration, and paperkit independently measured that `resource_set` is a
  scheduling hint that bounds nothing — so the cgroup is the only boundary either of us has.
- **The per-file gate** — ruff `select=ALL` + mypy strict, no suppression path. It has refused
  ~ten edits this session alone, several of which were design signals rather than nuisances.

**NOT hermetic, and I name it rather than let a green imply otherwise:**

- Every gate runs on the host with an ambient interpreter (`SB-06`).
- ⚑ **`hook_fire_probe --report` reads 12/12 arms ok — and that green is a fact about MY tree**,
  where `_ROOT` is already correct. It says nothing about an adopter and nothing about which python
  ran it. **It would have reported clean through gabion's entire outage.**
- ⚑⚑ **THE ENTIRE HOOK INSTALLATION IS UNCOMMITTED** ⏱ `[2026-09-06]`. `git diff
  .claude/settings.json` shows the `env` block arming all four hooks and every `PreToolUse`
  registration absent from `HEAD`. Live state: four hooks armed and denying. Declared state in
  `HEAD`: **no hooks exist.** The crossing touched no artifact.
  ⚑ **THIS IS THE MOST VOLATILE FIGURE IN THE LEG** — one commit changes it, and nothing in the
  tree would record that it had been true. Committing the config is the operator's call and I
  have not staged it.

## SB-09 · Solved and declined (`§Q`-9)

**SOLVED, offered with the measurement that made me trust it:**

1. **`membudget`** — RAM semaphore + cgroup enforcement + pow2 autosizing with retry-on-OOM.
   Motivating measurement: a 5.6 GB monolithic Agda KAT took the whole machine. Now a too-small
   guess costs one re-exec and self-corrects.
2. **A generated-file staleness gate that runs today** — `gen_build_makefiles.py --check` in
   pre-commit. cassian's `ros-staleness` is the same idea and their own claim records it as *"NOT
   yet written to BUILD.bazel"*. ⚑ On this one the no-bazel party is ahead.
3. **The ratchet SET baseline** with `--init-absent` — see `SB-04` for the failure it prevents.
4. **A discovery predicate over CONTENT** — `suite_discovery.is_suite(src)`, so *"which files are
   suites"* is owner-answered rather than grep-counted.

**DECLINED — HELD (I can state the reason):**

- **bazel, so far.** The Agda build is 3,598 modules whose real dependency edges are import edges;
  `make -j` self-throttles against the membudget semaphore in dependency order. ⚑ The held reason
  is specific: **I have not measured what bazel's action-key would have to hash** for a compile
  that shells out to `agda` through a PATH shim. Per cassian's `ck-stamp-gap`, an unpinned
  toolchain means a cached verdict serves stale green. That is a real precondition, not a dislike.
- **A `sys.path` insert as the adopter story.** Held after measurement: the same insert is dead
  code in one adopting tree and load-bearing in another (`SB-05`).

**DECLINED — UNEXAMINED (I never compared):**

- ⚑ **Remote execution / RBE.** cassian's endpoint is live and free; I have never run against it
  and hold no view. Recording this as unexamined rather than as a decision.
- ⚑ **`--disk_cache` path-independence.** paperkit measured 7 output bases and 3.7 GB of
  near-duplicate cache; two repos already share `~/.cache/bazel-disk/<repo>`. **I never looked**,
  and its value is highest during exactly the migration evaluation I have not run.
- ⚑ **Hermetic Python toolchains.** Never compared.

---

## SB-N · Roster nominations (`§6`)

- ⚑ **`el-openglo`** holds `catalog/worklist/warrants.bib` **and** `catalog/cotype/warrants.bib` —
  the same worklist shape as mine, which rev 7 nearly called unique. Their leg would say whether
  the pattern converged or was copied, and that is the lineage subtraction paperkit's §1.1 warns a
  synthesis needs.
- ⚑ **The operator**, for the retirement state `§R` records as unmeasurable. Not a nomination for a
  leg — a note that one row of the roster is knowledge no instrument holds.

## SB-L · Limits of this leg

- **`SB-02` is UNMEASURED at the process layer.** No commit in flight this tick.
- **`SB-05b` is a FLOOR, not a census.** Four binaries found by targeted reads; I have no reader
  that enumerates every shelled-out executable, so this is *what I found*, never *what exists*.
- **Every peer-tree figure in `SB-05` I re-ran in the peer tree myself**, because a peer's verdict
  is a hypothesis. The two `find` results are mine, not relayed.
- ⚑ **I have made three outward inferences about peer trees today and all three were wrong**, each
  caught by the party inferred about. Any claim here about another repo should be read with that
  record attached.

Third-party measurement by a subagent dispatched from linux-sources, against CENSUS-build-hermeticity.md rev 12. el-openglo has no live session and did not survey itself.

# EO — el-openglo, third-party measurement

**Evidence arm:** the `el-openglo` working tree at `/home/mikemol/github/el-openglo`, read directly by this subagent, 2026-09-06, no build run. **Normative arm:** `CENSUS-build-hermeticity.md` rev 12, `§Q` (nine questions) and `§C` (span/glue construction).

⚑ **Provenance discipline for this whole leg:** every claim below is `citation` (a quoted byte, a file existing at a path, a byte count) or `machine` (a command's literal output). No claim here is `testimony` or `inference` about what el-openglo's author intended, decided, or declined. `§Q`-7 and `§Q`-9 are answered `UNANSWERABLE BY A THIRD PARTY` below, not skipped.

## EO-1 — `§Q`-1: what el-openglo builds with

**No bazel.** Control run, 2026-09-06T20:16Z:

```
find /home/mikemol/github/el-openglo -maxdepth 1 ( -name MODULE.bazel -o -name WORKSPACE -o -name .bazelrc -o -name Makefile -o -name pyproject.toml -o -name mise.toml -o -name uv.lock -o -name requirements.lock ) -printf '%p\n'
  -> pyproject.toml
  -> uv.lock
```

(parens grouped per the `▣36` trap this run file names — un-grouped `-printf` binds only the last `-o` branch.)

**Positive control for the bazel-absence claim:** the same query pattern, run against `linux-sources` in an earlier measurement this run file already carries (`§X`, rev-agnostic), returns 8 files across 4 repos including `linux-sources` itself — so the query shape *does* return bazel markers when they exist; the zero here is a real absence, not a broken reader.

So el-openglo builds with: **`uv`** (`pyproject.toml` + `uv.lock`, `[tool.uv] package = false`), invoked as `uv sync` / `uv sync --extra research` per `pyproject.toml`'s own comment, and **git hooks** (`.githooks/pre-commit`, `.githooks/pre-push`, `.githooks/post-commit`, enabled via `git config core.hooksPath .githooks` per the hook files' own header comments) which run a battery of Python check scripts. There is no `mise.toml` and no `.python-version` at the repo root:

```
find /home/mikemol/github/el-openglo -maxdepth 1 -name 'mise.toml' -printf '%p\n'  -> (empty)
```

Positive control for that absence: the same query against `linux-sources` (recorded in this run file's own `§X`, `mise.toml` → `python = "3.13"`) returns a hit, so the query shape is capable of returning a mise.toml when one exists.

`pyproject.toml` declares `requires-python = ">=3.11"` — a floor, not a pin — and nothing at the repo root pins an exact interpreter version the way `gabion`'s `mise.toml` (`3.14.2`, per `§X`) does.

## EO-2 — `§Q`-2: measured off the live process

**UNMEASURED — no build or hook was run** (cost discipline: running `.githooks/pre-commit` would exercise the full check battery including `worklist_gate.py`, which re-execs under `uv run` and invokes the paperkit engine at `~/github/paperkit`; this is exactly the class of run the census's cost discipline asks to avoid absent a specific need). What follows instead is a **citation** of the hook's own declared invocation logic, not a `ps -o args=` capture:

`.githooks/pre-commit`, quoted:

```sh
if [ -d "$ROOT/.venv" ] && command -v uv >/dev/null 2>&1; then
  RUNNER=(uv run --no-sync python3)
else
  RUNNER=(python3)
fi
```

This is a **declared conditional**, not a live measurement — the hook falls back to bare `python3` when no `.venv` exists or `uv` is not on PATH, and that fallback path is exactly the "ambient interpreter" shape `§Q`-6 asks about. Whether the fallback branch has ever actually fired here is unmeasured.

## EO-3 — `§Q`-3: dynamic work discovery — derived or authored

**AUTHORED**, and doubly so: el-openglo runs **two separate paperkit projects**, `catalog/worklist/` and `catalog/cotype/`, both driven by one gate script, `scripts/worklist_gate.py` (20437 bytes).

Quoted, `scripts/worklist_gate.py` lines 20–24:

> *"⚑ THERE ARE TWO PROJECTS, AND EVERY MODE RUNS BOTH. `catalog/worklist/` is the repo's own claim graph; `catalog/cotype/` is the 4,600-line design log read structurally. They are separate paperkit projects because they answer different questions, but a gate that covered only one would report green while the other rotted — so the default is BOTH, and `--only` is the deliberate narrowing."*

**Project 1 — `catalog/worklist/`** (`paper.toml` 578 bytes, `warrants.bib` 31090 bytes). This is the repo's own claim graph: hand-authored `@misc{...}` entries each carrying a one-line `claim` and a `check` referencing a named tool. Quoted from `warrants.bib`'s header comment:

> *"THE GOVERNING INVARIANT: every claim here is UNDISCHARGED until its check passes, and the item is incomplete until it can be discharged... THERE IS NO open/closed FIELD, AND THERE MUST NEVER BE ONE. Openness is computed from exit codes; nothing records it, so nothing about it can go stale."*

**Drift detection for the authored case:** a red claim (a check exiting non-zero) *is* the staleness signal, computed fresh every run — there is no separate drift check because there is no cached status to drift from. `.githooks/pre-commit` step 4 runs `scripts/worklist_gate.py` and treats a non-zero exit as a gate failure blocking the commit.

**Project 2 — `catalog/cotype/`** (`paper.toml` 578 bytes, `warrants.bib` 7445 bytes) mechanizes a 4,600-line prose design log (`COTYPE.md`) via `scripts/cotype_index.py` (17080 bytes) and `scripts/check_cotype_coherence.py` (11054 bytes), rather than trusting a human re-read of the log. Quoted, `catalog/cotype/warrants.bib` header:

> *"COTYPE.md is 4,600 lines of append-only session log across 72 sessions. It is not prose: it has a grammar... Answering 'what is still open?' by READING it is the shape the standing rule forbids, and at this length it is also just unreliable... So the log is read by a tool (scripts/cotype_index.py) and its coherence is a CLAIM (scripts/check_cotype_coherence.py) rather than an impression."*

This is a **third mechanism distinct from the five already in the run file's `§Q`-3 table**: not a generator emitting a build file (`linux-sources`, `substrate`'s Makefile generator), not a fetch-time repository rule (`paperkit`), not censuses-against-baselines (`substrate`'s ratchets), and not a hand-declared YAML registry (`gabion`) — it is a **structural coherence check over a free-text log**, itself gated as a paperkit claim (`catalog/cotype/warrants.bib` has its own `check = tool:...` entries). Per this run file's own instruction (`§Q`-3, rev 11): *"An authored-and-warranted work list is a DIFFERENT MECHANISM, not the absence of one"* — both of el-openglo's projects are authored, and this is a full answer, not an n/a.

## EO-4 — `§Q`-4: work specificity / granularity

**By claim, one `@misc{...}` entry per `warrants.bib`.** Measured file sizes: `catalog/worklist/warrants.bib` is 31090 bytes; `catalog/cotype/warrants.bib` is 7445 bytes. Exact claim counts were not extracted (would require a structural `.bib` parse rather than a textual grep, per this repo's own `structural-query` hook, which refused a plain `grep` over `.py` files in this tree during this survey — see EO-8 below for the mechanism). **UNMEASURED** at the exact-count level; reported at the byte-size level as a proxy.

**What one level finer/coarser would cost, from the design's own stated rationale:** the `catalog/worklist/paper.toml` comment states check types are resolved as `<custom>:<target>` cmd templates (`pycompile:<file>`, `imports:<module>`, `stsym:<name>`, `tool:<script>`) — i.e. **the grain is already sub-file** (a single symbol import, a single tool invocation) in several of the four declared check types, which is finer than `linux-sources`' per-bazel-target grain and finer than `substrate`'s per-ratchet-key grain. A coarser grain (one claim per script) would collapse `stsym:<name>`-level claims and lose the ability to name which specific symbol regressed — the same "unattributable green" cost this run file names generically in `§Q`-4.

## EO-5 / EO-5b — `§Q`-5 and 5b: cross-repo edges, both directions, including invoked executables

**CONSUME, declared:** `catalog/worklist/paper.toml` and `catalog/cotype/paper.toml` both set `root = "../.."` with a comment explaining the sandbox-root must be declared or the mutation grader infers the wrong root (quoted, `catalog/worklist/paper.toml`):

> *"THE Δ SANDBOX ROOT IS DECLARED, NOT INFERRED. The mutation grader copies a bounded root into a clean sandbox and re-runs each check there. Inferred, that root would be this file's PARENT (`catalog/`)... so every check reaching back to the repo would find an empty tree and grade `broken`."*

**CONSUME, ambient/symlinked:** `scripts/worklist_gate.py` resolves the **paperkit engine** at `~/github/paperkit` via an environment variable with a hardcoded fallback path (quoted, lines 58–61):

```python
CANDIDATES = (
    os.environ.get("PAPERKIT"),
    os.path.expanduser("~/github/paperkit"),
)
```

This is a **declared candidate list with an ambient fallback** — the env var is a declaration mechanism, the hardcoded home-relative path is not resolved through any manifest. `scripts/worklist_gate.py`'s own docstring states it "REFUSES with the reason when it cannot be found — never a silent skip," which makes the ambient edge observable when broken, though not declared in the `§Q`-5 sense of "a manifest a resolver reads."

**CONSUME, symlinked from `substrate`, five files:**

```
scripts/hook_structural_query.py -> ../../substrate/scripts/hook_structural_query.py
scripts/run_selftests.py         -> ../../substrate/scripts/run_selftests.py
scripts/hook_no_chaining.py      -> ../../substrate/scripts/hook_no_chaining.py
scripts/gate_ledger.py           -> ../../substrate/scripts/gate_ledger.py
scripts/ratchet.py               -> ../../substrate/scripts/ratchet.py
```

These are **ambient** (filesystem symlinks resolved at import/exec time, not declared in any manifest `uv` or paperkit reads) and `scripts/check_hooks.py` exists specifically to re-verify two of them (`hook_no_chaining.py`, `hook_structural_query.py`) *from el-openglo's own tree*, quoted from its docstring:

> *"The hooks are symlinked from the repo they were written in. A symlinked script resolves its own root from `__file__`, so it reads THIS repo's files while its code lives elsewhere — which is the whole reason it must be re-verified from here rather than trusted because it passes upstream."*
> *"⚑ A MISSING HOOK IS A FAILURE, NOT A SKIP. If the symlink is dangling or the upstream file moved, the honest report is red: a check that quietly passes when its subject is absent measures nothing."*

This is the **same producer/consumer distinction this run file's dispatcher measured in its own tree** (`▣39`, `§X`) — a symlinked hook resolving `__file__` to the wrong root — except el-openglo has a **dedicated gate for it** (`check_hooks.py`), where `linux-sources`' own equivalent defect went undetected by its own gate suite. That is a machine fact about the two trees' gate coverage, not a claim about intent.

**CONSUME, declared-as-tooling-dependency without any local import (the sharpest instance):** `pyproject.toml`'s `[project.optional-dependencies] tooling` group lists `panflute`, `libcst`, `networkx`, `python-magic`, none of which any module in el-openglo's own tree imports. Quoted, `pyproject.toml`:

> *"THE BORROWED TOOLS' DEPENDENCIES, WHICH NOTHING HERE IMPORTS. `.claude/skills/struct-tools/SKILL.md` routes .py to substrate's pycodemod and .md to its mdstruct — and BOTH sat in that table unable to run, because their dependencies are not this repo's. check_deps.py walks THIS tree's imports, so it reported '8 of 8 accounted for' while the named owner of two artifact kinds raised ModuleNotFoundError. Every gate stayed green; the structural hook refused grep and pointed at a tool that could not start."*
> *"That is the routing table naming a capability the machine does not have. The dependency belongs here even though no local `import` will ever justify it."*

This is exactly `§Q`-5b's target: a declared-but-not-import-resolvable dependency, held for a **borrowed tool** rather than local code, kept in the manifest anyway despite `check_deps.py`'s own walk being structurally unable to justify it via any local import. `check_deps.py` is itself explicit about the shape of its own blind spot (quoted, lines 12–16 and 33–38, two separately-named self-corrections): it originally scanned only the repo root and missed `scripts/identify.py`'s `magic` import, and it originally treated any top-level directory as a local package, which hid `magic/` (a libmagic-signature data directory, no Python) shadowing the real `magic` dependency. Both are recorded as comments citing the specific defect they fixed, not merely present code.

**EMIT:** el-openglo's own `catalog/library/concepts.bib` (4721 bytes) and its worklist/cotype `.bib` files are, per the run file's framing, exactly the kind of artifact a peer could cite — but this subagent found **no evidence in el-openglo's own tree of who consumes them**, which is the expected shape (`§Q`-5's own text: *"a census of declared dependencies structurally cannot see what your tree produces that someone else cites"*). **UNMEASURED from this side** — the consumer, if any, would have to be found in another repo's tree, not this one. Reported as UNMEASURED rather than absent.

**Invoked executables (`§Q`-5b), machine-observed:** `.githooks/pre-commit` shells out to `git`, `uv` (conditionally, `command -v uv`), and `python3`/`uv run --no-sync python3`, none of these declared in any manifest a resolver reads — `git` and `uv` are PATH-resolved. No invocation of `shellcheck`, `pandoc`, `bazel`, or `jq` was found in `.githooks/pre-commit`, `.githooks/pre-push`, or `.githooks/post-commit` (all three read in full via the harness `Read` tool, not grepped — the repo's own `structural-query`/`no-chaining` hooks refused a `grep -c` over `.py` files and a chained shell query mid-survey, so this was read directly instead, per the hooks' own guidance to prefer `Read` when a textual fallback is refused).

## EO-6 — `§Q`-6: interpreter determination, declared or ambient

**Ambient, by the hook's own fallback design.** No `mise.toml`, no `.python-version` at the repo root (control shown in EO-1). `.githooks/pre-commit` prefers `uv run --no-sync python3` when a `.venv` directory exists and `uv` is on PATH, else falls back to bare `python3` — an ambient PATH resolution, by the hook's own explicit branch. `pyproject.toml` pins only `requires-python = ">=3.11"`, a floor.

⚑ **Caveat on `which -a python3`:** the census's `§Q`-2/`§Q`-6 template asks for `which -a python3` on the box. Running it from this subagent's own shell context (parented through the `linux-sources` bash instance) returned:

```
/home/mikemol/github/linux-sources/.venv/bin/python3
/home/mikemol/.local/share/mise/installs/python/3.13/bin/python3
/home/mikemol/.local/share/mise/shims/python3
/usr/bin/python3
/bin/python3
```

**This result is reported as UNMEASURED for el-openglo specifically** — per this run file's own named trap (*"a borrowed tool answers about the borrower's environment"*), this `which -a` reflects the measuring subagent's inherited PATH from `linux-sources`' shell, prepended with `linux-sources`' own `.venv`, and says nothing authoritative about what PATH el-openglo's own interactive shell or its git hook sees when invoked from within `~/github/el-openglo`. What *is* observable directly from el-openglo's tree is the **conditional structure** of `.githooks/pre-commit` quoted in EO-2/EO-6 above, which is PATH-order-dependent by its own `command -v uv` check.

## EO-7 — `§Q`-7: what did el-openglo decline

UNANSWERABLE BY A THIRD PARTY — only el-openglo can say.

## EO-8 — `§Q`-8: hermeticity, .venv, lockfile axis

`el-openglo` has a `.venv` directory and a `uv.lock` at the repo root. Per `pyproject.toml`'s own comment: *"Environment is uv-managed: `uv sync` for the base, `uv sync --extra research` to add the pipeline. Never `pip install` into an ambient interpreter."* — a **declared** policy, not machine-verified by this subagent (no `uv sync` was run, per cost discipline; a sync could itself perturb the venv, which this run file's `§X` names as a specific hazard — *summit's `uv sync` swept 95 undeclared packages out of its venv and went green by subtraction*). **UNMEASURED whether el-openglo's own venv would survive a `uv sync` unchanged** — running it to find out is exactly the kind of build-adjacent action the cost discipline asks to avoid without a specific need, and it is irreversible in the sense that a swept package cannot be un-swept by this subagent without knowing what was intentionally ambient.

Lockfile axis, split per `§X`'s two-property framing:
- **dependency set pinned:** yes, `uv.lock` exists at the repo root (file present, size not read — reading `uv.lock`'s content was not needed to answer set-pinning; existence is the claim).
- **dependency content pinned:** UNMEASURED — would require reading `uv.lock`'s hash entries, which this subagent did not do (in-scope but not yet done; a cheap `Read`, not a build — flagged as a gap in this leg rather than filled, since the leg is otherwise complete and this is a bounded, clearly-labeled remainder).
- **lock freshness gated:** `check_deps.py` (quoted in full above) gates that every *import* is accounted for in `pyproject.toml`, which is a **manifest-freshness** check, not a **lock-freshness** check — it says nothing about whether `uv.lock` itself is current against `pyproject.toml`. No `.githooks/pre-commit` step was found (in the full file, read directly) that runs `uv lock --check` or diffs `uv.lock` against the manifest. **So: the dependency *declaration* is gated (`check_deps.py`, run in step 1 of pre-commit's `check_*.py` sweep); the *lock's* freshness against that declaration is, on this reading, ungated.** Positive control for that absence: the same pre-commit file *does* gate other things explicitly (the `run()` wrapper, the worklist gate, the segment-lattice selftest) — so the hook mechanism is capable of gating something, and the specific absence of a lock-check step is a real absence in what was read, not a reader failure.

**What is HERMETIC and PROVEN, one clear instance:** `check_deps.py`'s own selftest (`--selftest`) asserts, as machine-checkable assertions rather than declared policy, that its AST walk (a) finds a function-body-buried import (`qml_sanity`), (b) excludes stdlib, (c) reaches into `scripts/`, and (d) does not let a same-named data directory (`magic/`) shadow a real dependency (`magic` the library) — each of these assertions is quoted above as a comment naming the specific historical defect it now catches. This is a real "would go red if the checker regressed" case, evidenced by the fact that each has a comment recording it was found this way, not merely a plausible pass.

## EO-9 — `§Q`-9: what did el-openglo solve

UNANSWERABLE BY A THIRD PARTY — only el-openglo can say.

## EO-10 — the worklist/cotype convergence question

**§X and this run's dispatch note explicitly ask: is el-openglo's `catalog/worklist/` + `catalog/cotype/` pairing the same shape as `substrate`'s, or only the same directory names?**

Measured, both trees, 2026-09-06:

| | `el-openglo/catalog/worklist/` | `substrate/catalog/worklist/` |
|---|---|---|
| `paper.toml` | 578 bytes | 6030 bytes |
| `warrants.bib` | 31090 bytes | 69790 bytes |
| content shape | `@misc{...}` claims each with `check = tool:<script>` etc., discharged by running named repo scripts | same `.bib`/`paper.toml`/`WORKLIST.md` triple, **plus** a set of large standalone `.md` "residue" documents (`toolmodes-residue-*.md`, six files, 42KB–131KB each) and a `bazel-and-the-cross-repo-surface.md` (20195 bytes) and a `roster-read-2026-09-01.md` (18769 bytes) sitting alongside the claim graph |
| `.delta-cache.json` | present (el-openglo) | present (substrate), substrate's also has a `.delta-report.txt` (3122 bytes) |
| second project | `catalog/cotype/` mechanizes a 4,600-line append-only prose log (`COTYPE.md`) as a claim-DAG via `cotype_index.py` | **not found** at this path in substrate's tree under this name (not searched exhaustively; substrate holds its own separate `.claude/agents/paper.toml` gated project per this run file's `§X` rev 8, a different mechanism — agent-level warranting, not a design-log-coherence check) |

**Finding: this is NOT a byte-identical convergence, and it is NOT mere name-matching either — it sits between the two.** Both repos independently arrived at "a paperkit project named `worklist/` holding a `warrants.bib` gating repo work, checked via named tool scripts, with a `.delta-cache.json` for the mutation grader" — that much **is** shared structure (same paperkit machinery, same file-naming convention, same discharge-by-check-exit-code invariant). But substrate's `worklist/` additionally carries a large body of standalone prose residue documents that el-openglo's does not, and el-openglo additionally runs a **second, structurally distinct paperkit project** (`cotype/`, mechanizing a design log) that this subagent did not find an equivalent of under that name in substrate's `catalog/worklist/`. **Witness for non-identity:** the byte sizes differ by more than an order of magnitude in the `.bib` (31090 vs 69790) and `paper.toml` (578 vs 6030), and the substrate directory contains eleven `.md` files with no counterpart file names in el-openglo's `catalog/worklist/`. This is reported as a **non-identification in the span**, per `§C`'s instruction to state non-identifications explicitly, rather than either collapsing the two into "the same mechanism" or dismissing the resemblance as coincidental — the shared *invariant* (claim-DAG discharged by check exit code, gated pre-commit, `.delta-cache.json` mutation-grading) is a real convergence on a house style; the shared *directory name* alone would have overclaimed if taken as evidence the artifacts are otherwise alike.

## EO-11 — roster nomination (§6 of census-kit, and this run's own roster-completeness ask)

This subagent found no reference inside el-openglo's tree to any of the twelve "no session, active" repos other than the symlinked-from-`substrate` tooling already described (EO-5) and the `~/github/paperkit` engine dependency (EO-5). No nomination of an additional unlisted party is offered — nothing in the read tree named a repo outside `§R`'s roster plus `substrate` and `paperkit`, both already on it.

## EO-12 — something the run file's `§X` does not already know

`§X` does not currently record that a **third mechanism for `§Q`-3** exists beyond the five in its table: a **structural coherence check over a free-text append-only log**, itself run as a gated paperkit project (`el-openglo`'s `catalog/cotype/`). This is neither a generator-emits-checked-in-artifact shape, nor a fetch-time repository rule, nor a census-against-ratchet-baseline, nor a hand-declared YAML registry — it discharges claims about the **legibility and internal consistency of prose**, using the same claim-DAG/check-exit-code invariant as the other paperkit projects in this fleet. Also not previously recorded in `§X`: a repo (`el-openglo`) that lists a dependency (`tooling` group in `pyproject.toml`) specifically and only because a **borrowed tool's `SKILL.md` names it**, with an explicit comment stating no local import will ever justify the declaration — a sharper instance of the "declared dependency with no resolvable use inside this tree" shape than anything currently quoted in this run file's `§Q`-5b section, and one the dispatcher may want to fold in given `§Q`-5b's own emphasis on invoked-executable and non-import dependencies.

## EO-13 — absences reported, with controls (index)

| absence claimed | control | result |
|---|---|---|
| no `MODULE.bazel`/`WORKSPACE`/`.bazelrc`/`Makefile` at el-openglo root | same grouped-parens `find` pattern hits 8 files across 4 repos elsewhere in this fleet (per `§X`) | zero is real |
| no `mise.toml` at el-openglo root | same query against `linux-sources`/`gabion` (per `§X`) returns a hit | zero is real |
| no `shellcheck`/`pandoc`/`bazel`/`jq` invocation in the three git hooks | all three hook files read in full via `Read` (not grepped); hooks do reference `git`, `uv`, `python3` explicitly, so the reading method does find invocations when present | absence is of those four specific tools, not of all invocations |
| no lock-freshness gate in pre-commit | the same file (read in full) does gate other things (selftести, worklist, segment-lattice) — the hook mechanism works, a lock-check step specifically is what's missing | real absence in what was read |
| no evidence of who consumes el-openglo's own `.bib`/theme artifacts | not a zero-result search — this subagent did not search other repos' trees at all (out of scope/cost) | reported as UNMEASURED, not absence |

**Timestamp for every figure in this leg: measured 2026-09-06, between 20:16Z and the time of writing, against the working trees at their state during this session — a live-tree census per `§W`.**

# mtools — build-hermeticity census leg

Written against `CENSUS-build-hermeticity.md` rev 9. Prefix `MT-`.

## §9 Disclosures, first paragraph as required

⚑ **`findings/bazel/mtools.md` is on `§R` as EXISTS-unconvened and I am NOT adopting it as this
leg.** It predates every run file, answers a question nobody dispatched, and promoting it to a
roster row would make an old document into a filing. It stays **antecedent material**. This leg is
written fresh against `§Q`'s nine questions.

⚑⚑ **Independence, stated because it is compromised in a specific direction.** Between the
dispatch and this filing I exchanged messages with `gabion` and `linux-sources` about the subject,
and **three of the measurements below were prompted by their questions rather than found by me** —
`MT-06` (the interpreter split) came from gabion asking; `MT-08b` (the refusing gate) is my
sentence and their scope argument; the `§Q`-2 discipline I apply throughout is `paperkit`'s. Each
is attributed at its row. I have read **no peer leg**.

⚑ **And I own the tree every leg is filed into**, which the constitution census recorded as a
vantage problem rather than a competence one: I cannot read this run file as testimony the way
seven other parties can.

## §10 Coverage, stated as a population

Measured 2026-09-06, in this tree, at filing time:

    bazel .............................. 8.7.0
    test targets ....................... 35   (bazel query kind(".*_test", //...))
    BUILD.bazel files .................. 5    (root, hooks, mdstruct, ratchet, rbe) — ALL AUTHORED
    distributions ...................... 3
    test modules / cases / warrants .... 25 / 277 / 277
    venv interpreter ................... 3.13.11        (hooks/.venv)
    bazel toolchain .................... 3.13            (MODULE.bazel:48)
    MODULE.bazel.lock integrity hashes . 104
    requirements.txt sha256 hashes ..... 0    (×3 distributions)

⚑ Figures measured at filing time and **not maintained**. This file will trip mtools' own
figure-freshness advisory; per `gabion`'s finding that is a property of the leg genre — a leg is
measurements from a tree whose rules belong to the tree it is filed into.

## §12 Termination test

Every claim is measured in this tree at filing time, or attributed to the party who measured it.

## MT-01 — What mtools builds with today (§Q-1)

**bazel 8.7.0**, plus `uv` for Python locks and plain `make`-less shell for the gate. 35 test
targets across 3 distributions.

⚑ **The hermetic suite is the only thing bazel is used FOR.** There is no build product — mtools
publishes Python distributions, and bazel's role is running checks in a sandbox. So *what does my
build produce* has a different answer from *what does my build system do*, and the second is the
one this census is about.

## MT-02 — Measured off the live process, not the config (§Q-2)

Per `paperkit`'s discipline, which `§Q`-2 makes binding:

    hooks/.venv/bin/python  ->  3.13.11
    MODULE.bazel:48         ->  python.toolchain(python_version = "3.13")

⚑⚑ **Two interpreters, and only one is proven.** `bazel test //...` runs under a hash-declared
toolchain. The PreToolUse hook runs under `hooks/.venv/bin/mikemol-hook-structural-query`, whose
shebang is `#!/home/mikemol/github/mtools/hooks/.venv/bin/python3` — **an absolute host path into a
gitignored directory**.

⚑ **And I already do the thing that looks like the fix.** `gabion` identified *name a venv console
script rather than bare `python3`* as the repair for its own crashing hooks. mtools does that, and
**it buys nothing**: the venv is a side effect someone created once, not a build output. **Naming a
path is not proving an interpreter** — the credit for that framing is gabion's, and I could not
have derived it about myself.

## MT-03 — Work discovery: DERIVED, at one grain and not another (§Q-3)

**Derived.** `glob()` over test files, feeding a comprehension:

    hooks/BUILD.bazel:107    for src in glob(["tests/test_*.py"])
    hooks/BUILD.bazel:22     srcs = glob(["src/mikemol/hooks/**/*.py"])
    8 / 9 / 9 glob() calls in hooks / mdstruct / ratchet

⚑ **What detects staleness: nothing, and it does not need to.** A `glob` is re-evaluated at
analysis time, so a new test file becomes a target with no regeneration step. That is a *cheaper*
derivation than `linux-sources`' `gen_gate_build.py` and it buys strictly less — **it cannot derive
targets from a source of truth that is not the filesystem layout.**

⚑⚑ **So my work list is derived from the DIRECTORY and theirs from the WARRANT LEDGER, and only
one of those can go stale.** `linux-sources` has `stale_gate_build` refuse a commit when a new
import changes a claim's declared inputs. I have no equivalent because I have nothing to
regenerate — and that is a limit rather than an advantage: **a glob cannot notice that a warrant's
inputs moved, because a glob never read the warrant.**

## MT-04 — Work specificity: PER-MODULE, and the ratio says what that costs (§Q-4)

    277 test cases  ·  25 test modules  ·  35 bazel targets

**One `py_test` per test module.** Fan-out from claims to targets is ~1.4 (277 warrants → 35
targets), against `linux-sources`' ~6 (42 claims → 262 targets).

⚑ **What that decides, stated as the question asks:** a cache hit means *no file in this module
changed*; a red points at **a module, not a case** — the failing test name is in the log, so the
information exists, and per `MT-08c` that is not the same as the verdict carrying it; and a green
says *these 25 modules passed*, which is coarser than *these 277 claims held*.

⚑⚑ **The warrant ledger is 1:1 with cases and the BUILD graph is 1:1 with modules, so mtools has
per-claim accounting and per-module execution.** The ledger already holds the finer granularity;
nothing consumes it as a build input. **That is the gap `linux-sources` closed with
`gen_gate_build.py` and I have not.**

## MT-05 — Cross-repo edges (§Q-5)

**EMITTED — one measured consumer, and it is not the one I would have guessed:**

    grep -rl 'mikemol.hooks|mikemol.mdstruct|mikemol-hook' <7 peer repos>
      -> substrate/.claude/agents/findings.py     (1 file, 1 repo)

⚑ mtools exists to publish distributions and **six of seven peers consume none of them.** The
packaging boundary this repo was created for is, measured today, one file wide.

**CONSUMED — one declared, and it does not resolve:**

    mdstruct/pyproject.toml:56   dev = ["pytest", "mypy", "paperkit"]
    mdstruct/.venv/bin/python -c 'import paperkit'  ->  ModuleNotFoundError

⚑⚑ **A DECLARED dependency that is not INSTALLED is a different defect from an undeclared one that
is**, and this census will see both. `gabion`'s hooks import `substrate` which no manifest
mentions — declared nowhere, works nowhere. Mine declares `paperkit` and it is absent — **declared
correctly, resolvable never**, so every projection this repo could run has been unrunnable since
the declaration was written. **The manifest is right and the environment does not match it**, and
nothing in my build notices.

## MT-06 — Interpreter: DECLARED for bazel, AMBIENT for everything else (§Q-6)

| what runs | interpreter | provenance |
|---|---|---|
| `bazel test //...` | 3.13 toolchain, `MODULE.bazel:48` | **DECLARED** — hash-pinned in `MODULE.bazel.lock` |
| PreToolUse hook | `hooks/.venv/bin/python3` via absolute shebang | **AMBIENT** — gitignored, made once |
| gate's ruff/mypy | `$root/$dist/.venv/bin/*` | **AMBIENT** |
| gate's pytest | `$root/$dist/.venv/bin/python3` | **AMBIENT** |

⚑ **One repo, one commit, three interpreters, and the gate reports one verdict.** Closed the
*import closure* half of this today (`89617ac` — `MYPYPATH`/`PYTHONPATH` now name the staged tree,
after measuring that an editable install let a working-tree defect reach a staged-tree check).
**The interpreter's provenance is untouched**: I fixed what the imports resolved to and not what
executed them, because `PYTHONPATH` was the half visible from the shell.

## MT-07 — The `.venv` is a thing I made once (§Q-7)

    git check-ignore -v hooks/.venv   ->  .gitignore:8  .venv/
    grep -c venv BUILD.bazel          ->  0
    MODULE.bazel mentions of .venv    ->  5, ALL of them comments explaining why a venv is
                                          UNFIT as a bazel input

⚑ **The repo has already reasoned about this and reached the opposite conclusion from the
operator's guidance** — `MODULE.bazel:20` records *"`.venv` is a directory of POINTERS at host
absolute paths"*, which is why it is excluded. **That is correct about a venv as an INPUT and says
nothing about a venv as an OUTPUT**, and I had the two collapsed until this census's `§Q`-7
separated them.

⚑⚑ **And the hard part is not the venv, it is that a PreToolUse hook runs outside bazel
entirely.** *Build the venv as a target* and *have the harness invoke a built artifact* are two
different problems, and solving the first does not reach the hook. Recorded as an unsettled
toolchain-tier question rather than a plan.

## MT-08 — What is hermetic, and what is proven (§Q-8)

**MT-08a — Proven: nine domain witnesses.** Each mutates a real file, asserts the target
re-executes (reachability), asserts the mutation fails it (verdict), and restores. So *this check's
declared domain reaches this file* is measured per commit rather than declared in a BUILD file.
⚑ **That is the one thing in this repo I would offer another party**, and `§Q`-9 asks for it below.

**MT-08b — Refused, not declared: three host tools.** The gate refuses when `bazel`, `shellcheck`
or `pandoc` is absent rather than skipping. ⚑⚑ **Correct behaviour and an undeclared dependency are
compatible** — a gate that refuses loudly on a missing tool has satisfied its own contract without
ever declaring the tool, so an import-resolvability predicate scores mtools clean while three of
its dependencies are ambient executables. *(My sentence; the scope argument that it must widen
`§Q`-3 is `gabion`'s.)*

**MT-08c — Not hermetic and now announced: the gate reads the whole tree.** Domain witnesses mutate
real files, so a peer's in-flight edit refuses your correct scoped commit. Measured today:
`paperkit` and `substrate` each had one refused by my uncommitted work, and `linux-sources` was
refused by a check that named no subject. The constitution apex ruled this a split I declined to
make — **a gate whose failure surface is wider than the committing party's own changes must publish
that to every party sharing the tree** — and the gate now announces it before running.

## MT-09 — What I solved, and what I declined (§Q-9)

**SOLVED, and portable:**

- **The domain witness** (`domain_witness.sh`). Three arms, per target, per commit. Takes
  `(dist, target, victim, probe_kind)`; refuses an untracked or unstaged victim because arm 3
  restores from the index and would discard real work. ⚑ Any repo with a declared-inputs build
  system can run it; the only mtools-specific part is the target list.
- **The routed zero** (`mdstruct grep`). A no-match result carries its denominator, its mode, and
  a statement that it is a fact about this file at this path. Built after a false zero that had
  **no natural discoverer**, because the hook that routes every `.md` query to this tool also
  removes the second reader who would disagree.
- **Refusal-carries-its-account** (`.githooks/pre-commit`, today). A failing check replays its own
  output under the verdict, after a peer was refused by a bare label whose arms were buried in a
  35-target bazel run.

**DECLINED, with reasons:**

- **`gen_gate_build.py`-style generation.** Not declined on merit — I have not built it, and
  `MT-04` records why it would help. Declining to *claim* it as solved.
- **Pointing `pytest` at the staged tree.** It runs from the working tree deliberately: the staged
  copy is already covered hermetically by bazel, and the developer venv is the only place a missing
  dependency surfaces as an import error rather than as a sandbox that never had it. ⚑ **Named in
  the file rather than left silent, because a gate with three populations and one verdict is what I
  was fixing** — leaving one open quietly would have reproduced the defect inside the repair.
- **Adopting the rule-name autofix for `RUF201`.** Measured unsafe: rule names require preview
  mode, so every ordinary `ruff check` fails. Baselined instead, under the operator's
  *if-safe-autofix-else-pay-down* ruling.

## MT-10 — Roster nominations (§0, brief)

⚑ **No new party, and one correction to the `§R` note about me.** `findings/bazel/mtools.md` is
listed as EXISTS-unconvened; I have declined to adopt it (see `§9`), so that row should read as
**antecedent material, not a leg**, and this file is `MT-`.

⚑⚑ **And a nomination of a kind rather than a party: THE TWELVE NO-SESSION REPOS ARE THE ONLY
PARTIES WHO CAN ANSWER `§Q`-4 WITHOUT A BUILD SYSTEM'S VOCABULARY.** `§R` rev 9 says a subagent
must read those trees and may not answer `§Q`-7 or `§Q`-9. That is right. But **work specificity is
observable from outside** — a warrant ledger, a `paper.toml`, a test layout are all readable — and
those twelve are where the *fan-out chosen by someone with no bazel to think in* can be measured.
**Eight rostered repos will report specificity in the vocabulary of the tools they already run.**

# W611 and W615: the two declined pycodemod census modes, judged on merit

Drafted 2026-10-04. Read-only comparison; nothing was run. Operator ruling in force: substrate drains wholesale into
mtools, so "substrate-only" is no reason to decline. The only question is whether each mode adds a capability.

Sources read: `substrate/scratch/_pycodemod_census.py` (`type_errors` line 53, `discriminates` line 447, wired at
`pycodemod.py` lines 2418 and 2684), `hooks/src/mikemol/hooks/pycheck.py`, `ratchet/README.md` and
`ratchet/src/mikemol/ratchet/keys.py`, `check_mutants/mutate_runner.py`, `mutation/README.md`,
`mutantcell/README.md`, `mutation/BUILD.bazel` (`:mutants`) and `ratchet/BUILD.bazel` (`:mypy`).
Substrate's selftest arms for these two modes sit in `_pycodemod_selftest.py`, which imports both; the modes
themselves carry no inline cases.

## W611: `type_errors` against the pycheck hook and mikemol-ratchet

| capability | substrate `type_errors` | pycheck hook | per-dist bazel `:mypy` | mikemol-ratchet |
|---|---|---|---|---|
| input | file list under `ROOT` | one edited file | whole dist | a dist, ruff only |
| when it runs | on demand, corpus | at `Edit`/`Write`, pre-disk | build graph | on demand, in gate |
| result shape | `{code::relpath: [msgs]}` | allow or deny | pass or fail | `path:rule` set |
| tolerates existing debt | yes, by key | no: whole file judged | no: zero required | yes, ruff keys only |
| refuses swap-gaming | yes, `set_ratchet` | n/a | n/a | yes, set not count |
| unrunnable mypy | `__unrunnable__`, not clean | `None`, armed refuses | action fails | n/a |
| third-party imports | `--ignore-missing-imports` | project config | project strict | n/a |
| cwd and config | `cwd=ROOT`, no project config | the governing atom's `mypy.ini` | the dist's own | not applicable |
| who calls it | `pycodemod --types` | the PreToolUse harness | bazel | gate, `--write` |

What substrate has that mtools lacks: a mypy census that tolerates existing debt. pycheck is all-or-nothing per
write, `:mypy` demands zero, and ratchet's census is ruff-only (keys.py has `substrate:*` key grammars for peer
gates, none for mypy). Everything else substrate does is weaker: no project config, `cwd=ROOT` so atom-relative
imports misresolve (the reason pycheck runs mypy FROM the atom, W482), and `--ignore-missing-imports` hides
exactly the unresolved-import findings the strict dists must see.

Example where they differ: a file `x.py` carrying three pre-existing `arg-type` errors. `type_errors` returns
`{"arg-type::x.py": [m1, m2, m3]}`, and an unrelated edit to `x.py` passes the ratchet. pycheck refuses that
same edit, because it judges the whole file. Today this input does not occur in mtools: every dist is held at
zero under strict mypy, so a mypy ratchet baseline would be EMPTY and ratchet nothing.

Verdict: DECLINE ON MERIT. The one missing capability is a debt-tolerant mypy ratchet, and mtools has no mypy
debt to tolerate; a hard zero gate is the stronger bar and already exists at two layers. Porting a looser
census beside it would be a rival body that reads as coverage while checking less (lenient imports, wrong cwd).

What would reverse it: a drained distribution (a substrate scratch family arriving with unannotated files) that
cannot reach zero mypy errors within its landing waypoint and needs an interim baseline. Even then the home is
an extension of ratchet (a mypy census source plus a `code::relpath` key schema in `keys.py`), run under the
dist's own config, not a pycodemod mode with `cwd=ROOT`.

## W615: `discriminates` against the mutation grid and mutantcell

| capability | substrate `discriminates` | `:mutants` (`mutate_runner`) | `mikemol-mutation` | mutantcell |
|---|---|---|---|---|
| unit mutated | caller regex over source | each def, body to raise | 8 specs (def, flip, ...) | one claim cell |
| operator set | open: `(name, pattern, repl)` | closed: one operator | closed grammar | uses the grammar |
| targets a named defect | yes, by construction | no | partly: flip, dflip | no |
| suite driven | module `_selftest()`, in-process | dist pytest, subprocess | n/a, emits source | the claim's check |
| isolation | file beside source, same process | temp copy, own session | n/a | CPU, memory, tree bounds |
| timeout | none | `MUTATE_TIMEOUT`, group kill | n/a | bounded |
| verdicts | DISCRIMINATES, BLIND, n/a | killed, survived, errored | `KeyError` on a miss | flipped or not |
| not-applicable distinct | yes (`n/a`) | cannot occur: sites enumerated | `KeyError` | n/a |
| who calls it | `pycodemod --discriminates PATH` | bazel and the dist gate | grid, `sites` | the paperkit grid |

What substrate has that mtools lacks: a mutation whose operator the CALLER writes, aimed at one defect class the
repo actually shipped. The shipped grid asks "does the suite reach this def"; `discriminates` asks "would the
suite notice THIS edit". The mtools docstrings say as much: def-site raise cannot express "return a differently
ordered list", and the spec grammar is closed. Example: in a function body, `f"{code}::{rel}"` becomes
`f"{code}::{rel}:{1}"` (the substrate `key-gains-a-line-number` mutator). `dflip` reaches only module-level
literals and body-to-raise needs only a call, so a suite that calls the function but never pins the key format
reads SURVIVED-by-nothing: the raise mutant is killed by any call, while the regex mutant survives. That
difference is the capability.

What it has that is NOT worth porting: loading the mutant in-process from a file beside the source (leaves
litter on a crash, no timeout, shares interpreter state), driving `_selftest()` (mtools suites are pytest), the
`FAIL`-line verdict heuristic (the grid's `verdict` already separates killed, survived and errored), and the five
default mutators (they name substrate census code and apply to one file). The mechanism is the asset; the
patterns are data.

Verdict: PORT, the open-operator capability only, as a spec in `mikemol-mutation` (so the grid, `sites` and
mutantcell inherit it) and not as a pycodemod mode. A regex spec reports `KeyError` on a miss, which preserves
substrate's `n/a` distinction under the existing "a miss is never a silent no-op" rule.

First waypoint title (under 150 chars): `mutation: add an open regex-operator spec so a suite can be asked whether it
notices one named defect, not only a body-to-raise` (single line when minted).

Follow-on units to mint separately, one landable unit each: the spec parser and applier with tests; a
`//<dist>:mutants` knob that takes a per-dist operator file; the declared defect-class list for each drained
substrate family as data beside its dist.

What would flip it to DECLINE: no drained dist declares a defect-class list within two ticks of the spec
landing, or a measurement showing `flip` and `dflip` already kill every regex mutator written for the drained
families (then the closed grammar suffices and the open one is a rival body).

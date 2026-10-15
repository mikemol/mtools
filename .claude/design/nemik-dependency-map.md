# nemik dependency map (mtools:W1251, for nemik:W514)

Derived 2026-10-15 from the syntax trees of 15 repos by `mikemol.corpus.depmap`; nothing was moved
and nemik's tree was only read. Four edge kinds, each read from the AST, never from a text search
of code. The reader's blind spots are printed on the first lines of every run.

## Generator

    env -C corpus PYTHONPATH=src .venv/bin/python -W ignore -m mikemol.corpus.depmap \
        [--rows] [--mention nemik] ROOT [ROOT ...]

The run behind the numbers below named: nemik, mtools, aeternum, el-openglo, gabion, gcalculus,
paperkit, resumes, rosettapkg, linux-sources, substrate, summit, amr-skills, luthen-observability,
life (every repo with a queue except the three worktree copies). `--rows` gives one row per
occurrence with file:line; the default is `COUNT kind source target`. A file under a `tests`
directory reads as `<source>:tests`.

## Import edges (what runs when something is imported)

nemik imports three mtools dists, every use through a vendored wheel pinned at ca6702b (nemik's
pyproject lines 19-27; six wheels: pathsforward, hooks, icsstruct, fence, rulerseq, frontier):

| nemik module | imports | kind |
|---|---|---|
| adapter, alarm, check, marks, metrics, realize, residue, score | mikemol.pathsforward | 8 modules; adapter, alarm and check also import it inside a definition |
| blocks, rank | mikemol.frontier | deferred (inside a definition) |
| serve | mikemol.rulerseq | deferred |
| tests: realize, residue | mikemol.pathsforward | deferred |
| tests: ruler_table | mikemol.rulerseq | module level |

No file in any of the 15 repos imports `nemik`. nemik is a sink of import edges, never a source:
the unification therefore moves a producer into a consumer's repo, and no third repo needs a
rewritten import.

Other importers of `mikemol.pathsforward` are mtools' own: `debtplan` (queue.py and 3 tests) and
pathsforward itself. No other fleet repo imports it; they reach it only through the CLI.

## File-format contract (which file one tool reads or writes)

This is the coupling that matters. In nemik, src and tests together, 51 string constants name
`paths-forward.json`, 2 the `.ledger` and 2 the `.marks.jsonl` (a first run, before tests were
split into their own source; rerun with `--rows` for the split). The writer that owns the format is pathsforward
(`foreign.py:31`, `marks.py:33`). The same file is read by a THIRD lineage that is neither:
mtools' hooks dist names it in `build_failure`, `commit_kata` (all three of json, ledger, md),
`inbound_asks`, `nemik_check`, `revendor_apply`, `standing_facts`, `tick_stop` and
`work_claims_hook`, and debtplan writes cards into it. So the queue format has one writer and at
least four independent readers across two repos, and a format change today is coordinated by
letters, not by a type.

## CLI contract (which executable one tool runs)

Only literal argv lists are read. The result is the honest-empty case: nemik shows `git` (13) and
`kubectl` (1); pathsforward shows `opa` (1). NO row connects the two lineages. That was a blind
spot of the reader, not an absence, and the next section closes it (W1252).

## CLI contract, second reader (mtools:W1252)

`depmap` now also reads `tool` (a string constant that is exactly `mikemol-*`/`nemik-*`), `hook`
(commands in `.claude/settings.json`, by event and matcher) and `shell` (names on non-comment
lines of `*.sh` and `bin/` files). Over nemik and mtools:

- nemik -> mtools: 6 constants naming `mikemol-paths-forward` in src (12 more in tests),
  `mikemol-ics` once, and a settings.json that wires 7 `mikemol-hook-*` commands.
- mtools -> nemik: hooks names `nemik-check` (2 shell lines, 1 constant), katas names `nemik-check`
  and `nemik-rank`, pathsforward's tests name `nemik-witnesses`.
- So the CLI contract exists and runs BOTH ways, through constants and hook wiring, never through
  the literal argv the first reader could see. Noise: `nemik-45` (a session name), `nemik-cal-` and
  `nemik-never-writes-a-queue` (fragments) are not tools.

## Reader independence (input to W517's contract question)

Of the readers of `paths-forward.json`, only nemik (11 modules) and debtplan import
`mikemol.pathsforward`. The eight hooks modules and katas do not: they parse the file with their
own code. Those are the independent readers, so they are where a schema both sides test pays first;
nemik and debtplan share the model and break together with it, loudly, at a pin bump.

## Where pathsforward assumes nemik is not its concern

`--mention nemik` over pathsforward's `src/` finds the word in 20 modules, 75 comments and
docstrings in all (its tests add 52 more), concentrated in `ops.py` (20), `check.py` (15),
`cli.py` (10), `ledger.py` (4), `model.py` (4), `closure.py` (2), `gate.py` (2), `inbound.py` (2). They read as one of three
things: a rule cited to a nemik card (`nemik:W<n>`, the bulk), a statement that nemik reads a field
(`check.py`, `model.py`), and a refusal whose shape nemik dictated (`ops.py`). The third kind is
the architectural one: pathsforward carries nemik's shapes as comments rather than as a contract
both lineages test, so `nemik-check` and `--check` disagree whenever the comment drifts. Run
`--mention nemik --rows` for the line numbers.

## Inputs to W517

- mtools:W1229 is the pin table (which repo pins which sha, vendored wheel or git).
- `mikemol-repin --check-must-have` and `repin/must_have.json` (mtools:W1137) already name the
  fixes a consumer pin must carry; a unified repo retires the vendored-wheel step for nemik.
- Reproduce: the aggregate for nemik plus mtools is ~31 KB; regenerate rather than store it.

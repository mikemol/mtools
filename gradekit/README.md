<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-gradekit

Four of paperkit's `tools/` modules moved together into mtools (mtools:W548, a cut of W532):
`verdict`, `grades_rec`, `read_grade` and `effective`. `report_refresh` is NOT here; it stays in
paperkit (decision recorded on W548).

This distribution depends on three sibling distributions, by the operator's ruling of mtools:W562
(mechanism A+B, measured in W566): `mikemol-grade` (the ladder and the clamp), `mikemol-bibparse`
(the claim-edge reader) and `mikemol-atomicwrite` (the durable write). They are path sources in
`[tool.uv.sources]` (not editable, which hides them from mypy) and `py_library` dependencies in
`BUILD.bazel`. The pip hubs `gradekit_deps` and `gradekit_dev` do not know them.

| module | does | console script |
|---|---|---|
| `mikemol.gradekit.verdict` | the verdict record authority: `emit`, `exists`, `agg`, `agree`, `calc`, `cohere`, `canary`, each writing one compact record atomically | `mikemol-gradekit-verdict` |
| `mikemol.gradekit.read_grade` | reads a calculation record into a grade record carrying the tests, the baseline word and the three reasons | `mikemol-read-grade` |
| `mikemol.gradekit.grades_rec` | joins a project's metadata to the per-claim grade records and applies the clamp over the graded claims | `mikemol-grades-rec` |
| `mikemol.gradekit.effective` | joins grade files to the bibs' edges and clamps each claim by what it rests on and delegates to | `mikemol-effective` |
| `mikemol.gradekit.jsonio` | checks a JSON file into the ladder's `Json` type, or refuses it by name | none (library) |
| `mikemol.gradekit.cli` | the shared command-line boundary: option taking and one-line failure reports | none (library) |

`mikemol-verdict` is taken by `mikemol.hooks.verdict`, so the verdict script carries the
distribution name.

## What changed from paperkit

- **No `sys.path` edits, no `__file__` layout.** The three modules that inserted paperkit's
  engine directory and imported `grade` or `bib` now import `mikemol.grade.grade` and
  `mikemol.bibparse`. Nothing computes a root from its own location.
- **`verdict` no longer carries its own atomic write.** The paperkit tool duplicated
  `durable.write_atomic` on purpose, because it was staged into a sandbox as a lone file, and a test
  gated the two for agreement. DECISION: it imports `mikemol.atomicwrite.durable.write_atomic` and
  the duplicate is gone; this package is installed beside its dependencies, so the lone-file
  reason does not hold. The agreement test has nothing left to compare.
- **`effective` reads edges through `mikemol.bibparse.edges.claim_edges`** instead of
  `bib.parse_project`: one call, key to `rests_on` list and `check` string. It no longer runs the
  engine's paper.toml placement guards, the unknown-field warnings or the `entails` refusal
  (effective never read those fields). It also refuses a key defined twice inside one bib, which
  paperkit allowed.
- **Failures are exceptions at the library layer and one line at the command line.** bibparse
  raises `ProjectError` (no paper.toml, a bad `warrants` list, a missing bib), `DuplicateKeyError`
  and `BibSyntaxError`; the scripts catch these and the package's own `RecordError`, `UsageError`
  and `OSError` at `main`, print `<script>: <message>` on standard error and return 2. Paperkit
  let these escape as `SystemExit` messages or tracebacks.
- **Inputs are checked.** A grade, calculation or metadata file is read into the ladder's `Json`
  type: a float anywhere, a missing required field, or a value of the wrong type is refused with
  the file and field named. Paperkit raised `KeyError` or passed the value along.
- **`verdict` uses the public names.** `grade._grade_from_sens` is `grade_from_sens` and
  `bib._SCOPES` is `grade.SCOPES`.
- **`verdict agg ... below:<floor>` with a floor that is not a rung** exits 2 with a message
  instead of a `KeyError` traceback. It still refuses; it never grades everything green.
- **`verdict cohere` takes `--coherence SCRIPT`** (default `paperkit/coherence.py` under the
  working directory, as before) so the script is a parameter, and `verdict emit` takes
  `--account FILE` as before. The other subcommands reject both options.
- **`main(argv=None)` on every script, each with a `__main__` guard.** Output goes through
  `sys.stdout` at call time.
- Output bytes are unchanged for the same inputs: `effective` keeps its indent of 2 and its
  claims sorted by key.

## Paperkit call sites to repoint

Rules that stage a tool as a lone script: `tools/verb.bzl:23` (`_VERDICT`) and `:329`
(`grades_rec.py`), `tools/grade.bzl:134` and `:194`, `tools/calc.bzl:696`, `:721`, `:750` (each
`//tools:verdict.py`) and `:761` (`tools/read_grade.py`), `tools/bibtex.bzl:1210` and `:1226`
(`//tools:read_grade.py` as data), `tools/calc_demo/BUILD.bazel:9`, and the `exports_files` line of
`tools/BUILD.bazel:8`. Tests that read the sources: `paperkit/tests/boundaries_ladder.py:38` and
`:88` (the `grade.below` derivation in verdict), `boundaries_agree.py:73`, `boundaries_scope.py:99`
(read_grade staged alone) and `boundaries_write_atomic.py` (gated the duplicate that is now gone).
`effective.py` has no caller in paperkit's rules.

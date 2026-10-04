# W612-W614: the three census modes declined 2026-09-26, re-read at source

Source: `/home/mikemol/github/substrate/scratch/_pycodemod_census.py` (lines 133-338, 996-1223) and its arms in
`scratch/_pycodemod_selftest.py` (lines 956-1000 `--projects`, 1062-1128 `--artifacts`). Operator ruling 2026-10-04:
"substrate-only" is not a reason to decline. Each mode is judged on its merit and its operands.

| Waypoint | Mode | Measures | Recommendation |
| --- | --- | --- | --- |
| W612 | `--artifacts` | which tools read a failure-bearing artifact | PORT |
| W613 | `--touches` | which files and flags one function reads | PORT |
| W614 | `--projects` | paperkit projects and their foreign bibs | ASK paperkit |

## W612: build_artifact_readers

What it measures: for each python file, the string literals that name a build artifact, split by whether the
artifact can hold a failure (`FAILURE`), only a success (`SUCCESS`), or both (`BOTH`). For whom: anyone deciding which
tools emit commit-blockers by construction (a tool that reads failure records produces blockers). Its worth is the
discrimination, not the vocabulary: docstrings and comments are not reads (CST, so prose is excluded), and a
vocabulary pair where one token is a prefix of the other (`.agdai.log` versus `.agdai`) must match failure first and
subtract before the success pass. Both are generic and both have arms.

Substrate-specific names and how each becomes an operand:

| Origin name | Where | Becomes |
| --- | --- | --- |
| `FAILURE_BEARING` tuple (Agda vocabulary) | module constant | required operand `failure: Sequence[str]` |
| `SUCCESS_ONLY` tuple | module constant | required operand `success: Sequence[str]` |
| `_pycodemod_core.ROOT`, `py_files()` | relpath base, default population | `paths` operand plus `relative_to` operand |
| `shared_cache`, `SUBSTRATE_NO_CACHE`, `_l2_cached` | L2 memo | dropped; no cache in the first cut |
| `cst is None` silent `continue` | libcst probe | removed; libcst is required |
| `len(v) < 80 and "\n" not in v` | literal filter | named constant `MAX_LITERAL`, kept |
| `except Exception: continue` on parse | skipped file | a reported `Skip`, never silent |

Two defects to record in the cut, not carry over: the failure match is case-sensitive while the success match is
`.lower()` on both sides, so the same token can match differently by side (make both exact, or both folded, and say
which); and an unreadable or unparseable file vanishes from the answer (report it as `Skip`, as `size.py` does).

Cut plan: one module `pycodemod/src/mikemol/pycodemod/artifacts.py`. API
`artifact_readers(paths, failure, success) -> Readers` with `rows: list[Reader]` (path, matched artifacts, bearing)
and `skipped: list[Skip]`, frozen slotted dataclasses like `Size`/`Sizes`. A `_Literals` CSTVisitor collects
non-docstring short literals (a docstring is the sole expression of an `Expr` statement). No ROOT global. CLI wiring
in `cli.py` is a second, later unit: `--artifacts --failure TOKEN... --success TOKEN...`, refusing to run when either
list is empty (an empty vocabulary measures nothing and must not read as a clean census).

Arms to transcribe (selftest lines 1069-1128), all with the vocabulary passed in rather than imported:

1. a file reading `.agdai.log` is FAILURE
2. a file reading `.agdai` cores is SUCCESS, not FAILURE (the prefix-subtraction case)
3. a file reading `.agda-times.tsv` is SUCCESS
4. a file reading both is BOTH and names both artifacts, in the order `fail + succ`
5. a file reading no artifact is absent from the census (no third verdict)
6. an artifact named only in a docstring or comment is not a read
7. new: an unparseable file lands in `skipped`; an empty vocabulary is refused

Recommendation: PORT. First waypoint title (under 150 chars): "pycodemod: artifacts.py, which tools read a
failure-bearing build artifact, vocabulary supplied by the caller, prose excluded by CST, skipped files reported".

## W613: touches

What it measures: for ONE named function in a source file, the files it reads (every `os.path.join` over string
literals, following three same-scope bindings: `x = "lit"`, `for x in ("a", "b")`, and `import m` which resolves to a
tool file), the paths it could not resolve (reported as `unresolved`, never approximated), and the flag-shaped string
literals it tests for (`"--set"`, `_name`). For whom: a planner ordering work items. Code-warranted edges (item A's
witness reads what item B's work edits) complement prose-warranted ones. The origin's `--touches` driver then groups
co-readers into hyperedges and orients them with `dagcone.orient_hyper`; that driver is CLI and sits outside the
census function.

Substrate-specific names and how each becomes an operand:

| Origin name | Where | Becomes |
| --- | --- | --- |
| `catalog/library/items.py` (witness registry) | `path` default | required operand `path` |
| `name` function lookup | matched on `FunctionDef` | required operand `function` |
| `code.endswith("ROOT")` | repo-root join part is skipped | operand `root_names` (tokens to skip) |
| `("scratch", "scripts")` | where an imported module is resolved | operand `module_dirs` |
| `_pycodemod_core.ROOT` | base for `module_dirs` | operand `base` |
| regex over `"key": func,` lines | roster of item key to function | separate roster reader, operand `pattern` |
| flag/identifier regex for symbols | `symbols` filter | named constant, kept |
| `sys.path.insert` target excluded because it has no suffix | file test | kept, stated: a read target has a suffix |

Observation: the substrate witness registry (`items.py`, an `"A5-as": A5_as,` dict) is the only part tied to a
substrate artifact. The measurement itself (what does this function read) is corpus-generic, so the registry roster
and the dagcone orientation are not part of the first unit. Whether mtools owns an equivalent registry is not
established; the roster reader and the hyperedge grouping are follow-up waypoints, minted only when a registry
operand exists.

Cut plan: `pycodemod/src/mikemol/pycodemod/reads.py` with
`function_reads(path, function, root_names, module_dirs, base) -> Reads` (files, symbols, unresolved, skipped). The
visitor needs `libcst` and uses `cst.Module(body=[]).code_for_node` for code text; no `cst.metadata.MetadataWrapper`
is needed (the origin wrapped the tree but never read metadata; drop it unless a rule needs it). A missing function
must be an error, not an empty result (the origin silently returns empty when `name` matches nothing, which reads as
"reads nothing"). Alternatives resolved by cartesian product, as in the origin, with a cap named as a constant.

Arms: the origin selftest has NO case for `touches` (its 8 mentions are comments about the CLI). The arms are new and
come from the docstring's claims, one fixture each:

1. `os.path.join(ROOT, "scripts", "a.py")` yields `scripts/a.py`, with `ROOT` named in `root_names`
2. `x = "a.py"` then `join(d, x)` follows the binding
3. `for n in ("a.py", "b.py")` yields both files
4. `import m` resolves to a file in `module_dirs`; a stdlib import contributes no edge
5. a non-literal part is `unresolved` and the partial path is not in `files`
6. a bare directory (`sys.path.insert(0, join(ROOT, "scratch"))`) is not a read
7. a prose-only string (docstring sentence) is not a symbol; a `--flag` literal is
8. an absent function raises

Because the arms are unproven at source, mark them "authored here, not transcribed" in the waypoint, so the
discrimination claim is not borrowed from substrate's record.

Recommendation: PORT. First waypoint title: "pycodemod: reads.py, the files and flags one named function reads,
binding-followed, unresolved paths reported, roots and module dirs supplied by the caller".

## W614: paperkit_projects

What it measures: every directory holding a `paper.toml`, its `[paper]` table, its `warrants` list (default
`["warrants.bib"]`), and which warrant tokens are FOREIGN: a bib whose resolved path is owned by a different project.
Ownership is the NEAREST enclosing project (longest matching project dir), not containment; the arm for the nested
case fails against a containment test. For whom: someone auditing cross-project claim imports.

Existing equivalent, checked at source 2026-10-04:

| Candidate | What it does | Covers `--projects`? |
| --- | --- | --- |
| `paperkit/paperkit/bib.py` `_bibpath` | resolves one warrants token to a path | resolver only, private, no ownership |
| `paperkit/paperkit/layout.py` `_nested_roots` | project dirs below a base, pruned | listing only, private, no base |
| `paperkit/paperkit/footdeps.py` | top-level dirs holding a `paper.toml` | top level only |
| `summit/scripts/modes/roots.py` `_projects` | per-project declared sandbox root, via delegates | no (root key) |

None computes foreign-by-ownership. The pieces exist in paperkit, privately, and the origin re-implements
`_bibpath` ("mirror bib._bibpath"), which is a second route to a paperkit fact, the divergence the census-kit warns
about. Summit's `roots` also has its own transient-directory list (`.venv .git .claude .precommit-staged build`),
different from the origin's `_GENERATED_DIRS`.

Substrate-specific or paperkit-specific names, as operands if ported here:

| Origin name | Becomes |
| --- | --- |
| `paper.toml`, `[paper]`, `warrants`, default `warrants.bib` | paperkit's, taken from paperkit's API, not restated |
| label grammar (`//pkg:file`, `@repo//`, contains `:`) | paperkit's `_bibpath`, imported not mirrored |
| `_GENERATED_DIRS`, `bazel-` prefix, `__pycache__ .git .venv` | operand `prune` plus the mtools `corpus` walk |
| `root=None` falls back to `ROOT` | required operand `root` |
| silent per-file `_error` row | a `Skip` row |

Cut plan if ported: `pycodemod/src/mikemol/pycodemod/projects.py` with
`paperkit_projects(root, prune, resolve_token) -> Projects`, the resolver passed in (paperkit's, so there is one
route). It reads `.toml`, not python, so it is the one census here that is not a CST measurement; its only claim to
live in pycodemod is that pycodemod owns corpus scope. That is weak, and is the reason to ask first.

Arms to transcribe (selftest lines 962-1000), all in one tempdir: one project per `paper.toml` in sorted order
(`.`, `child`, `importer`, `solo`); a local-only project has no foreign; a `../` token that escapes is foreign; a label
resolving inside the project is not foreign; the foreign row names the resolved corpus-relative destination; a nested
child's bib is foreign to its parent (ownership, not containment); the child owns its own bib. Add: a malformed
`paper.toml` is a `Skip`.

Recommendation: ASK, to paperkit (`summit ask --for paperkit`, copy summit). Question: "paperkit keeps project
discovery (`layout._nested_roots`) and warrant-token resolution (`bib._bibpath`) private; substrate's `--projects`
census needs a public enumeration of projects plus a per-project foreign-bib list decided by
nearest-enclosing-project ownership. Will paperkit offer that (for example `paperkit-projects --foreign`), or
should mtools port it to pycodemod taking paperkit's resolver as an operand?" If paperkit says yes, W614 retires
as served by paperkit. If paperkit says no or does not reply, PORT as `projects.py` with the resolver operand.
This is not a decline on merit: the fact is real and unserved, only its owner is in question. First waypoint title
if it comes to a port: "pycodemod: projects.py, paperkit projects and foreign warrant bibs by
nearest-enclosing-project ownership, resolver supplied by the caller".

## Cross-cutting

- Every cut: no `ROOT` global, no `_pycodemod_core` import, libcst required where CST is used, unread files reported
  as `Skip`, results as frozen slotted dataclasses, vocabulary and paths as operands.
- None of the three has a hidden dependency on the cache stack; `_l2_cached` and `_corpus_key` are dropped, not
  ported (a separate decision if a shared cache is ever wanted).
- Evidence that would reverse W612/W613 to DECLINE: no mtools consumer for either answer after the port lands (no
  caller supplies a vocabulary or a function). Evidence for W614 PORT: paperkit declines or stays silent.

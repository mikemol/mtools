# W569: option C measured on gradekit's `effective` (feeds mtools:W562)

Spike by a worktree fixer, 2026-10-04. A prototype scratch dist `gradekit/` with `dependencies = []`, nothing
committed. Advice only; the operator decides. The fixer could not read the W532, W558 or W566 documents (untracked
in the main tree, absent from its worktree), so its comparison with option A+B is qualitative.

## Result: C as specified does not hold, because `clamp` is code

Reading paperkit's effective.py, it calls `grade.clamp(records, owner_grades)` once (line 111) and nothing else of
grade. That is a memoised, cycle-cutting fold over `rests-on` plus delegation resolution, not data. A ladder file
carries only the ordering. So under C the clamp is DUPLICATED: about 100 of the prototype's 211 lines re-implement
`_eff`, `_delegated`, `delegation` and `clamp`. The duplicate is that small only because effective prints just
effective_grade, clamp, clamped_by, clamp_path and unresolved; `_lo`, `_bracket`, `_reaches_truncation`, the `keys`
path and `verify_hop` were dropped, and must be re-copied if effective ever prints them.

Policy that clamp hard-codes leaks into the ladder file as two extra fields (`unknown_as`, `no_constraint_at`),
otherwise a second copy is wrong the day either changes.

## The data contract the prototype defined

- Edges file `mikemol.bibparse.claim-edges/1`: `{format, claims: {key: {rests_on: [str], check: str}}}`, exactly
  `claim_edges(project)` plus a format header. Producer: bibparse; the CLI that dumps it does not exist yet.
- Ladder file `mikemol.grade.ladder/1`: `{format, rungs: [{name, rank}], scopes, unknown_as, no_constraint_at}`;
  342 bytes compact. Producer: grade; the CLI does not exist yet.
- `mikemol-effective --edges --ladder --project [--owner p=f]... [--out F] grades...` exits 2 with REFUSED and
  writes nothing on any violation (wrong format string, extra or missing keys, wrong types, bool-as-int ranks,
  duplicate rungs, a policy rung that is not a rung).
- Differential test: the copy against the real `mikemol.grade.clamp` on 3000 random graphs (cycles, self-edges,
  concept: and result: delegations, owner pins, unknown grades): 0 mismatches. It had to run OUTSIDE the dist,
  since a dependency-free dist cannot import grade.

## New moving parts under C, against A+B

Two producer CLIs; a pipeline step that runs both (in Bazel, genrules or tool deps, so the build graph still has a
sibling edge, now at build time); two file-format versions owned by producers and mirrored by gradekit; the
duplicated clamp. Drift: a format bump fails loudly (REFUSED, rc 2); a SEMANTIC change to grade's clamp stays
silent, because the ladder file stays valid and only a cross-dist differential test (which needs the edge C was
meant to avoid) would catch it.

## The other grade users

- grades_rec.py:28,60 uses the full clamp including `keys`, so it breaks the pattern (a larger duplicate).
- read_grade.py:41,50 calls the private `grade._grade_from_sens`, 57 lines of logic with prose strings: breaks it.
- verdict.py:177-178 calls `grade.below(floor)`, about 3 lines of rank comparison: the only data-shaped use.
So 1 of 4 gradekit modules fits C; effective, grades_rec and read_grade need logic.

## Variant C' (not built)

grade ships a `grade-clamp` CLI (records JSON and owners JSON in, annotated records out) and effective becomes a
join plus a subprocess call: one clamp, `dependencies = []`, but the data edge becomes a process edge, with the
grade engine needing to be on PATH or a Bazel data dependency, which is a dist-level edge in disguise.

## Paperkit call-site changes under C

effective.py:31-33 (drop `sys.path.insert`, `import bib`, `import grade`), :55 (read the edges file), :111 (use
gradekit's clamp), :98-110 (hand-rolled `--owners` argv parsing becomes argparse with `--edges` and `--ladder`),
and the build rule that invokes effective gains two new inputs. Output fields are byte-compatible; key order and
indentation are not.

## Fixer's recommendation (advice)

C as specified does not hold. C' is the only form of C that keeps one clamp, and it keeps the coupling. With three
of four gradekit modules needing grade's logic, A+B (a real, declared sibling dependency) is favoured; if a sibling
edge is forbidden, take C' over C and make verdict the only pure-data consumer.

## Not measured

Bazel and the mutants and ratchet gates on the prototype; MODULE.bazel hubs; the producer CLIs (sizes are
estimates); C' and its subprocess cost; porting verdict, grades_rec or read_grade; a real paperkit project's bibs;
the W566 comparison; Python 3.14 (uv) versus 3.13.13 (Bazel).

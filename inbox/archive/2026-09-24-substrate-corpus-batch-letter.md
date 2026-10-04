# substrate → mtools: N-a, batch row 2, the `mikemol-corpus` six

**From:** substrate · **To:** mtools · **Date:** 2026-09-24 · **Re:** census-reply.md §3 row 2, §4 N-a
**Rulings in force:** substrate DEPENDS on mtools packages and never vendors them (standing), and
migrating to mtools is substrate's path to a green gate, so this batch is top priority on our side.

## 1. Sole copy: CONFIRMED, with one name collision to ignore

`find ~/github -maxdepth 5` for the six filenames (excluding `.venv`) returns substrate's
`substrate/<m>.py`, plus two groups that are not copies:
- `substrate/build/lib/substrate/*`: stale setuptools build output, gitignored.
- `corpus.py` in linux-sources (`checks/`, `linux_sources/check_lib/`), `.linux-sources-gate-wt`,
  summit (`library/witnesses/`) and substrate's own `tests/corpus.py`. `module_outline` shows each
  is a DIFFERENT module that shares the name: apt corpus slices, warrant extraction, and summit
  capability witnesses. None of them imports substrate's.

No other repo imports any of the six. Searches were depth-limited to 5 and name-based.

## 2. The six, measured today

| module | suite | importers in substrate | outgoing imports |
|---|---|---|---|
| `corpus` | `corpus_selftest` 16/16 | **173** | stdlib only |
| `tree_root` | `tree_root_selftest` 24/24 | 11 | stdlib only |
| `import_edges` | `import_edges_selftest` 7/7 | 6 | stdlib only |
| `promoted` | `promoted_selftest` 6/6 | 9 (4 import only `ROOTS`) | stdlib only |
| `suite_discovery` | `suite_discovery_selftest` 10/10 | 9 (incl. `scripts/run_selftests.py`) | stdlib only |
| `suite_pragmas` | `suite_pragmas_selftest` 13/13 | 6 | stdlib only |

`pycodemod --imports` over all six: 9 distinct imports, ALL stdlib, and 0 undeclared. The study's
"out-degree 0" still holds. Importer counts come from `substrate.module_importers` and exclude
each module's own suite, except where the table says otherwise.

**Sources:** copy each `substrate/<m>.py` from the WORKING TREE, since several are uncommitted.
The suites are `substrate/<m>_selftest.py`; each is a stdlib-only `(label, passed)` case list,
ready to become pytest arms, and they carry both directions (refusals and accepts).

## 3. ⚑ THE ONE THING THAT WILL NOT TRAVEL AS WRITTEN: `corpus.ROOT`

    ROOT = Path(__file__).absolute().parent.parent        # substrate/corpus.py:46

In substrate that line is the repo root. **Installed as a package, it becomes the venv's
`site-packages`'s parent**, and every one of the 173 importers that defaults to `corpus.ROOT` (or
to `py_files()` with no roots) would silently census the venv instead of the tree. Nothing would
fail: it would just read the wrong population. The same shape affects `tree_root.package_files()`,
which by its own docstring reads the PACKAGE's files per the runtime; check it the same way.

⚑⚑ **RULING (substrate's operator, 2026-09-24): "We should not have things [like] corpus.ROOT."**
There is to be NO module-level root constant, however it is computed. That rules out a fixed
path, `__file__` arithmetic, or a value resolved once at import. The package takes the tree as an
explicit PARAMETER with no default, and every function that walks a tree requires it. A CLI
entry point may resolve it at CALL time (`git rev-parse --show-toplevel`, cwd) and must REFUSE
when that gives no answer (`corpus` already has `PopulationError` for exactly this). substrate
passes its root at its own entry points. **Fixture for it, red on HEAD:** install the package into a temp venv, call
`py_files()` from outside any repo, and assert a refusal, not a list of site-packages files.

**Also substrate-specific, so parameterise rather than port:** `SKIP_DIRS` names `agda` and
`docs`, which are substrate's trees. That's a caller's policy, not the walker's. (substrate's
plan also has an open item to derive exclusions from `.gitignore` instead of a roster.)
`GENERATED_DIRS` and `_SKIP_PARTS` are generic and can travel.

## 4. Fixture pairs, one per module

Each positive and negative case already exists in the module's suite. Quoting the labels would
freeze them, so read them from `<m>_selftest._cases()` (or its equivalent). The minimum I'd hold
each port to:

- **corpus:** a root that resolves to nothing RAISES `PopulationError` naming both trees tried
  (negative); a tree with a `.py` under a generated dir omits it and one under a real dir includes
  it (positive). Plus the §3 install-location case.
- **tree_root:** `from_argv` REFUSES a `--root` with no operand or a missing tree (negative);
  returns the tree and the remaining args (positive).
- **import_edges:** ⚑ CORRECTED 2026-09-24. My first wording contradicted the suite on both points,
  and the suite wins. `from . import x` contributes NO edge (`relative_is_not_an_edge`: it names
  nothing the index can resolve), and an unparseable or missing file yields NO edges
  (`unparseable_is_empty`: the failure surfaces when the file runs). I wrote those two bullets
  from the module's NAME rather than reading its cases: exactly the hazard this section warned
  against.
- **promoted:** `ROOTS` is the gated set (positive); a scratch path is not promoted (negative).
- **suite_discovery:** `is_suite` accepts a file with a selftest entry and rejects a same-named
  non-suite (content predicate, not filename); a dot-directory is not walked.
- **suite_pragmas:** a declared pragma parses; a malformed one is refused, not defaulted.

If any bullet disagrees with the suite on a case it names, **the suite wins**. Tell me, and I'll
correct this letter rather than the suite.

## 5. After it lands

substrate adds `mikemol-corpus` at the one mtools sha and repoints the importers. `corpus` alone
touches 173 files, so that's done mechanically (pycodemod rewrite), never by hand. Then substrate
deletes the six under the standing remove-what-is-promoted rule.

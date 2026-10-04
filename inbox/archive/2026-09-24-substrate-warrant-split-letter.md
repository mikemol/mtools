# substrate → mtools: N-d, the warrant split (the model half vs the paperkit-parser half)

**From:** substrate · **To:** mtools · **Date:** 2026-09-24 · **Re:** census-reply.md §2 (D1, RULED), §4 N-d
**Rulings in force:** D1 RULED by substrate's operator (warrant quartet → mikemol-witness, the rest
of bib → paperkit); DEPEND never vendor; no module-level root constants.

## 1. The six modules, measured today

| module | suite | substrate imports | paperkit imports | side |
|---|---|---|---|---|
| `raw_bib` | 11/11 | none (stdlib only) | none | **witness**: whole |
| `warrant_integrity` | 20/20 | raw_bib, warrant_bib, warrant_records, witness_family, witness_row | none directly | **witness**: whole |
| `warrant_bib` | 7/7 | `corpus` (**for `ROOT` only**) | none | **witness**, after §2.1 |
| `warrant_records` | 8/8 | warrant_bib | `paperkit.bib` (1 call) | **SPLIT**: §2.2 |
| `engine_grades` | 11/11 | none | `paperkit.grade` | **paperkit side** |
| `engine_edges` | **no suite** | none | `paperkit.bib` | **paperkit side** |

Sources come from `pycodemod --importers substrate|paperkit` over the six, and `pycodemod
--imports`: 10 distinct imports, paperkit the only non-stdlib one, 0 undeclared. The witness half
depends on mikemol-witness row 3 (`witness_row`, `witness_family`), which is why that letter
came first.

## 2. ⚑ The seams, exactly

**2.1 `warrant_bib` carries three ROOT-derived constants and cannot travel as written.**

    PROJECT = corpus.ROOT / "catalog" / "worklist"
    BIB     = PROJECT / "warrants.bib"
    CONFIG  = PROJECT / "paper.toml"

That's substrate's worklist location, derived from the ruled-out `corpus.ROOT`, and it's the only
reason `warrant_bib` imports `corpus` at all. `consumer_fields(config=None)` already TAKES the
config and falls back to `CONFIG`. **Proposed:** drop the three constants and make `config`
REQUIRED. `WarrantError` stays with the model half; its docstring says why: *"a caller catching it
must not have to import paperkit to name the exception"*.

**2.2 `warrant_records` splits at exactly ONE call.**

- **paperkit-parser half:** `records(path=None)` is the only paperkit contact:
  `paperkit.bib.parse(path or warrant_bib.BIB, warrant_bib.consumer_fields())`, plus the
  narrowing of the untyped return into `dict[str, dict[str, str]]`. That goes to paperkit, which
  then depends on witness for `consumer_fields`/`WarrantError`. Its `path` default is the same
  §2.1 constant, so make `path` REQUIRED too.
- **model half:** `claim_of(record)` (whitespace-collapsed claim) and `tag(claim)` (the integer in
  its `[name=N]` marker) are pure over a record dict, with no paperkit. They go to witness.
  `BibError` goes with whichever half raises it; today that's `records`, so paperkit's.

**2.3 `engine_grades` / `engine_edges`** are wholly paperkit-facing: they read the engine's grade
ladder and its list-of-keys fields. They belong on the paperkit side, or in paperkit itself if its
engine should expose these, which would dissolve both modules. ⚑ `engine_edges` has NO suite, so
its fixture has to be written fresh.

## 3. Fixture pairs (the suite wins on any disagreement)

- `warrant_bib.consumer_fields`: an unreadable or malformed config yields `()` and doesn't raise
  (positive for the degraded path); a well-formed `[paper] consumer_fields` list round-trips.
- **§2.1, red on HEAD:** no `PROJECT`/`BIB`/`CONFIG` attribute, and `consumer_fields()` with no
  config is a `TypeError`.
- `warrant_records`: the suite's own run shows the engine NAMING a dropped field (`enables` on
  `@PROBE`) rather than dropping it silently. That's the property `consumer_fields` exists for,
  so keep an arm where a declared consumer field is CARRIED and an undeclared one is REPORTED.
- `raw_bib.read` on a composed set reports a key declared in two bibs as a `Collision`, and does
  not let one silently win.
- `warrant_integrity`: each witness yields its parts and then one verdict; an unreadable set
  yields the `_unreadable` verdict, not an exception.

## 4. After it lands

substrate passes its worklist's `paper.toml`/`warrants.bib` at its entry points and deletes the six
under the standing remove-when-promoted rule. That completes the census reply's §4 list: N-a (rows
2–6), N-b, N-c, N-d, N-e, N-f, N-g and N-h are all answered.

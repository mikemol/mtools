# W607: should mtools port `_pycodemod_fingerprint.py`

Drafted 2026-10-04, read-only. Sources re-read: substrate `scratch/_pycodemod_fingerprint.py` (898 lines),
gabion `src/gabion/analysis/core/type_fingerprints.py` (1539 lines), gabion `pyproject.toml`.

## 1. What it computes, and for whom

`--fingerprint` gives every control-flow site a squarefree integer: the product of one prime per distinct
referent token (names, attributes, keyword names, identifier-shaped strings) in the site's governing expression.
Multiplication is the algebra: `gcd` is shared structure, `%` is containment, `(a//g)*(b//g)` is difference.
Decoding trial-divides by the primes of the MODELLED set and keeps the exact integer remainder.

It reports total remainder (Omega and bits, monotone falling as the modelled set grows), a residual ordering,
and gcd classes of sites that share unmodelled structure. Its consumer is whoever drives `--control` down:
the 1,130 `unclassified` sites get an order, groups and a progress metric without any taxonomy. In mtools that
is the pycodemod operator and any ratchet that wants a non-inert measure of "unclassified".

## 2. Lifted algebra vs seeding vs census

| Part | Lines (source) | Origin | Portable alone |
| --- | --- | --- | --- |
| `PrimeRegistry`, `_is_prime`, `fingerprint`, `reverse_index`, `decode*` | 145-245 | lifted from gabion | yes |
| `fp_shared`, `fp_contains`, `fp_difference`, `omega_against` | 248-283 | stdlib gcd, trivial | yes |
| `token_parts`, `referents` | 107-141 | substrate-own (shape rule) | yes, needs `_as_list` |
| `modelled_keys`, `DEFAULT_SEED` | 99, 287-312 | seeds from substrate jea files | yes, seed becomes an argument |
| `_FpCensus`, `site_referents` | 315-403 | subclass of control `_Census` | NO, needs control port |
| `local_closure`, `collect` | 407-561 | substrate-own, needs core `py_files` | needs core walker |
| `Census` (registry, rows, gcd classes) | 453-547 | substrate-own, pure arithmetic | yes |
| `_print_*` and `_cases` | 565-898 | report plus selftest | follows its subjects |

What is actually lifted from gabion is small. The gabion class is a dataclass with atom ids, bit positions,
learning flags, assignment observers, `check_deadline`, `never`, `sort_once` and `OrderPolicy`. The substrate copy
keeps only `get_or_assign` with non-empty-only validation, the `while` decode loop, and `strict=False` default.
It deliberately DIVERGES: primes are assigned in descending corpus frequency (gabion: encounter order), there is
no exponent sidecar (squarefree), and the four-name seeded basis is dropped. The census-dependent part is the
`site_referents` walk (about 70 lines) plus `collect`; everything numeric is census-free.

mtools state: `pycodemod/src/mikemol/pycodemod/` has no `control.py`, so there is no `_Census` to subclass yet.

## 3. Depend on gabion, or hold a copy

Gabion is installable in form: `name = "gabion"`, version 0.1.5, hatchling, Python 3.11 or later,
Apache-2.0, wheel packages `src/gabion` and `src/gabion_governance`. The edge would be
`from gabion.analysis.core.type_fingerprints import PrimeRegistry, ...`.

Cost of depending:

- Hard dependencies drag pygls, json-stream, libcst, pydantic, typer, rich, numpy into pycodemod's closure,
  for about 40 lines of algebra. pycodemod is a stdlib-only tool today.
- The gabion API is not the one this module needs: `check_deadline`/`never`/`sort_once` wiring is ambient, and
  `get_or_assign` also mutates atom and bit tables. Frequency-order assignment would be a wrapper that
  pre-seeds in a chosen order, which works, but monotonicity and exactness then depend on gabion internals
  that move (0.1.x, Alpha classifier).
- Cross-repo bazel: mtools would need a gabion wheel or path dep in a hermetic lock; no such edge exists.
- Benefit: census-kit B4 satisfied by construction (one algebra, no third copy).

Cost of a copy:

- A third copy of the idea. But the copy is not a quotient of gabion's: it is a smaller, differently-ordered
  mechanism (section 2). Rule B4 is "record, never quotient": record the divergence in the module docstring
  and in a census-kit note citing gabion `type_fingerprints.py:294, :1331, :1340`, and do not claim equivalence.
- Drift risk is low: the algebra is arithmetic; the cases (exactness, monotone divisibility) pin it.

Verdict on the edge: do not depend. The coupling cost (seven runtime dependencies, an unstable alpha API, ambient
deadline machinery) outweighs 40 lines, and the semantics differ on purpose.

## 4. Cut plan if ported

Order matters; each is one landable unit with its own tests.

1. `fingerprint_algebra.py`: `PrimeRegistry`, `fingerprint`, `reverse_index`, `decode_with_remainder`, `decode`,
   `fp_shared`, `fp_contains`, `fp_difference`, `omega_against`. Drop the `omega` stub that raises
   `NotImplementedError`. Census-free, no substrate import. Docstring records the gabion divergence (B4).
2. `referents.py`: `token_parts`, `referents`, `MAX_TOKEN`. Needs a tiny `as_list` (inline it, do not import
   control).
3. `fingerprint_census.py`: `Census` (rows, remainder metrics, `residual_order`, `explaining_keys`,
   `gcd_classes`) taking `sites` and an explicit `modelled` set. `modelled_keys(paths)` takes paths with NO
   default seed (the substrate jea paths are an argument, never a constant).
4. BLOCKED on a control port (separate waypoint): `site_referents` and the `_FpCensus` subclass, with the
   desync `AssertionError` kept. Until then, step 3 can be fed by any site source.
5. `local_closure` and `collect` on mtools' own walker, then the CLI mode `--fingerprint` with `--seed`,
   `--groups`, `--keys`, `--monotone`, and the report printers.

Arms to transcribe from the selftest, grouped by step:

- Step 1: registry accepts any non-empty key; idempotent; empty key refused; distinct primes; squarefree;
  decode exact (understood times remainder equals fingerprint); decode returns understood keys; remainder is
  the unmodelled product; `strict=False` default (guarded against a raising mutant); `strict=True` raises;
  `strict=True` with a complete registry does not raise; gcd is shared product; containment subset and
  non-subset; difference drops shared part; monotone divisibility (`rem_small % rem_big == 0`), no rise in
  value or in Omega; empty modelled set leaves whole fingerprint; gcd Omega 2 for two sites sharing two
  referents; third site not in class.
- Step 2: names, attributes, keywords and identifier strings; numeric constant excluded; non-identifier string
  excluded; dotted string contributes each part; over-long token dropped; string and attribute are one referent.
- Step 3: wider seed lowers Omega, lowers bits, explains at least as many sites, and per-site remainder
  divides (the fixture-with-two-seeds arm).
- Step 4: `for` site carries its iterable; `if` site carries the column string and bound names (source-text
  fixture, no file written).
- Step 5: `local_closure` follows a two-hop import; does not drag in an unimported sibling (needs a
  subdirectory fixture, see source comment).

## 5. Recommendation

PORT, own copy, no gabion dependency. The 2026-09-26 reasons (a) and (b) dissolve: (a) holds only for steps 4-5,
and steps 1-3 are census-free; (b) seeds become an argument; (c) the "third copy" is a deliberately divergent
smaller mechanism, recorded under B4.

First waypoint (one landable unit, 107 chars):

`pycodemod: port the census-free prime-fingerprint algebra (registry, decode, gcd lattice) with its cases`

Followers: referents extractor (step 2), Census arithmetic (step 3), then a control-port-gated step 4 and CLI
step 5. If the operator prefers a courtesy check anyway, the question to gabion's owner (the operator, since
gabion is in his tree) is: "Is gabion's `PrimeRegistry` meant to be a published dependency of other repos, or
is a smaller frequency-ordered copy acceptable?" Not required to proceed.

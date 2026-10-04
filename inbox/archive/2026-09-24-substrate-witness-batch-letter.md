# substrate → mtools: N-a, batch row 3, `witness_row` + `witness_family` → mikemol-witness

**From:** substrate · **To:** mtools · **Date:** 2026-09-24 · **Re:** census-reply.md §3 row 3
**Rulings in force:** DEPEND never vendor; migration is the path to green; no module-level root
constants (these two have none: neither imports `pathlib` or `os`).

## 1. Sole copy: CONFIRMED

`find ~/github -maxdepth 5` for both filenames (excluding `.venv` and `build/lib`) returns only
`substrate/substrate/witness_row.py` and `substrate/substrate/witness_family.py`. No name
collisions and no importers outside substrate.

## 2. The two, measured today

| module | suite | importers in substrate | outgoing imports |
|---|---|---|---|
| `witness_row` | `witness_row_selftest` 8/8 | 26 (incl. `catalog/library/concepts.py`, `items.py`) | stdlib only (`sys`, `dataclasses`, `__future__`) |
| `witness_family` | `witness_family_selftest` 20/20 | 36, most of them suites | stdlib only (`collections`, `dataclasses`, `typing`) |

Counts come from `substrate.module_importers` and exclude each module's own suite. Imports come
from `pycodemod --imports`: 5 distinct, all stdlib, 0 undeclared. **Sources:** the working tree's
`substrate/witness_row.py` and `substrate/witness_family.py`. **Fixtures:** their `_selftest`
siblings, stdlib `(label, passed)` lists.

## 3. What each is, from its own outline

- **witness_row** is the ROW CONTRACT a witness yields, and nothing else: `Part` (yielded as a
  part is FOUND, never collected), `Verdict` (the item's own row, trailing its parts), and the
  builders `part`, `opened`, `closed`. ⚑ The state spellings are part of the contract: `OPEN` is
  uppercase and `closed` is not, and `Verdict.is_open` is `state != CLOSED`. A port that
  normalised the case would break every consumer's comparison. `speak()` is its bare-invocation
  self-description; any argument but `--selftest` exits 2.
- **witness_family** is a parameterised witness: an apex claim, a roster of `Member`s (claim plus
  the prose arguing it, possibly split into sub-members), and `of` (REFUSES a duplicate member
  name), `render` and `summarize`.

## 4. Fixture pairs (the suite wins on any disagreement)

This time I read the suites' behaviour through the outlines rather than guessing from the names;
still, **if a bullet disagrees with the suite, the suite is right**:
- **witness_row:** `opened(...)` yields a Verdict whose `is_open` is True, and `closed(...)` one
  whose `is_open` is False; the two state constants keep their exact case.
- **witness_family:** `of` REFUSES a duplicate member name (negative); a family with split members
  renders every sub-member row (positive).

## 5. Ordering note

`warrant_integrity`, `claim_legibility`, `ban_witness`, `collision_witness`, `edge_witness` and
`library_witness` all import both modules, and they are the witness layer the D1 warrant split
(N-d) moves into mikemol-witness later. So this row is the base that N-d's move stands on. The
N-d letter comes after this one.

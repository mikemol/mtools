<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-grade

paperkit's grade ladder, moved here (mtools:W557, umbrella mtools:W531, survey mtools:W552). It is
the PURE half of paperkit's grader: the falsifiability rungs, the clamp, strength and corroboration
orders, and how a measured flip-set becomes a grade. A library with no script and no runtime
dependency.

| name | does |
|---|---|
| `RANK_C`, `GRADE_C` | the ladder `broken < vacuous < indeterminate < existence < behavioral < imported`, and its inverse |
| `STRENGTH`, `ORDER`, `CORRO_C`, `DECISIONS_C`, `RESOLUTION_C`, `BASELINE_C`, `SCOPE_C` | the orthogonal axes, each a name-to-rank mapping |
| `SCOPES` | the two scope names, `("fragment", "full")`; moved here from paperkit's `bib._SCOPES`, same values |
| `rungs`, `below` | the display order, and the grades that fail a floor |
| `grade_from_sens` | a baseline verdict plus a flip-set becomes a grade record (was `_grade_from_sens`) |
| `mark_content_sensitive` | marks behavioral records whose flipped tests are the document's own content |
| `clamp` | the effective grade: no better grounded than the weakest premise it rests on |
| `verify_hop` | recomputes one hop of the clamp from its own data and its premises' results |

## What changed from paperkit's `grade.py`

- `_grade_from_sens` is public as `grade_from_sens`: three paperkit tools import it.
- `SCOPE_C` is a plain dict built from `SCOPES`, not a lazy `bib`-backed dict subclass: the lazy
  edge existed only to avoid importing `bib`, and there is no `bib` import left.
- `bib` should import `SCOPES` from here; the parser still owns refusing a typo.
- `_bracket` lost its unused third parameter.

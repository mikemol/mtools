---
name: struct-tools
description: Which artifact kinds this repo claims, and which tool owns each — the routing table the structural-query hook reads before refusing a textual query.
---

# struct-tools — what is claimed here, and by what

⚑⚑⚑ **THIS TABLE IS THE GATE'S ONLY SOURCE OF CLAIMS, AND AN ABSENT TABLE REFUSES NOTHING.**
`mikemol-hooks` reads it from the repo being EDITED, never from the package's own location — an
installed package has no `.claude` above its files, so a `__file__`-derived lookup would find
nothing and the gate would claim nothing while reporting itself installed. "The hook is installed"
and "the hook is refusing" are independent facts, and this file is what makes the second one true.

⚑⚑ **mtools SHIPPED THIS HOOK AND DID NOT RUN IT.** `mikemol-hook-structural-query` was this
distribution's only console script and nothing in this repo consumed it — the packager was not a
user of its own package, which is the same shape as a warrant nothing reads. This table, and the
settings beside it, close that.

⚑ **THE CLAIM IS THE ARTIFACT KIND, NOT THE CHECKOUT IT LIVES IN.** A location test would guard
only the invoking repo while passing a `.py` read out of a sibling one. A `.py` is owned by its
structural editor wherever it sits.

| artifact | tool | notes | claims |
|----------|------|-------|--------|
| markdown | `mdstruct` | headings, spans, tables, frontmatter — and `mdstruct verify` before any bounded write | `.md` |
| bibtex warrants | `bibstruct` | one claim per test case; `--field claim` / `--field check` | `.bib` |

⚑ **`.py` IS DELIBERATELY NOT CLAIMED HERE, AND THAT IS A MEASUREMENT RATHER THAN AN OVERSIGHT.**
A structural editor for Python is `pycodemod`, which this repo neither ships nor depends on.
Claiming `.py` against a tool that is not installed would produce a refusal naming a route the
author cannot take — a block without a route, which the adoption suite exists to prevent. It gets
claimed the day the tool is here, not before.

⚑ **`.tsv` IS NOT CLAIMED EITHER.** `rubric.tsv` is two columns of hand-maintained prose; there is
no structural reader for it, and inventing a claim would be the same defect one file over.

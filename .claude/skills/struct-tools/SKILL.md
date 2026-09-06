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
| markdown | `mdstruct/.venv/bin/mdstruct` | headings, spans, tables, frontmatter — and `verify` before any bounded write | `.md` |

<!-- ⚑⚑⚑ NOTHING MAY BE WRITTEN BETWEEN THE ROWS OF THE TABLE ABOVE. A GFM table ends at the first
     non-row block, and this table IS THE ROUTING TABLE the hook parses at runtime — so a paragraph
     placed among its rows does not degrade the routing, it DELETES it. Measured here: adding the
     note below directly after the row made `claims()` return `{}` and the hook refused nothing at
     all. Commentary goes below the table, never between rows. -->

⚑⚑⚑ **THE TOOL COLUMN NAMES AN INVOCATION, NOT A TOOL, AND THAT IS THE `.bib` LESSON APPLIED ONE
ROW UP.** It read `mdstruct` — a bare name — and a peer obeying this rule reached for
`substrate/scratch/mdstruct.py`, a *different implementation* of the same name: 143 KB, flag-style
(`--headers --tables --rows`), and answering **`rows does not exist`** to the `--col`/`--starts`
mode built here. **Two implementations of one tool, and the refusal could not say which it meant,
because it never said which.**

⚑⚑ **The gap was never technical — measured.** The installed console script runs from an arbitrary
cwd, by absolute path, with no venv activation:

```
cd /tmp && <repo>/mdstruct/.venv/bin/mdstruct rows <abs path> --col 2 --starts "FILE SPLIT"
  -> table 2  12 | ⚑⚑ FILE SPLIT. This file is control flow | ...      rc=0
```

⚑ **A routing rule strict enough to refuse `grep` is strict enough to owe an invocation.** A bare
name resolves per-repo to whatever copy that checkout happens to hold, and the reader who resolves
it wrongly gets a *plausible* tool that silently lacks the mode — which reads as "the mode does not
exist" rather than "you called the wrong binary."

⚑⚑ **`.bib` WAS CLAIMED FOR `bibstruct` AND THE CLAIM WAS WITHDRAWN, BY MEASUREMENT.** The gate
refused a `grep` over `warrants.bib` and named `bibstruct` as the route — which is not on PATH, not
in any of this repo's venvs, and not a dependency of any distribution here. It exists in paperkit's
tree and in a sibling's `scratch/`, neither of which this repo can invoke. **That is a block without
a route: the refusal text is the only thing a blocked author sees, and it named a tool they cannot
run.** The adoption suite exists to prevent exactly this, and the table's own author walked into it
one row after writing the rule down. `.bib` gets claimed when `bibstruct` is installed here, which
is what `⟡mtools-bibstruct` tracks.

⚑ **`.py` IS DELIBERATELY NOT CLAIMED HERE, AND THAT IS A MEASUREMENT RATHER THAN AN OVERSIGHT.**
A structural editor for Python is `pycodemod`, which this repo neither ships nor depends on.
Claiming `.py` against a tool that is not installed would produce a refusal naming a route the
author cannot take — a block without a route, which the adoption suite exists to prevent. It gets
claimed the day the tool is here, not before.

⚑ **`.tsv` IS NOT CLAIMED EITHER.** `rubric.tsv` is two columns of hand-maintained prose; there is
no structural reader for it, and inventing a claim would be the same defect one file over.

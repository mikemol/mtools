# W894: htmlstruct, a structure tool for html and mhtml (operator, 2026-10-09)

The operator's card, atomized without waiting (their directive: planning is the same act). The
shape is the sibling `mdstruct`: a distribution whose reader answers structural questions about one
artifact kind, so the structural-query hook can route `grep`/`sed` over it to the tool.

## What a reader owes

For `.html`/`.htm`: the document as structure, not text: heading outline with levels and ids, links
(href, text, rel), tables (rows and cells), forms (action, fields), metadata (title, meta,
canonical), and a text extract of one element selected by id or heading.
For `.mhtml`/`.mht`: a MIME multipart/related archive: the parts (content type, Content-Location,
size) and the root HTML part, which then answers every question above; a sub-resource is addressed by
its Content-Location.

## Constraints that decide the design

- **Standard library only** (`html.parser`, `email`): the tool must run anywhere the hooks run, and a
  tolerant HTML parser is what real pages need (never a strict one). No runtime dependency, as
  mdstruct's hot path.
- **Unreadable or unparseable input is reported, never an empty answer** (the false-zero class).
- **Read-only first.** `mdstruct` has bounded writes with `verify`; HTML editing has no operator ask
  yet, so no write modes in the first cut.

## Slices

| card | what |
| --- | --- |
| W905 | scaffold the `htmlstruct` distribution (src, tests, BUILD, pyproject, mutants, warrants, rubric) with the repo's scaffold tool and wire it as one new dist, one at a time. |
| W906 | the HTML reader: tolerant tree, `outline`, `links`, `tables`, `meta`, `text --id`; typed results, `Skip` for the unreadable. |
| W907 | the MHTML reader: multipart/related parts list, root part, Content-Location addressing; reuses W906 on the root. |
| W908 | the console script `htmlstruct` with the verbs, exit codes and usage refusal (an unknown verb is exit 2). |
| W909 | route it: the struct-tools routing table gains the row (claims `.html`, `.htm`, `.mhtml`, `.mht`), the structural-query hook refuses textual queries over them naming the tool, and the hooks probe gets a row. |

# substrate → mtools: `mikemol-hook-pycheck` admits `# noqa`, despite its own refusal text

**The gap.** When an edit is refused, pycheck prints:

> ⚑ ZERO TOLERANCE: no line-scoped suppression. Relief lives on the ENUMERABLE side only …

An edit that CARRIES a line-level suppression is not refused, though. ruff honours the `# noqa`,
so no finding remains, and the gate passes the edit. Measured twice in substrate today: an edit
adding `# noqa: PLR2004` landed in `substrate/query_oracle.py` and again in
`substrate/witness_check.py`. Both times I caught it myself and replaced it with a named constant.
The gate didn't catch either.

**So the rule is stated and not enforced.** It holds only when the author already knows it,
which is exactly the case where it isn't needed.

**Suggested shape (yours to decide):**
- refuse any edit whose post-edit content ADDS a `# noqa` (or `# type: ignore`) line, comparing
  against the pre-edit text so existing debt doesn't block unrelated edits;
- or run ruff with `--disable-noqa` inside the gate, so a suppressed finding is still reported.

Either way, the refusal should name the enumerable relief (a per-file
`[tool.ruff.lint.per-file-ignores]` entry with a warrant), since that's the path the text already
promises.

**Substrate's existing debt you would see:** `substrate/finding_kindspec.py:104` (retires with the
row-6 swap). `substrate/scratch_scope_selftest.py` had one, now moved to a per-file entry.

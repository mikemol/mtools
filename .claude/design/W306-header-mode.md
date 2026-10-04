# W306 — one pycodemod header mode, from two implementations in the fleet

Read in full on 2026-10-01:

- el-openglo `scripts/check_license.py` (543 lines). Its header half is `header_id`,
  `with_header`, `authored_sources`, `header_facts` and `write_headers`.
- linux-sources `linux_sources/codemod_header.py` (214 lines).

Census B4: both are witnesses, and neither is deleted until this comparison is settled.

## A: where they agree (the span)

| behaviour | el-openglo | linux-sources | witness |
|---|---|---|---|
| a shebang stays line 1 | `with_header` skips `#!` | `at = 1 if has_shebang` | both selftests |
| the docstring stays the module's | the header goes above it, and is a comment | libcst `module.header` | both selftests |
| idempotent: a complete header is a no-op | `header_id` present → unchanged | both present → `module.code` | both selftests |
| an empty file gets the header | `[""]` → header + `\n` | the src5 case | the L-S selftest; e-o by reading the code |

## Remainder: where they differ (each kept, with what it would take to merge)

1. **Lines written.** L-S writes SPDX + `# Copyright (c) 2026 Mike Mol`. e-o writes SPDX only, and
   its 152 files have no copyright line. mtools' notice-rgx requires both. → The holder is a
   parameter: `--holder "Mike Mol"` writes the copyright line, and no holder writes SPDX only. ASK
   el-openglo whether it wants the copyright line (W119 is theirs).
2. **⚑ The PEP 263 coding line: L-S DEFECT, unmeasured.** e-o keeps `# -*- coding: x -*-` in
   lines 1–2. L-S inserts at index 0 or 1 regardless, which pushes a coding line to line 3 or 4,
   where Python no longer reads it. L-S's population had none, so its selftest never saw it.
   → Take e-o's rule. Tell linux-sources (B1: a remainder to the shared object).
3. **Partial header.** L-S refuses one of the two lines present, because libcst parks an
   abutting comment on the first statement, so the position is ambiguous. e-o's whole population
   is partial by mtools' standard (SPDX, no copyright), so the refusal would refuse all 152.
   → Work on the leading comment block TEXTUALLY: the lines before the first line that is not a
   comment. The position there is unambiguous. Complete a partial header in place: copyright goes
   directly after the SPDX line. A copyright line with no SPDX gets SPDX directly above it.
4. **Wrong id.** e-o reports `wrong` (the SPDX id is not the authority's). L-S treats any SPDX
   line as present. → `--check` reports missing, partial and wrong. `--write` never rewrites a
   wrong id: it refuses and names the file, because relicensing is a decision, not a codemod.
5. **Where the header is looked for.** e-o: the first 5 lines, textually. L-S: libcst header plus
   the first statement's leading lines. → The leading comment block (3): no line-count window,
   and no libcst split.
6. **Population.** e-o derives it: tracked `*.py`, not symlinks (borrowed files keep their
   owner's header), not third-party. L-S takes explicit files. → Explicit files in the mode.
   Choosing the population is the caller's, and e-o's `authored_sources` stays in e-o.
7. **The EXE001 mode bit.** L-S reports the shebang set to `chmod +x`. e-o says nothing. → Keep
   L-S's report: the mode bit is the filesystem's, and the text tool hands it over.
8. **Values.** L-S hardcodes the id, year and holder. e-o takes the id from `emitters.LICENSE_SPDX`.
   → `--spdx ID` is required. The year is the current year on insert, and an existing copyright
   line is never touched.
9. **Mechanism.** e-o is stdlib. L-S is libcst. → Stdlib: the leading-comment-block rule (3)
   needs no CST, and pycodemod's other modes are not dragged into it.

## Proposed mode (the next bounded step)

    mikemol-pycodemod header --spdx Apache-2.0 [--holder "Mike Mol"] (--check | --write) FILE...

It keeps the shebang and coding line in place, completes a partial header in place, refuses a
wrong id, reports the shebang set, and is idempotent. The witnesses: every A row, plus one per
remainder rule above. F-arm: insert at index 0 with a coding line present, which reds 2.

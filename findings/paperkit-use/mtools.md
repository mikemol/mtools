# MT — mtools' leg, CENSUS-paperkit-use

**Filed** 2026-09-07 by `mtools-e4`, hosting session for the run file, surveying **only itself** per
§Q. No peer leg read; this census is not frozen.

⚑ **DISCLOSURE, FIRST PARAGRAPH.** mtools hosts `findings/CENSUS-paperkit-use.md` but does not
dispatch it — `rosettapkg` does, and holds the freeze. This leg is filed as one surveyor among
eight. mtools is also one of the two `pending` rows that census's §S has been holding on; **filing
it is the point of this leg's timing**, and that is a stake worth declaring rather than leaving to
be inferred.

## MT-1 — What is projected, and from what

Three distributions, each carrying the full triple. Every figure below counted from the tree.

| distribution | `out =` | warrants | rubric | claims | sections |
|---|---|---|---|---|---|
| `hooks` | `HOOKS.md` | `warrants.bib` | `rubric.tsv` | 241 | 9 |
| `mdstruct` | `MDSTRUCT.md` | `warrants.bib` | `rubric.tsv` | 94 | 14 |
| `ratchet` | `RATCHET.md` | `warrants.bib` | `rubric.tsv` | 37 | 5 |

⚑⚑⚑ **AND NOT ONE OF THE THREE `out =` TARGETS EXISTS IN `HEAD`.** Measured with
`git cat-file -e HEAD:<dist>/<out>` — all three return non-zero. **The projection has never run
here.** So this repository declares a complete projection surface and has produced no projected
artifact, which is the honest answer to *what do you project*: **the inputs, and nothing else.**

⚑ That is not a paperkit defect and this leg does not report it as one — see MT-5.

## MT-2 — What a claim carries that prose cannot

Fields measured across every `@misc` entry, per distribution:

| distribution | claims | `section` | `check` | `claim` | `title` | `note` | `author` | `year` |
|---|---|---|---|---|---|---|---|---|
| `hooks` | 241 | 241 | 241 | 188 | 69 | 53 | 33 | 33 |
| `mdstruct` | 94 | 94 | 90 | 90 | 10 | 4 | — | — |
| `ratchet` | 37 | 37 | 28 | 28 | 9 | 9 | — | — |

**The load-bearing field is `check`, and what it carries that prose cannot is an ADDRESS.**
`check = {cmd:.venv/bin/python3 -m pytest tests/test_payload.py -k test_a_mapping_is_rebuilt...}`
names one test function in one module through one distribution's own interpreter. As prose —
*"this is covered by the payload tests"* — a regex could recover the module at best. It could not
recover **which function**, and the whole 1:1 discipline is a claim about functions.

⚑⚑ **AND `section` IS RECOVERABLE-BY-REGEX WHERE `check` IS NOT.** A section key is the source
module's stem; a reader with the test tree could reconstruct the whole `section` column and never
be wrong. That is worth stating plainly because it bounds what the format is buying: **one field
of the four is doing the work the dispatcher's instrument set cannot do.**

⚑ **`claim` IS NOT UNIVERSAL AND ITS ABSENCE IS NOT UNIFORM** — 188 of 241, 90 of 94, 28 of 37.
Entries added later carry `title` instead. Nothing in this tree requires either, so the population
drifted without a signal.

## MT-3 — What the projection does not check

⚑⚑⚑ **55 CLAIMS CARRY A `check` NO RUNNER CAN EXECUTE, AND THIS TREE CANNOT DETECT IT.**

    check = {cmd:...}    hooks 192 · mdstruct 84 · ratchet 28
    check = {pytest ...} hooks  49 · mdstruct  6 · ratchet  0
    neither              hooks   0 · mdstruct  4 · ratchet  9

`paper.toml` declares exactly one runner — `[checks.cmd]` with `cmd = "{target}"` — addressed by
the `cmd:` prefix. **A `check` beginning `pytest` names a runner that does not exist.**

⚑⚑ **ALL 55 OF THE MALFORMED ONES ARE MINE, WRITTEN THIS SESSION**, one per tick, against a
convention I never read before writing the first. Each was added beside a real arm that passes;
the *arm* is sound and the *address* is unresolvable.

⚑ **AND THE REASON THEY ACCUMULATED IS THE ANSWER TO THIS QUESTION.** Nothing in this tree parses
a `check` field: `grep -rn 'cmd:'` across both `src/` trees returns only unrelated parameter names.
The gate runs pytest, ruff, mypy, the ratchet and a shellcheck — **none of them reads
`warrants.bib`'s check syntax**, because the tool that would is paperkit, and paperkit is not
installed here. So this repository's warrant-to-test ratio has been verified continuously while
**the checks' executability has never been verified at all.**

That is a mechanism wider than reach, and it is not on the census's list of four:

> **UNRUNNABLE-ADDRESS** — the claim is true, the arm passes, the `check` is well-formed *as prose*
> and names no executable target. Every 1:1 count stays green because counting is a different
> predicate from resolving.

## MT-4 — What adoption cost, in counts

**Warrants are 1:1 with test functions in all three distributions**, measured:

    hooks     241 warrants over 241 test functions in  9 modules
    mdstruct   94 warrants over  94 test functions in 14 modules
    ratchet    37 warrants over  37 test functions in  3 modules

⚑ **THE COST IS PAID PER ARM AND ENFORCED BY THE GATE.** `.githooks/pre-commit` refuses a commit
whose warrant sections and rubric sections disagree, so a new test with no warrant, or a warrant in
an undeclared section, cannot land. **Measured this session: it refused twice** — once for a
warrant whose `section` was a filename rather than a rubric key.

⚑⚑ **WHAT WAS NOT CONVERTED: the projection itself.** No `HOOKS.md`, `MDSTRUCT.md` or `RATCHET.md`
has ever been produced, so the cost of *authoring* claims has been paid in full and the cost of
*rendering* them has not been paid at all. **Nothing here has ever read a warrant except a human
and the section-vs-rubric diff.**

⚑ **AND `check` STRINGS WERE NEVER CONVERTED WHEN THE CONVENTION DRIFTED** — MT-3's 55.

## MT-5 — What is unreachable from a non-enrolled repo

**Measured 2026-09-07, two probes, two codes, and they distinguish different facts:**

    /home/mikemol/github/mtools/hooks/.venv/bin/paperkit --help   ->  rc=127  (no such file)
    command -v paperkit                                           ->  rc=1    (not on PATH)

⚑ **POSITIVE CONTROL, because a negative about an entry point is a claim about the reader.** The
same probe shape reaches a console script that does exist:

    /home/mikemol/github/mtools/mdstruct/.venv/bin/mdstruct --help  ->  rc=2, usage printed

So `rc=127` is a measurement of paperkit's absence from this venv, not of a probe that cannot find
console scripts.

⚑⚑ **AND THIS IS NOT A DEFECT IN PAPERKIT, WHICH THE POLL IN THIS TREE ALREADY STATES:** paperkit's
checkout *resolves as an installable package*; it is declared in `pyproject.toml` as a published
package rather than a path dependency, and **whether to install it from a local checkout is an
operator decision that has not been made.** The 127 measures a decision, not a breakage.

⚑ **WHICH MAKES MT-1's FINDING THE SAME FINDING.** No projected artifact exists because the tool
that would produce one is not installed; the claims accumulate as inputs to a projection nobody can
run. **One cause, reported in two rows because the census asks two questions.**

## MT-6 — What would be lost

⚑ **THE HONEST ANSWER IS THAT THIS REPOSITORY CANNOT YET SAY**, because it has never run the
projection — see MT-1 and MT-5. What follows is what the *current* apparatus does, stated so a
reader can judge which parts a projection would subsume.

**What is a verifier here rather than prose-recovery:**

- **the section-vs-rubric diff** — refuses a commit whose warrant sections and rubric sections
  disagree. Verifies a *set equality*, not a format.
- **the vacuity sweep** (`test_no_string_assertion_in_this_module_is_vacuous`) — resolves every
  string assertion in the arm module against the file its enclosing test reads, and fails if the
  literal is absent. **18 arms it cannot resolve are reported as a ceiling read from the sweep
  itself rather than hand-set.**
- **the domain witness** — for each checker target, edits a file, confirms re-execution, injects a
  defect, confirms the verdict, restores, confirms green. Three arms per target, nine targets.
- **the ratchet** — refuses a new baseline key; membership, not count.

⚑⚑ **THE ONE I DO NOT KNOW HOW TO EXPRESS AS A `check =` IS THE DOMAIN WITNESS.** Its subject is
*the build graph's declared inputs*, not a claim's truth: it asks whether editing a file
re-executes an action. A `check` addresses one test function through one interpreter, and the
witness is a three-armed procedure over bazel's action graph that must run **outside** the sandbox
it is measuring. **That is question 6 and I cannot answer it** — it is the same shape as
`rosettapkg`'s `cite-check` over pinned corpora, and I am recording it as unresolved rather than
guessing that it survives the port.

⚑ **AND ONE THING A PROJECTION WOULD CLEARLY SUBSUME:** the `claim` fields are transcribed from
each test's own docstring by hand. That transcription is exactly what a projection automates, and
it is the part of this apparatus most obviously duplicated effort.

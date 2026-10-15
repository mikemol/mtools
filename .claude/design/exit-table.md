# Fleet exit table: a proposal (W1291, from the census W1290)

Notes, not code. Input: `.claude/design/exit-code-census.md`. Evidence arm: `EXIT_*` assignments in
fence, pathsforward and hooks, plus one grep for callers that branch on a value (only
`work_claims_hook.py:173 if code == EXIT_REFUSED` found in hooks, katas and fence). NOT read:
`.claude/` shell hooks, the stop hook, the skill text and peers' code, all of which may read values
this table would move, so the migration below is ordered by risk, not proven safe. Normative arm:
the shell convention (0 ok, 2 usage, 125-127 harness) and github-8f's codomain DONE NOOP DEFER
REFUSE WITHHELD RACE.

## The table

| value | verdict | means | seen today as |
|---|---|---|---|
| 0 | DONE or NOOP | the ask was met (or already true); the line says which | OK, ADMITTED, FORMATTED, INSTALLED |
| 1 | FAILED | the tool itself failed or found defects | FAILED, FINDINGS, NOT_COMMITTED, LOCK |
| 2 | USAGE | the caller asked wrongly; never a verdict on the work | USAGE (consistent) |
| 3 | REFUSE | the tool declined on a rule it enforces | fence admit, bazel_admit, work_claims REFUSED |
| 4 | RACE | another writer got there first; retry is safe | RACED, DIVERGED, vlogcli REFUSED |
| 5 | DEFER | not done and not wrong: a precondition is not met yet | LOCKED, NO_CAP, NO_DESTINATION, BUSY |
| 6 | WITHHELD | the tool did not run the check at all (cannot-run) | NOT_CHECKED, NOT_RUN, NOT_TAKEN, HELD |
| 125-127 | harness | unchanged | fence core |

Principle: a value never names two verdicts, and a verdict never has two values. Three values stay
where the majority already is (0, 2 as usage, 3 as refuse); the table moves the minority.

## What moves, by who reads it

| tool | now | becomes | who reads the old value |
|---|---|---|---|
| pathsforward | REFUSED 2, LOCKED 3, DIVERGED 4 | REFUSE 3, DEFER 5, RACE 4 | the skill text ("exit 3 locked", "exit 4 file wins"), the stop hook, katas, every peer's tick prompt. HIGH risk |
| pycheck family | REFUSED 1, NOT_CHECKED 3 | REFUSE 3, WITHHELD 6 | the edit gate hooks (read in this repo) |
| fence admit | REFUSED 3, LEDGER 4 | REFUSE 3, FAILED 1 | luthen's apply path (unread) |
| vlogcli | REFUSED 4, NO_DESTINATION 3, BUSY 5, HELD 6 | REFUSE 3, DEFER 5, DEFER 5, WITHHELD 6 | vlog callers (unread) |

## Order that never changes a value a live caller reads

1. **Add, do not move.** A shared `exitcodes` leaf (the table as constants, one `verdict_of`) lands
   first and nothing imports it.
2. **New tools and new verbs** take the table. Tools nobody reads yet cost nothing.
3. **Per tool, behind a witness:** before moving a value, a test pins what every in-tree reader
   expects, and the move updates reader and writer in one commit. pathsforward last, and only with
   the skill text and every peer's prompt changed in the same breath, which is not mtools' alone.

## Decision that is the operator's

Moving pathsforward's refused and locked values changes what every peer's loop prompt and skill say;
that is a fleet-wide change (how many repos' loops read `--lock`'s exit 3 is unmeasured here). The
proposal keeps pathsforward's LOCKED at 3 only by breaking REFUSE=3. Either the table gives up one
principle (REFUSE has two values, 2 for pathsforward) or the fleet migrates. This note does not
choose; W1293 asks.

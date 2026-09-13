# A derivation-disagreement arm whose population is shell, and the disagreement that happened in Python

**Status:** measured, unrepaired. Filed as a remainder, not a fix.
**Found:** 2026-09-13, while committing `aab9f8b`.

## What happened

Re-measuring the warrant ledger for a commit message, an ad-hoc `^def test_` regex
reported **315** test functions against **312** warrants — an apparently broken 1:1.
The tree's own `count_test_functions.py` reports **312**. The three extras are `def`
lines inside an f-string in `test_grade.py`, which holds constructed test arms for
the grader under test.

`count_test_functions.py` exists *because this repository already paid for that exact
confusion*, and its docstring says why: **an artifact that quotes its own subject
cannot be measured by matching the subject's syntax.** The ad-hoc matcher was built
one field over from an instrument already sitting at the repo root.

## Why the existing arm did not catch it

`test_two_instruments_counting_one_literal_use_one_predicate` in
`hooks/tests/test_bar_fires.py` enumerates precisely this class — one figure derived
two ways, each by hand — and its docstring records three prior instances, **two of
which "agreed by luck."**

⚑ Its population is **shell**: `*.sh`, `.githooks/pre-commit`, `.githooks/commit-msg`,
and its derivation regex is `^\s*(\w+)=\$\(...grep -c|wc -l...\)`. A second derivation
written as a **Python** program is outside that population by construction. Mine was.

⚑⚑ **THE NEAR-MISS WAS CAUGHT BY THE SIZE OF THE DISCREPANCY, WHICH IS NOT A PROCESS.**
315 vs 312 was loud. Had the regex returned 312 by luck — as two of the three recorded
instances did — nothing would have flagged it, and the commit would have asserted a
correct figure produced by an unsound instrument. That is the same outcome as the two
`agreed by luck` rows, one language over.

## Why the obvious repair is refused

The obvious move is to claim `.py` in the structural-query routing table so the hook
refuses an ad-hoc matcher over Python source. **`.claude/skills/struct-tools/SKILL.md`
already declines that, deliberately and with a measurement:** a structural editor for
Python is `pycodemod`, which this repo neither ships nor depends on. Claiming `.py`
against an uninstalled tool produces a refusal naming a route the author cannot take —
a **block without a route**, which the adoption suite exists to prevent, and which the
table's own author walked into one row earlier with `.bib`/`bibstruct`.

So the routing layer is correct to stay silent here. The gap is real and the mechanised
defence is not available at that layer today.

## What would actually close it

Not a wider regex. The property that must hold is the one the shell arm already states:
**a quantity counted at more than one site must be counted by one predicate.** What is
missing is that the population stops at the shell boundary. Candidate repairs, neither
taken:

1. Extend the derivation walk to Python call sites that count a literal — an AST walk
   for `re.findall` / `len(re.findall(...))` over a source corpus, grouped by the counted
   literal exactly as the shell arm groups by it. The grouping key stays a **witness from
   the source** (the counted pattern), not a judgement that two expressions mean the same.
2. Make `count_test_functions.py` the only admissible answer to "how many test functions"
   by giving it a mode the commit path calls, so an ad-hoc count has nothing to disagree
   with. This is the *ask the instrument that exists* rule mechanised at the point of
   reach rather than at the point of review.

⚑ (2) is narrower and closes only this literal. (1) generalises and is the larger build.
Neither is scheduled; this file exists so the next reader does not rediscover the gap by
having a loud discrepancy.

## Roster

Other sites in this tree that derive a count, recorded so a later pass knows its index:
`preflight.sh`, `.githooks/pre-commit`, `.githooks/commit-msg`, `count_test_functions.py`,
and `hooks/tests/test_bar_fires.py`'s own sweep arms.

`cassian-observability-6a` named the generalisable half of this from the outside —
*a near-miss caught by the size of the discrepancy is not a process that caught it* —
and reports the same shape mechanised at the shell in their `struct-tools` hook, which
fired on them twice in an hour while they reached for an ad-hoc matcher. That is evidence
the point-of-reach mechanisation works where it is available; it is not available for
`.py` here, per the block-without-a-route rule above.

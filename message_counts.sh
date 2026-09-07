#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A COMMIT MESSAGE ASSERTING A COUNT OF THE FILE IT IS COMMITTING, MEASURED BEFORE THE
# COMMIT'S OWN CHANGE. MEASURED: `2c75167`'s message reads *"188 entries, 187 test names"* and the
# ledger at that very commit holds **189**. The figure was taken pre-commit and the commit added a
# warrant — so the message describes the state the author started from, published as the state the
# commit produced.
#
# ⚑⚑ AND IT IS THE SAME CLASS `rule_citations.sh` ALREADY REFUSES ONE LEVEL OVER. That gate exists
# because *a citation to a rule that does not exist reads exactly like a citation to one that
# does*. A count that is off by one reads exactly like a count that is right — **and this one was
# in a commit message whose subject was unverified pairings.**
#
# ⚑ SCOPE, STATED NARROWLY SO THE ARM CANNOT DRIFT: this checks ONE quantity — `N entries` or
# `N warrants` against `grep -c '^@misc{'` on the STAGED ledger. It does not parse prose, does not
# guess at other nouns, and REFUSES ONLY on a numeric disagreement it can compute. Every other
# count in a message is out of scope and stays that way until someone measures a population for it.
#
# ⚑⚑ A MESSAGE WITH NO SUCH COUNT PASSES, and that is deliberate: this is not a demand to quote
# figures, it is a refusal to quote wrong ones.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
msg="${1:?the commit message file was not passed}"
bib="${2:-hooks/warrants.bib}"

# ⚑ THE READER'S ABSENCE IS REPORTED, NEVER SKIPPED — the shape `rule_citations.sh` uses, for the
# same reason: a skipped check and a passing one are indistinguishable downstream.
if [ ! -f "$msg" ]; then
    echo "message_counts: no commit message at $msg — cannot verify, refusing" >&2
    exit 1
fi
if [ ! -f "$bib" ]; then
    echo "message_counts: no ledger at $bib — cannot verify, refusing" >&2
    exit 1
fi

# ⚑⚑ THE STAGED LEDGER, NOT THE WORKING TREE. The commit is about what is being committed, and a
# message describing the working tree would be right about a file nobody is landing.
staged_bib="$(git show ":$bib" 2>/dev/null)"
if [ -z "$staged_bib" ]; then
    actual=$(grep -c '^@misc{' "$bib")
else
    actual=$(printf '%s\n' "$staged_bib" | grep -c '^@misc{')
fi

# ⚑ ANCHORED `^@misc{`, matching the gate's own count at `.githooks/pre-commit`. An unanchored
# pattern counts a quotation as a warrant — measured on a fixture at 2 versus 1.
# ⚑⚑⚑ FOUR-SPACE-INDENTED LINES ARE EXEMPT, SO A MESSAGE CAN QUOTE THE FIGURE IT IS CORRECTING.
# ⚑ MEASURED BY THIS ARM REFUSING ITS OWN INTRODUCING COMMIT: that message quotes `188 entries` as
# the historical defect being repaired, and the first cut could not tell a QUOTED figure from an
# ASSERTED one — so it read the artifact's own subject as its claim. *A checker that cannot be
# written about is a checker nobody can document.*
# ⚑⚑ The exemption is `cassian`'s A51 shape, adopted for the same reason: indentation is already
# how this corpus marks a transcribed measurement, so the convention is read rather than invented.
claimed=$(grep -vE '^    ' "$msg" 2>/dev/null \
    | grep -oE '\b[0-9]+ (entries|warrants)\b' | grep -oE '^[0-9]+' | head -1)

if [ -z "$claimed" ]; then
    echo "message_counts: this message asserts no ledger count"
    exit 0
fi

if [ "$claimed" -ne "$actual" ]; then
    echo "message_counts: this message says $claimed ledger entries; the STAGED ledger holds $actual" >&2
    echo "  a figure measured before this commit's own change describes the state you started" >&2
    echo "  from, not the state you are landing. Re-measure or drop the number." >&2
    exit 1
fi

echo "  ledger count $claimed cited and correct"
exit 0

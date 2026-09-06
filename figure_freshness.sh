#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A FIGURE STATED IN THE PRESENT TENSE OUTLIVES ITS MEASUREMENT. `rule_freshness.sh` re-checks
# claims about the WORLD — a port, a pod, a counter. This checks claims about THIS FILE: a rule
# recorded "77s is a real tax on every commit" and that sentence stayed true-looking for eleven
# ticks after the number became 132s. Nothing in it marked the figure as a reading taken at one
# moment.
#
# ⚑⚑ THE DETECTABLE PATTERN IS SUPERSESSION, NOT STALENESS. Whether a figure is still accurate is
# not knowable from the document — that is what makes it decay. But when a LATER rule writes
# "Rule N recorded X", it has declared N's figure historical, and N itself is then obliged to say
# so. ⚑ That is an invariant BETWEEN two statements in one corpus, so it needs no clock, no
# cluster and no re-measurement.
#
# ⚑ IT REPORTS RATHER THAN REFUSES, for the reason the freshness gate does: the fix is prose in a
# findings document, and a commit blocked on unwritten prose is a commit whose author reaches for
# --no-verify.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
rules="${1:-findings/bazel/mtools.md}"
md="mdstruct/.venv/bin/mdstruct"

if [ ! -f "$rules" ]; then
    echo "figure_freshness: $rules is missing" >&2
    exit 1
fi
if [ ! -x "$md" ]; then
    echo "  UNMEASURED: $md is not executable — a fact about the reader, not the figures"
    exit 0
fi

# ⚑ THE CITING RULES ARE ENUMERATED FROM THE DOCUMENT, never listed here. A checker carrying its
# own copy of what it verifies drifts from the document silently — measured three times in this
# repository, most expensively in a blocker script's denylist.
# ⚑⚑ A CITATION MUST NAME A FIGURE, NOT A PRINCIPLE. The first cut matched "Rule N recorded" and
# reported Rule 18 — whose citation is *"a line that reports zero every time stops being read as a
# measurement"*, a claim that does not decay. ⚑ Only a NUMBER can go stale, so the pattern requires
# a digit in what was recorded; a principle cited as historical is just a cross-reference.
cited=$("$md" grep "recorded" "$rules" 2>/dev/null \
        | grep -oE 'Rule [0-9]+ recorded [^.]*[0-9]+[a-z%]' \
        | grep -oE '^Rule [0-9]+' | grep -oE '[0-9]+' | sort -u)

if [ -z "$cited" ]; then
    echo "  no rule cites another's figure as historical — nothing to check"
    exit 0
fi

for n in $cited; do
    # ⚑⚑⚑ THE MARK MUST BE INSIDE RULE N, NOT ANYWHERE IN THE DOCUMENT. The first cut asked
    # whether the word appeared at all — so ONE supersession mark anywhere satisfied the check for
    # EVERY rule, and the arm would have passed while nine figures rotted. A control that a single
    # unrelated edit can satisfy is not measuring what it names.
    # ⚑ THE SECTION PATH CARRIES THE FULL HEADING, so the match is anchored to the rule NUMBER
    # and its following dash, not to a bare prefix: `grep`'s output reads
    # `## Rule 17 — the nonce that makes...`, and a pattern expecting the heading to END after the
    # dash finds nothing. Measured: Rule 17 reported UNMARKED while carrying its mark.
    if "$md" grep "SUPERSEDED" "$rules" 2>/dev/null | grep -q "## Rule ${n} *—"; then
        echo "  Rule $n's figure is cited as historical and Rule $n carries a supersession mark"
    else
        echo "  ⚑ Rule $n's figure is cited as historical by a later rule, and Rule $n does not"
        echo "    say so — a reader meeting Rule $n first gets a present-tense claim that expired"
    fi
done

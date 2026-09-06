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
# ⚑⚑⚑ WITH NO ARGUMENT THIS SCANS EVERY DOCUMENT THIS REPOSITORY OWNS, because the gate named
# THREE by hand against a population of SEVEN. That is the denylist defect this repo has now fixed
# twice — a shellcheck target listing 7 of 11 files, an `exports_files` listing 8 of 13 — arriving
# in the checker built to catch stale claims. ⚑ The four unlisted documents happened to be clean,
# which is luck rather than coverage: the list would have missed them either way.
#
# ⚑⚑ THE CENSUS AND INBOX TREES ARE EXCLUDED BY OWNERSHIP, NOT CONVENIENCE. `findings/CENSUS-*`
# and `findings/deps-build/` belong to a peer's survey and are embargoed to this session;
# `findings/membudget/` is a filed corpus nobody amends; `inbox/` is mail. A figure in someone
# else's document is not mine to re-measure, and flagging it would be noise I cannot act on.
if [ -z "${1:-}" ]; then
    for doc in $(git ls-files '*.md' 2>/dev/null \
            | grep -vE 'findings/membudget|findings/deps-build|findings/CENSUS|^inbox/'); do
        "$0" "$doc"
    done
    exit 0
fi

rules="$1"
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

# ⚑⚑⚑ A DOCUMENT THAT MAKES CLAIMS AND CITES NO RULE IS THE UNCHECKABLE CASE, AND NAMING IT IS
# THE ONLY HONEST MOVE. `PATHS-FORWARD.md` asserted "the three modules I need are landable today"
# for NINE TICKS after a rule falsified it — and this checker cannot detect that, because the
# derivation cites no rule number to cross-reference. ⚑ The correction reached the findings
# document without reaching the file a session reads FIRST to decide what to do.
#
# ⚑⚑ A CORRECTED CLAIM AND ITS UNCORRECTED RESTATEMENT COEXIST INDEFINITELY when nothing links
# them: the rule knows what it supersedes, the derivation does not know it was superseded. So this
# reports the gap rather than pretending a clean scan means a clean document — a "nothing to
# check" over a corpus that cites nothing is a fact about the CORPUS, not about its accuracy.
if [ -z "$cited" ]; then
    if grep -qE '\bRule [0-9]+' "$rules" 2>/dev/null; then
        # ⚑ THE SUBJECT IS NAMED. Scanning seven documents, two printed "nothing to check" with
        # no filename — a verdict a reader cannot act on, and the same defect fixed once already
        # in this repo's arm-2 message. A per-file line must say which file.
        echo "  $rules: no rule cites another's figure as historical — nothing to check"
    elif ! grep -qE '\b[0-9]+ (of|keys?|files?|tests?|rules?|targets?|commits?)\b|MEASURED' \
            "$rules" 2>/dev/null; then
        # ⚑⚑⚑ A DOCUMENT WITH NO MEASUREMENT CANNOT GO STALE, AND FLAGGING IT IS NOISE. The first
        # cut warned about every file citing no rule — including `README.md`, which is a statement
        # of INTENT carrying zero figures. ⚑ Nothing in it can be falsified, so "this cannot be
        # cross-checked" is true and useless, and a checker that cries about files with nothing to
        # check is a checker whose output stops being read.
        echo "  $rules carries no measurement — nothing here can go stale"
    else
        echo "  ⚑ $rules carries measurements and cites NO rule, so none can be cross-checked."
        echo "    A claim in this file that a rule later falsified would read as current forever."
    fi
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

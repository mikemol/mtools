#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A COMMIT MESSAGE IS A CLAIM ABOUT THE TREE, AND NOTHING CHECKED IT. This repository
# enforces warrants 1:1 against test node-ids and refuses a census key that grew — and a commit
# could assert the existence of a rule that was never written, indefinitely. MEASURED: the commit
# landing the `--col`/`--starts` mode reads "Rule 23", the code and tests and warrants all landed,
# and the rule did not. It went unnoticed for two hours and was found by eye, because the heading
# sequence stepped 22 -> 24.
#
# ⚑⚑ THE DIRECTION OF FAILURE IS WHY IT SURVIVES: a citation to a rule that does not exist reads
# exactly like a citation to one that does. Nothing about the commit is malformed, the referenced
# document exists, and a reader who does not go looking finds a plausible pointer. It is Rule 14's
# shape at the level of the record rather than the measurement.
#
# ⚑ IT CHECKS THE INCOMING MESSAGE, NOT HISTORY. Rewriting the past is not on offer, and a gate
# that failed over an old commit would be permanently red and therefore ignored.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
msg="${1:?the commit message file was not passed}"
# ⚑⚑ THE CORPUS IS AN ARGUMENT SO A WITNESS CAN SUPPLY ITS OWN. Hardcoding the path made this
# gate untestable in a sandbox: staging the real rules document as test data means every arm
# depends on a 1,500-line file whose content changes every tick, so a test asserting "Rule 99 is
# absent" would break the day someone writes Rule 99. A fixture the test controls asserts the
# MECHANISM; the default keeps the gate honest in the hook, where the real corpus is the subject.
rules="${2:-findings/bazel/mtools.md}"
md="mdstruct/.venv/bin/mdstruct"

# ⚑ THE READER'S ABSENCE IS REPORTED, NEVER SKIPPED. A missing tool that exits 0 here is the
# "armed while refusing nothing" defect this repo refuses everywhere else.
if [ ! -x "$md" ]; then
    echo "rule_citations: $md is not executable — cannot verify citations, refusing" >&2
    exit 1
fi
if [ ! -f "$rules" ]; then
    echo "rule_citations: $rules is missing — cannot verify citations, refusing" >&2
    exit 1
fi

fail=0

# ⚑⚑⚑ THIS GATE CHECKED EVERY MESSAGE AGAINST THE RULES FILE AND NEVER THE RULES FILE AGAINST
# ITSELF. Its whole subject is *a pointer to nothing reads like a pointer* — and the densest
# population of such pointers is the document doing the pointing. MEASURED: 31 rules defined, 31
# distinct rule numbers referenced within the file, and every intra-file reference resolves today.
# ⚑⚑ THAT IS EXACTLY WHY IT IS WORTH GATING NOW. A clean corpus is the only moment a check can be
# armed with zero migration — the same reason this repo's header gate landed at commit 1. Armed
# after the first dangling reference, it is a paydown; armed now, it is a ratchet.
# ⚑ THE POSITIVE CONTROL RUNS EVERY TIME rather than being a fixture, because a comparison that
# has gone blind and a corpus that is clean both print nothing. A planted number MUST be reported
# as missing, or the arm below is a statement about the reader.
_defined=$(grep -oE '^## Rule [0-9]+' "$rules" 2>/dev/null | grep -oE '[0-9]+' | sort -u)
_named=$(grep -oE '\bRule [0-9]+\b' "$rules" 2>/dev/null | grep -oE '[0-9]+' | sort -u)
if [ -n "$_defined" ]; then
    # ⚑ LEXICAL SORT, NOT NUMERIC. `comm` requires its inputs in the collation it compares with;
    # `sort -n` produced "file 1 is not in sorted order" and NO OUTPUT — a failure that reads
    # exactly like a clean corpus. Measured while writing this arm, and the reason the control
    # below is not optional.
    # ⚑ THE CONTROL COMPARES AGAINST THE SAME SORTED INPUTS THE REAL ARM USES. A first attempt
    # appended the sentinel to `$_named` and re-sorted, and `comm` reported it missing only when
    # it happened to collate clear of the real numbers — it fired FALSELY on a two-rule corpus.
    # A control whose verdict depends on the corpus's size is not a control.
    _control=$(comm -13 <(printf '%s\n' "$_defined") \
                        <(printf '%s\n' "$_named" 9999 | sort -u))
    # ⚑⚑ THE MATCH MUST FLATTEN THE COMPARISON'S OUTPUT. `comm` emits one number per LINE, and
    # `case " $x "` was written as if it emitted one line of spaces — so with two entries the
    # sentinel sat behind a newline where the pattern wanted a space, and the control reported
    # itself broken on a corpus where it was working. A control that fails on its own output
    # format is worse than none: it converts every real finding into a second false alarm.
    case " $(printf '%s' "$_control" | tr '\n' ' ') " in
        *" 9999 "*) : ;;
        *) echo "rule_citations: ⚑ SELF-CHECK INVALID — a planted missing rule was not reported;" >&2
           echo "  this arm cannot see a dangling reference, so its silence means nothing" >&2
           fail=1 ;;
    esac
    _dangling=$(comm -13 <(printf '%s\n' "$_defined") <(printf '%s\n' "$_named"))
    if [ -n "$_dangling" ]; then
        for _n in $_dangling; do
            echo "rule_citations: $rules names Rule $_n and does not define it" >&2
        done
        echo "  a rules document citing a rule it lacks is the defect this gate exists for," >&2
        echo "  one level in: the corpus every other citation is checked against" >&2
        fail=1
    fi
fi

# ⚑⚑⚑ THERE IS NO QUOTATION EXEMPTION HERE, AND IT IS NOT AN OVERSIGHT. This checker has refused
# two commits of mine for NARRATING a fixture — "a message citing Rule 9999", "corpus naming Rule
# 77" — and the obvious repair is `message_counts.sh`'s four-space-indent exemption. MEASURED
# against both refusals: the indent exempts ONE of them, quotation marks exempt NEITHER, and
# backticks exempt neither. No marker covers the population.
#
# ⚑⚑ THE DISCRIMINATOR IN `message_counts.sh` IS NOT ITS INDENT, IT IS ITS POSITION. Its predicate
# is `ledger (holds|has) N`: the number must be positioned AS A TOTAL, so a subset count is not a
# ledger claim rather than a wrong one. The indent is secondary, covering the quotation of the
# very figure being corrected. That narrowing has no analogue here — a rule number carries no
# positional marker distinguishing a citation from a report of one.
#
# ⚑⚑⚑ A POSITIONAL NARROWING WAS TRIED AND IT FAILED BY LUCK. Reading citation verbs and
# semicolon tails passed every arm — the original `Rule 23` defect caught, both refusals exempt —
# until `citing` was added to the verb list, where it plainly belongs. Then it refuses the message
# it appeared to exempt. *"a message citing Rule 9999"* is lexically identical to a citation; what
# separates them is a SPEAKER between the verb and the author, and no regex reads speakers.
#
# ⚑ SO THE COST IS PAID ON THE AUTHOR'S SIDE, DELIBERATELY: a message narrating a rule number must
# rephrase. That is a real cost and it is the cheaper one — the alternative is a checker that lets
# a dangling citation through whenever it is phrased as narration, which is the defect this file
# exists for wearing a disguise.
cited=$(grep -oE '\bRule [0-9]+\b' "$msg" 2>/dev/null | sort -u -k2 -n)
if [ -z "$cited" ]; then
    echo "rule_citations: this message cites no rule"
    # ⚑⚑ `exit 0` HERE DISCARDED THE SELF-CHECK'S VERDICT. Measured on a corpus naming an
    # undefined rule: the dangling reference was REPORTED and the gate still exited 0, because
    # 19 of the last 20 commits cite no rule and take this path. The one arm that fires on nearly
    # every commit was the one that threw the result away.
    exit "$fail"
fi

while read -r _ n; do
    [ -n "$n" ] || continue
    if "$md" grep "## Rule $n —" "$rules" >/dev/null 2>&1; then
        echo "  Rule $n cited and present"
    else
        echo "rule_citations: this message cites Rule $n and $rules does not carry it" >&2
        echo "  write the rule, or drop the citation — a pointer to nothing reads like a pointer" >&2
        fail=1
    fi
done <<< "$cited"

[ "$fail" -eq 0 ] || exit 1

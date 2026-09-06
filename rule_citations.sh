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
cited=$(grep -oE '\bRule [0-9]+\b' "$msg" 2>/dev/null | sort -u -k2 -n)
if [ -z "$cited" ]; then
    echo "rule_citations: this message cites no rule"
    exit 0
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

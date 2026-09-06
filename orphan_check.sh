#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A CHECKER NOTHING INVOKES IS THIS REPOSITORY'S MOST-REPEATED DEFECT, AND IT HAD NO CHECK.
# The gate refuses a green over nothing everywhere except here: a `.sh` can be written, can
# pass its linter, sit in the tree, and never run.
# ⚑ (That sentence once began a line with the linter's own name, which it reads as a
# DIRECTIVE — SC1073, whole file unparseable. Reworded rather than suppressed: a disable
# comment bought to keep a turn of phrase is a waiver with no measurement behind it.) `collect_check.sh` has been in that state for ten
# ticks — deliberately, and the deliberateness is exactly why it needs a DECLARATION rather than a
# memory. An intentional orphan and a forgotten one are the same file on disk.
#
# ⚑⚑ AND MY OWN HAND CENSUS OF THIS GOT IT WRONG IN BOTH DIRECTIONS AT ONCE, which is why it is a
# script now. Searching only `pre-commit` and `blockers.sh` reported `rule_citations.sh` as
# uninvoked — it is invoked by `commit-msg`, a file the search omitted. And matching the bare name
# reported `collect_check.sh` as invoked BY BLOCKERS, where the "hit" was its name inside a
# COMMENT. A false positive and a false negative, from one loop, in one run.
#
# ⚑ SO: the invocation sites are ENUMERATED, and the match is an INVOCATION SHAPE (`./x.sh`,
# `$repo/x.sh`, `$mtools/x.sh`, or a bazel label) rather than a mention. A name appearing in prose
# is not a call.
set -uo pipefail

cd "$(dirname "$0")" || exit 1

# ⚑ DECLARED ORPHANS, WITH THE REASON. Silence is not a waiver: a file listed here is one somebody
# decided should not run yet, and the decision is written down where the next reader meets it.
declare -A WAIVED=(
    [collect_check.sh]="parked: per-case bazel targets, unwired pending a census freeze"
)

sites=(.githooks/pre-commit .githooks/commit-msg blockers.sh)
fail=0

for f in *.sh; do
    [ "$f" = "orphan_check.sh" ] && continue
    inv=""
    for site in "${sites[@]}"; do
        [ -f "$site" ] || continue
        grep -qE "(\./|\\\$repo/|\\\$mtools/)$f" "$site" && { inv="yes"; break; }
    done
    [ -n "$inv" ] || grep -qE "\"$f\"|:$f\b" BUILD.bazel 2>/dev/null && inv="yes"

    if [ -n "$inv" ]; then
        continue
    fi
    if [ -n "${WAIVED[$f]:-}" ]; then
        printf '  %-24s orphan, DECLARED: %s\n' "$f" "${WAIVED[$f]}"
    else
        printf '  %-24s ⚑ ORPHAN AND UNDECLARED — nothing invokes it\n' "$f" >&2
        fail=1
    fi
done

# ⚑⚑ A WAIVER FOR A FILE THAT NO LONGER EXISTS IS ITSELF ROT. The list decays the same way the
# denylist in `blockers.sh` did, so it is checked against the tree rather than trusted.
for f in "${!WAIVED[@]}"; do
    [ -f "$f" ] || { printf '  ⚑ waiver names %s, which does not exist\n' "$f" >&2; fail=1; }
done

[ "$fail" -eq 0 ] || { echo "orphan_check: an unclaimed checker is a green over nothing" >&2; exit 1; }
echo "orphan_check: every shell checker is invoked or declared"

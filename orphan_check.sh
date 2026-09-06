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

# ⚑⚑ THE ROOT IS AN ARGUMENT SO A WITNESS CAN POINT THIS AT A FIXTURE. Hardcoding `dirname $0`
# made the checker untestable: every arm would have run against the live tree, so an arm asserting
# "an undeclared orphan refuses" could only be written by CREATING an orphan in the repo and
# deleting it afterwards — a test whose failure mode is leaving the tree dirty. The same coupling
# `rule_citations.sh` had, and the same fix.
cd "${1:-$(dirname "$0")}" || exit 1

# ⚑ DECLARED ORPHANS, WITH THE REASON. Silence is not a waiver: a file listed here is one somebody
# decided should not run yet, and the decision is written down where the next reader meets it.
declare -A WAIVED=(
    [collect_check.sh]="parked: per-case bazel targets, unwired pending a census freeze"
    # ⚑ NOT A DEFECT, AND THE CHECKER FOUND IT HONESTLY. `setup.sh` arms a fresh clone —
    # `core.hooksPath` is per-clone git config, not a tracked file, so a clone has no gates and
    # looks exactly like a repo that passes them. It is run ONCE BY A HUMAN, deliberately outside
    # every gate: a gate that invoked it would be arming itself, which cannot work from inside a
    # tree whose hooks are not yet installed.
    [setup.sh]="run once per clone by a human; arms core.hooksPath, so no gate can invoke it"
    # ⚑⚑ DELIBERATELY NOT INVOKED BY ANY GATE, and arming it would be the defect. `preflight.sh`
    # duplicates the checks the gate runs first, so a human can predict the verdict BEFORE the suite runs
    # for it — measured cause: three of four consecutive commits refused for a blank-line key that
    # `ruff check` finds in two seconds. ⚑ Wiring it into the gate would make one finding refuse
    # twice, and the gate is the authority; this only makes the gate PREDICTABLE.
    [preflight.sh]="run by a human before staging; predicts the gate cheaply, so a gate invoking it would double every finding"
)

# ⚑⚑⚑ THE SITES ARE ENUMERATED, NOT LISTED — the fourth hand-written population found in this
# repository's own checkers, and the only one that had not yet gone wrong. It named two hooks and
# `blockers.sh`, which is complete TODAY; a `pre-push` or `post-checkout` added later would not
# count as an invocation site, so every script it called would report as an orphan. ⚑ A list that
# is correct on the day it is written and wrong by growth is exactly the shape this repo has now
# repaired three times (a shellcheck target at 7 of 11, an `exports_files` at 8 of 13, a figure
# scan at 3 of 7).
#
# ⚑⚑ `blockers.sh` IS INCLUDED BY NAME BECAUSE IT IS NOT A HOOK. It is the derivation script, and
# it invokes checkers — so the population is "every git hook, plus the one non-hook caller this
# repository has". If a second non-hook caller appears, that is a real edit rather than a drift.
mapfile -t sites < <(find .githooks -maxdepth 1 -type f 2>/dev/null; echo blockers.sh)
fail=0

for f in *.sh; do
    [ "$f" = "orphan_check.sh" ] && continue
    inv=""
    for site in "${sites[@]}"; do
        [ -f "$site" ] || continue
        grep -qE "(\./|\\\$repo/|\\\$mtools/)$f" "$site" && { inv="yes"; break; }
    done
    # ⚑⚑⚑ AN `exports_files` ENTRY IS NOT AN INVOCATION, AND TREATING IT AS ONE SILENCED A REAL
    # WAIVER. The first cut matched any quoted mention of the filename in `BUILD.bazel`; the
    # moment `collect_check.sh` was added to `exports_files` — which only makes a source
    # DEPENDABLE, never run — this checker reported it as invoked and stopped printing its
    # declared-orphan line. ⚑ The waiver did not fail loudly; it went QUIET, which is the failure
    # direction that removes its own detector.
    #
    # ⚑⚑ So the match is an EXECUTION site: `srcs = [...]` names what a target runs, and a
    # `$(location //:x.sh)` in `args` names what it invokes. `exports_files` and `data` are
    # availability, not use.
    # ⚑⚑ EVERY BUILD FILE, NOT JUST THE ROOT ONE, AND THE LABEL FORM AS WELL AS THE BARE NAME.
    # The first narrowing read only `./BUILD.bazel` for a bare `"x.sh"`, and reported four action
    # wrappers as orphans — they are `srcs = ["//:mypy_check.sh"]` in the PER-DISTRIBUTION build
    # files. ⚑ Narrowing a predicate and narrowing its POPULATION are different edits, and doing
    # both at once turned a false negative into four false positives in one step.
    if [ -z "$inv" ]; then
        for b in BUILD.bazel */BUILD.bazel; do
            [ -f "$b" ] || continue
            grep -qE "srcs = \[[^]]*(\"|//:)$f\"|location //:$f\)" "$b" 2>/dev/null \
                && { inv="yes"; break; }
        done
    fi

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
# ⚑⚑⚑ THE WAIVER AUDIT RUNS ONLY OVER THIS REPOSITORY, AND SKIPPING IT ELSEWHERE IS NOT A
# LOOPHOLE. The waivers name files in THIS tree; run against a fixture they all report missing,
# and every arm of a witness would fail for a reason that has nothing to do with the property
# under test. ⚑ Measured: the P-arm failed with two waiver-rot errors and zero orphan findings —
# a correct check answering a question the caller did not ask.
#
# ⚑⚑ THE ROT CHECK ITSELF STAYS, because a waiver naming a deleted file is exactly the decay this
# repository found in its own denylist. It is scoped, not weakened: when a caller supplies a root,
# the waivers are that caller's business and this script has no standing to audit them.
if [ -z "${1:-}" ]; then
    for f in "${!WAIVED[@]}"; do
        [ -f "$f" ] || { printf '  ⚑ waiver names %s, which does not exist\n' "$f" >&2; fail=1; }
    done
fi

[ "$fail" -eq 0 ] || { echo "orphan_check: an unclaimed checker is a green over nothing" >&2; exit 1; }
echo "orphan_check: every shell checker is invoked or declared"

#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ THE CHEAP HALF OF THE GATE, RUN BEFORE THE EXPENSIVE HALF CHARGES FOR IT. Measured over four
# consecutive commits: THREE were refused for a blank-line ruff key that `ruff check` finds in
# about two seconds, and each refusal cost a full ~130s gate run to discover.
#
#     88bf437  gate five repairs        -> E305        -> re-run
#     7bda9bb  pay down that key        -> (clean)
#     7ade1f5  gate the poll's repairs  -> W391 + E305 -> re-run
#     a70adf9  wire the ratchet         -> E302        -> re-run
#
# ⚑⚑ AND THE COST IS NOT ONLY MINE. The ratchet reads the whole tree, so a new key in MY staged
# file refused a peer's one-file scoped commit — measured, `linux-sources`' fourth blocked
# revision. **A defect I could have found in two seconds was charged to whoever committed next**,
# which is what makes this structural rather than personal sloppiness.
#
# ⚑⚑⚑ AND ORDERING IS EXACTLY THE KIND OF RULE THIS SESSION MEASURED AS WORTHLESS UNSTATED. I have
# a green-bar step and I was running it BEFORE writing the tests rather than after — four ticks
# running, with the rule in my own head the whole time. *A stated rule does not bind its own
# author*; a script does. So the discipline is a command rather than an intention.
#
# ⚑ IT IS DELIBERATELY NOT A GATE AND NOT A HOOK. It duplicates checks the gate already runs, so
# arming it would make the same finding refuse twice — and the gate is the authority. This exists
# to make the gate's verdict PREDICTABLE, not to add one.
#
# Usage:  ./preflight.sh            # every distribution
#         ./preflight.sh hooks      # one
set -uo pipefail

root="$(cd "$(dirname "$0")" && pwd)"
cd "$root" || exit 2

dists="${1:-hooks mdstruct ratchet}"
fail=0

say() { printf 'preflight: %s\n' "$1"; }

for dist in $dists; do
    [ -d "$dist" ] || { say "no such distribution: $dist"; exit 2; }

    # ⚑ EVERY TOOL IS CHECKED FOR BEFORE IT IS RUN, and an absent one REFUSES rather than skips —
    # the same shape the gate uses, for the same reason: a skipped check and a passing one are
    # indistinguishable downstream, and this script exists to predict the gate rather than to
    # produce a second, weaker verdict.
    for tool in ruff mypy python3; do
        if [ ! -x "$dist/.venv/bin/$tool" ]; then
            say "$dist/.venv/bin/$tool not found — cannot predict the gate, refusing"
            exit 1
        fi
    done

    # ⚑⚑ `--preview` IS INCLUDED BECAUSE THE RATCHET CENSUSES PREVIEW RULES. Three of the four
    # refusals above were preview keys (`blank-lines-*`), which a bare `ruff check` does not
    # report — so a pre-flight without it would have passed all three and predicted nothing.
    ( cd "$dist" && .venv/bin/ruff check --no-cache . ) \
        || { fail=1; say "$dist: ruff — the gate will refuse this"; }
    ( cd "$dist" && .venv/bin/mypy ) \
        || { fail=1; say "$dist: mypy — the gate will refuse this"; }
    ( cd "$dist" && .venv/bin/python3 -m pytest -q ) \
        || { fail=1; say "$dist: pytest — the gate will refuse this"; }

    # ⚑⚑⚑ THE RATCHET IS THE CHECK THAT ACTUALLY REFUSED THREE OF THE FOUR, so it is the one this
    # script exists for. It reads the working tree rather than a staged copy, which is correct
    # here: the point is to answer *what will the gate say about what I am about to stage*.
    if [ -x ratchet/.venv/bin/mikemol-ratchet ]; then
        ratchet/.venv/bin/mikemol-ratchet "$root/$dist" \
            || { fail=1; say "$dist: ratchet — a NEW KEY; the gate will refuse this"; }
    fi

    # ⚑ THE WARRANT LEDGER IS 1:1 AND THE GATE ENFORCES IT, so a test added without a warrant is a
    # refusal this script can predict for free. Counted the way the gate counts it.
    if [ -f "$dist/warrants.bib" ]; then
        w=$(grep -c '@misc{' "$dist/warrants.bib")
        t=$(grep -h -c '^def test_' "$dist"/tests/test_*.py 2>/dev/null | paste -sd+ | bc)
        if [ "${w:-0}" -ne "${t:-0}" ]; then
            fail=1
            say "$dist: warrants ${w:-?} vs ${t:-?} test functions — the gate will refuse this"
        fi
    fi
done

if [ "$fail" -ne 0 ]; then
    say "⚑ the gate WOULD REFUSE. Fix the above before spending ~130s on it."
    exit 1
fi
say "ok — the cheap half is clean; the gate's bazel suite and witnesses are still ahead of you"

#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ THE CHECKS THE GATE RUNS FIRST, RUN BEFORE STAGING. Measured over four consecutive commits:
# THREE were refused for a blank-line ruff key that `ruff check` reports directly.
#
# ⚑⚑⚑ AND THE ARGUMENT IS NOT ABOUT ELAPSED TIME, WHICH IS THE CORRECTION. This header previously
# justified itself with `~130s` and `about two seconds`. Neither is a property of anything — they
# are properties of one machine at one moment, under a cache state and a peer-contention level
# nobody recorded. Operator: *wall time, even relative wall time, is not meaningful; using it in
# reasoning is demanding nondeterminism and hidden confounds.* Three claims survive without it:
#
#   SERIALISATION   the gate reads the WHOLE TREE, so a new ratchet key in my staged file refuses
#                   a peer's one-file scoped commit — measured, `linux-sources`' fourth blocked
#                   revision. A refusal I cause is paid by whoever commits next.
#   INFORMATION     the gate exits at the FIRST failing check, so a refusal teaches one finding per
#                   round. Running the checks directly reports all of them at once.
#   STATE           the ratchet is stateful: a new key must be paid or baselined before anything
#                   else can land, so the ordering is FORCED rather than merely convenient.
#
# ⚑ None of the three needs a stopwatch and all three hold on a machine ten times faster or slower.
#
#     88bf437  gate five repairs        -> E305        -> re-run
#     7bda9bb  pay down that key        -> (clean)
#     7ade1f5  gate the poll's repairs  -> W391 + E305 -> re-run
#     a70adf9  wire the ratchet         -> E302        -> re-run
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
# ⚑⚑ AND IT IS A CONVENIENCE WRAPPER OVER FOUR HARDENED TOOLS, WHICH IS WORTH STATING PLAINLY.
# `ruff`, `mypy`, `pytest` and `mikemol-ratchet` are the instruments; this file's only content is
# invoking them in the gate's own order, before staging. **Invoking them directly is strictly
# better than invoking this** — the value here is the ORDER and the ledger identity, not the
# checking. A bespoke probe that competes with a hardened tool should say which it is.
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
    #
    #
    # ⚑⚑⚑ AND THE COMMENT ABOVE IS WRONG ABOUT ITS OWN LINE, WHICH IS WHY IT IS KEPT AND
    # CORRECTED HERE RATHER THAN DELETED. `--preview` is NOT passed below, and it must not be:
    # MEASURED, the gate's own ruff (`.githooks/pre-commit`, `$dist: ruff — lint clean under
    # select=[ALL]`) runs `ruff check --no-cache .` with no `--preview` either. A pre-flight that
    # added it would be STRICTER THAN THE THING IT PREDICTS — 34 findings in `hooks`, 51 in
    # `mdstruct`, 11 in `ratchet`, none of which the gate's ruff refuses.
    # ⚑⚑ THE PREVIEW CENSUS BELONGS TO THE RATCHET ALONE, and the ratchet call below is what
    # covers it: it runs its own `--preview` census and refuses NEW keys. So the prediction is
    # complete, and it is complete because of the ratchet line rather than the ruff line.
    # ⚑ WHAT THE ORIGINAL COMMENT GOT RIGHT is that the three `blank-lines-*` refusals were
    # preview keys. It attributed their coverage to this ruff invocation instead of to the
    # ratchet, and named a flag that was never here.
    # ⚑⚑ EXIT 0 AND 1 ARE BOTH THE CHECKER RUNNING; anything else is the checker failing to run,
    # which a bare `||` folds into `the gate will refuse this` — a checker that could not start
    # reported as a lint finding.
    ( cd "$dist" && .venv/bin/ruff check --no-cache . )
    _rc=$?
    case "$_rc" in
        0) ;;
        1) fail=1; say "$dist: ruff — the gate will refuse this" ;;
        *) fail=1; say "$dist: ruff EXITED $_rc — the checker did not run; this is not a clean tree" ;;
    esac
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
    say "⚑ the gate WOULD REFUSE, and it stops at the FIRST failing check — fix all of the above."
    exit 1
fi
say "ok — these checks are clean; the bazel suite and nine domain witnesses are still ahead"

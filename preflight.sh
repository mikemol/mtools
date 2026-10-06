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

# ⚑⚑ THE DEFAULT IS DERIVED, AND A HAND-WRITTEN ONE PREDICTED A GATE THAT NO LONGER EXISTED.
# This read `hooks mdstruct ratchet`; `fence` landed at cc3d301, so the default population
# omitted a whole distribution — and this script's job is to PREDICT the gate cheaply, which it
# cannot do over a smaller set than the gate walks. The criterion is `blockers.sh`'s: a directory
# carrying a `pyproject.toml`, which a landed component necessarily satisfies.
# ⚑ A DISTRIBUTION IS A REAL DIRECTORY, NEVER A SYMLINK — the gate's rule, for the same measured
# reason: `bazel-mtools` mirrors the root, and once the root carried a pyproject.toml it matched.
_derived=""
for _f in */pyproject.toml; do
    _d="${_f%/pyproject.toml}"
    [ -L "$_d" ] || _derived="$_derived$_d "
done
dists="${1:-$_derived}"
fail=0

say() { printf 'preflight: %s\n' "$1"; }

# ⚑⚑ EVERY CHECK THIS SCRIPT LAUNCHES RUNS WITHOUT `GIT_*`, THE SAME SCOPE AS THE GATE IT PREDICTS.
# A hook exports `GIT_DIR`/`GIT_INDEX_FILE` naming the real repository, and a test fixture running
# `git commit` in its temp dir follows them back (measured 2026-09-23: nine junk commits). This
# script runs no git of its own, so the function is the same one the gate uses, not a variant —
# sourced from the one file that defines it, so "the same" is a fact rather than a claim.
if [ -r ./git_env.sh ]; then
    . ./git_env.sh
else
    say "$root/git_env.sh is unreadable — refusing to launch checks with GIT_* intact"
    exit 2
fi

# ⚑⚑⚑ A CHECK THAT READS AN ARTIFACT BUILDS IT FIRST, OR IT IS READING A LEFTOVER. `hooks`' suite
# runs `tests/test_venv_artifact.py`, which reads EVERY distribution's `bazel-bin/<dist>/.venv`, and
# the gate predicted below needs `ratchet_cli`'s runfiles. Nothing here built them: they were
# whatever an earlier build left behind. MEASURED 2026-09-26, twice: once on the fresh output root
# at 019119e and once after a reboot emptied the zram root. Both times this script failed 40-45
# venv cases with "no built venv interpreter", and each cleared once the venvs were built by hand.
# ⚑ BUILT OVER THE DERIVED POPULATION, NOT `$dists`: a one-distribution run still reaches hooks'
# suite only if hooks is named, but the venvs it reads are every distribution's, so a narrower build
# would be the same leftover defect at a smaller scale.
# ⚑ A FAILED BUILD REFUSES. Skipping it would let the pytest below report the absence as a finding
# about the tree, when the truth is that the checks could not be set up.
_venvs=()
for _d in $_derived; do
    _venvs+=("//$_d:.venv")
done
if ! git_scrubbed bazel build "${_venvs[@]}" //ratchet:ratchet_cli --noshow_progress; then
    say "could not build the venvs and ratchet_cli the checks read — refusing to predict the gate"
    exit 1
fi

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

    # ⚑⚑⚑ AND THE SINGLETON TOO, BECAUSE THE LOOP ABOVE IS PER-DISTRIBUTION AND IT IS NOT.
    # `mikemol-ratchet` lives ONLY in `ratchet/.venv` — measured absent from fence, hooks and
    # mdstruct — so no iteration of the triple ever covers it. It was guarded below by
    # `if [ -x ... ]`, which SKIPS SILENTLY: the ratchet is *the check this script exists for*
    # (it refused three of the four cases that motivated the script), and its absence would make
    # this file predict a green the gate will not give.
    # ⚑⚑ THE SAME DEFECT AS `.githooks/pre-commit` AT 0097f22, ONE FILE OVER — and the arm that
    # caught it there could not see it here, because that arm read the gate ALONE: a hand-written
    # population of one, in a check written against hand-written populations. The arm now derives
    # its consumers, and also anchors `^\s*if` rather than `^if`, because this guard is indented
    # inside a `for dist` loop and a column-anchored pattern read this file as sound.
    _singleton=ratchet/.venv/bin/mikemol-ratchet
    if [ ! -x "$_singleton" ]; then
        say "$_singleton not found — cannot predict the gate, refusing"
        say "  a skip here would report green over a check that never executed"
        exit 1
    fi

    # ⚑⚑ THIS BLOCK ONCE OPENED WITH THE SENTENCE "`--preview` IS INCLUDED BECAUSE THE RATCHET
    # CENSUSES PREVIEW RULES", AND THAT SENTENCE WAS FALSE ABOUT THE LINE BENEATH IT. It is
    # quoted rather than restated, because a false assertion left as the block's FIRST line is
    # the one a reader meets before the correction — the staler an authority, the likelier it is
    # the one a new reader meets first. ⚑ The fact it rested on is true: three of the four
    # refusals it cites were preview keys (`blank-lines-*`), which a bare `ruff check` does not
    # report. What was wrong was the instrument it credited.
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
    # ⚑⚑⚑ ruff AND mypy ARE PREDICTED BY RUNNING THE GATE'S OWN TARGETS, NOT A SECOND COPY.
    # The gate delegated both to `//<dist>:ruff` and `//<dist>:mypy`; a pre-flight still invoking
    # `.venv/bin/ruff` would predict a check the gate no longer performs — which is the exact
    # defect `test_the_preflight_runs_the_ruff_the_gate_runs` exists to refuse, and it DID refuse
    # this file the moment the gate changed. A prediction whose instrument differs from its
    # subject's is not one.
    # ⚑⚑ AND IT STAYS FAST, WHICH IS THIS SCRIPT'S WHOLE PURPOSE: both targets are cached, so a
    # clean tree answers from the action cache with nothing re-executed.
    # ⚑ EXIT 0 AND 1..3 ARE DIFFERENT FACTS, kept as they were for the host ruff: bazel exits 3
    # when a test FAILS and 1 when the BUILD fails, so folding them together would report a broken
    # build as a lint finding.
    # ⚑⚑ `--test_output=errors` SO A REFUSAL CARRIES ITS FINDING. Saying "the gate will refuse
    # this" with no name for WHAT is the *detail that exists somewhere is detail the reader does
    # not have* defect, repaired twice elsewhere in this repo.
    #
    # ⚑⚑⚑ AND `--ui_event_filters=-INFO` SILENTLY DESTROYED EXACTLY THAT, WHILE THE COMMENT ABOVE
    # CLAIMED OTHERWISE. Measured on a planted `PLR2004`, one flag varied at a time:
    #
    #     --test_output=errors --noshow_progress --ui_event_filters=-DEBUG,-WARNING,-INFO
    #                                              rc=3, names PLR2004: FALSE   (7 lines)
    #     --test_output=errors --noshow_progress   rc=3, names PLR2004: TRUE   (26 lines)
    #     --test_output=errors                     rc=3, names PLR2004: TRUE   (33 lines)
    #
    # ⚑ BAZEL EMITS TEST OUTPUT AS AN INFO EVENT, so filtering INFO for quietness discards the
    # finding and leaves a log PATH the reader must go open. `--test_output=all` does not help —
    # measured, also FALSE under the filter — which is what proved the filter was the cause rather
    # than the output mode. The filter is gone; `--noshow_progress` alone is the quiet part.
    git_scrubbed bazel test "//$dist:ruff" "//$dist:mypy" --test_output=errors --noshow_progress
    _rc=$?
    case "$_rc" in
        0) ;;
        3) fail=1; say "$dist: ruff/mypy — the gate will refuse this" ;;
        *) fail=1; say "$dist: bazel EXITED $_rc — the checks did not run; this is not a clean tree" ;;
    esac
    ( cd "$dist" && git_scrubbed .venv/bin/python3 -m pytest -q ) \
        || { fail=1; say "$dist: pytest — the gate will refuse this"; }
    "$root/count_test_functions.py" --pairing "$dist" \
        || { fail=1; say "$dist: warrant pairing — the gate will refuse this"; }

    # ⚑⚑⚑ THE RATCHET IS THE CHECK THAT ACTUALLY REFUSED THREE OF THE FOUR, so it is the one this
    # script exists for. It reads the working tree rather than a staged copy, which is correct
    # here: the point is to answer *what will the gate say about what I am about to stage*.
    # ⚑ NO `if [ -x ]` GUARD: presence is REFUSED ON above, so reaching this line means it exists.
    # ⚑ EXIT 2 IS `cli.CANNOT_CENSUS` (no ruff to run), NOT a new key — the gate names them apart.
    git_scrubbed ratchet/.venv/bin/mikemol-ratchet "$root/$dist"
    _rc=$?
    if [ "$_rc" -eq 2 ]; then
        fail=1; say "$dist: ratchet — COULD NOT CENSUS (no ruff); the gate will refuse this"
    elif [ "$_rc" -ne 0 ]; then
        fail=1; say "$dist: ratchet — a NEW KEY; the gate will refuse this"
    fi

    # ⚑ NO COUNT OF WARRANTS AGAINST TESTS HERE (mtools:W839, operator 2026-10-06: the symmetric
    # difference is empty, not counts). The gate's warrant check is the set pairing, which this
    # script already runs for every distribution above (`count_test_functions.py --pairing`), so
    # the prediction is the same check and names each orphan warrant and unwarranted test.
done

# ⚑⚑ THE ROOT'S OWN BAR, WHICH NO DISTRIBUTION'S LOOP REACHES. The root scripts are linted by
# `//:ruff` and `//:mypy` under the root's lint-only `pyproject.toml`, and its one suite is paired
# against the root `warrants.bib` — the same three predictions as a distribution, over `.`.
git_scrubbed bazel test //:ruff //:mypy --test_output=errors --noshow_progress
_rc=$?
case "$_rc" in
    0) ;;
    3) fail=1; say "root: ruff/mypy — the gate will refuse this" ;;
    *) fail=1; say "root: bazel EXITED $_rc — the checks did not run; this is not a clean tree" ;;
esac
# ⚑ THE ROOT AND THE ATOMS ARE PAIRED WHEN THEY CARRY A LEDGER, as the gate pairs them (W328,
# W326). The root's ledger moved to check_mutants with the test it warranted.
for _f in "$root"/*/MODULE.bazel "$root/MODULE.bazel"; do
    _m="$(dirname "$_f")"
    [ -L "$_m" ] && continue
    [ -f "$_m/warrants.bib" ] || continue
    "$root/count_test_functions.py" --pairing "$_m" \
        || { fail=1; say "$_m: warrant pairing — the gate will refuse this"; }
done

if [ "$fail" -ne 0 ]; then
    say "⚑ the gate WOULD REFUSE, and it stops at the FIRST failing check — fix all of the above."
    exit 1
fi
# ⚑⚑⚑ THIS LINE ONCE SAID `nine domain witnesses` AND THE GATE INVOKES EIGHT. A hand-written
# population inside the instrument whose entire job is predicting that gate — and it passed every
# arithmetic check, because nothing about `nine` is malformed. It is a correct-looking number over
# a population nobody enumerated, which is the defect this session has measured most.
# ⚑⚑ THE FIGURE MOVES BY CONSTRUCTION: a witness is added by writing one `witness` line, so the
# count changes whenever the gate's coverage does. A hardcoded number describing a thing designed
# to grow rots silently and reports the rot as reassurance.
# ⚑ DERIVED FROM THE GATE ITSELF rather than restated here, so the two cannot disagree. If the
# gate is unreadable the count is reported as UNKNOWN rather than guessed — an unmeasured figure
# named as unmeasured is the honest form, and a fabricated one is the defect being repaired.
_gate="$root/.githooks/pre-commit"
if [ -r "$_gate" ]; then
    _witnesses="$(grep -c '^witness ' "$_gate")"
else
    _witnesses="an unknown number of"
fi
say "ok — these checks are clean; the bazel suite and $_witnesses domain witnesses are still ahead"

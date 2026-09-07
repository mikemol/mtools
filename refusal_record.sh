#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ THE RECORD COUNTED ONE REFUSAL PATH AND CALLED IT REFUSALS. Its purpose is a lower bound on
# how many peer commits this gate has refused. MEASURED across every hook in `.githooks/`: SEVEN
# paths reach `exit 1` and exactly ONE wrote a row — `pre-commit`'s accumulated-failure verdict.
# The two early exits (a missing tool, a missing bazel) and all four `commit-msg` exits refused
# and vanished.
#
# ⚑⚑ A CORRECT COUNT OVER A MIS-NAMED POPULATION. Every row in that file was true, the arithmetic
# was right, and the name on the column was `failed_checks` — so nothing in it could reveal that
# the population was *refusals of one kind*. It undercounts in the flattering direction: a gate
# that refuses more than it records reads as cheaper than it is, which is the live question an
# operator is holding open about this gate's cost.
#
# ⚑ ONE FILE, SOURCED BY BOTH HOOKS, because this gate's own `note_failure` comment says it: a
# repair applied to one call site is not a repair to the class. A second copy in `commit-msg`
# would be the two-writers shape that comment was written about.
set -uo pipefail

# ⚑ THE SAME DIRECTORY THE GATE ALREADY USES. Not a new location: a reader joining rows against
# `git log` should not have to learn two paths.
_rr_logs="${TMPDIR:-/home/mikemol/.cache}/mtools-gate-logs"

# record_refusal <hook> <labels> [detail]
#
# ⚑ THE HOOK NAME IS A COLUMN BECAUSE THE PATH IS THE THING THAT WAS MISSING. A row saying only
# *some check failed* cannot answer which gate is doing the refusing, and that is the question the
# record exists to answer.
record_refusal() {
    mkdir -p "$_rr_logs" 2>/dev/null || return 0
    _rr_log="$_rr_logs/REFUSALS.tsv"
    # ⚑ Header only when absent, so an append-only file cannot grow a header per row.
    if [ ! -s "$_rr_log" ]; then
        printf '%s\t%s\t%s\t%s\t%s\n' \
            'utc' 'session' 'committer' 'hook' 'failed_checks' \
            >> "$_rr_log" 2>/dev/null || true
    fi
    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        "${CLAUDE_CODE_SESSION_ID:-unknown-session}" \
        "$(git config user.email 2>/dev/null || echo unknown)" \
        "$1" \
        "$(printf '%s' "$2" | tr '\n' ' ' | sed 's/  */ /g')" \
        >> "$_rr_log" 2>/dev/null || true
    # ⚑ The account outlives the run only when a check captured one; an empty file would assert
    # that a refusal had no account, which is a different claim.
    if [ -n "${3:-}" ]; then
        printf '%s\n' "$3" \
            > "$_rr_logs/refusal-$(date -u +%Y%m%dT%H%M%SZ)-detail.log" 2>/dev/null || true
    fi
}

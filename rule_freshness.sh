#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A CITATION GATE PROVES A POINTER RESOLVES; IT SAYS NOTHING ABOUT WHETHER THE TARGET IS
# STILL TRUE. `rule_citations.sh` closed the case where a commit names a rule that was never
# written. This closes the next one: a rule that IS written, IS cited, and has quietly stopped
# describing the world. Those are different failures and the second is worse — a stale rule is
# indistinguishable from a live one at every point except the measurement it was derived from.
#
# ⚑⚑ ONLY ENVIRONMENT CLAIMS ARE CHECKED HERE, AND THAT SCOPE IS DELIBERATE. A rule about how a
# probe should be armed is a claim about reasoning and does not decay. A rule naming a PORT, a
# POD, or a COUNTER is a claim about a running system that changes without touching this repo —
# and Rule 12's own addendum already records that the BuildBuddy Service selector matches TWO
# pods, with only readiness disambiguating them. That is one `kubectl` away from being false.
#
# ⚑ IT REPORTS RATHER THAN REFUSES, AND THAT IS NOT A SOFT GATE. The subject is a shared cluster
# this repository does not own: a red gate on someone else's outage blocks commits that have
# nothing to do with it, and a gate that blocks for reasons the author cannot fix is a gate that
# gets bypassed. UNVERIFIABLE is a third outcome, distinct from FRESH and STALE.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
rules="findings/bazel/mtools.md"
metrics="http://127.0.0.1:31464/metrics"

say() { printf '  %s\n' "$*"; }
stale=0

if [ ! -f "$rules" ]; then
    echo "rule_freshness: $rules is missing" >&2
    exit 1
fi

# ⚑ THE CLAIM IS READ FROM THE RULES FILE, NOT RETYPED HERE. A checker carrying its own copy of
# the thing it verifies drifts from the document silently — which is the two-copies-of-one-list
# defect this repository has now measured three times.
if ! grep -q "31464" "$rules"; then
    say "no rule cites the metrics port — nothing to re-check"
    exit 0
fi

# ⚑⚑ Rule 12 rests on ONE endpoint serving the port. Two ready pods behind that Service would
# make every counter delta a sample from an unknown one of two populations, and the control arm
# CANNOT detect it: a no-op build moves neither pod's counters, so the control passes identically
# in both worlds. This is the premise the arms structurally cannot reach.
if command -v kubectl >/dev/null 2>&1; then
    # ⚑⚑⚑ A POSITIVE CONTROL, BECAUSE THIS CHECKER HAD NONE AND ITS WHOLE OUTPUT IS A NEGATIVE.
    # "Exactly one endpoint" is the reading that keeps Rule 12 valid — and a reader that returned
    # 1 for EVERYTHING would print FRESH forever. The arms this was built with were simulated
    # (an edited copy asserting two IPs); nothing proved the LIVE query could produce any other
    # number.
    #
    # ⚑⚑ AND NO IN-CORPUS CONTROL FOR "TWO" EXISTS: measured, all 13 Services in the namespace
    # have exactly one endpoint. So the control tests the discriminating CAPABILITY instead —
    # `pgbouncer` has ZERO, which proves the count varies with the subject rather than being a
    # constant the query manufactures. That is the census brief's own fallback: when the shape is
    # genuinely absent, exhibit the control on reader capability.
    ctl=$(kubectl -n cassian get endpoints pgbouncer -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null | wc -w)
    if [ "$ctl" -ne 0 ]; then
        say "⚑ CONTROL FAILED: pgbouncer should have 0 endpoints, read $ctl — this reader's"
        say "  counts are not trustworthy, so the freshness verdict below is UNMEASURED"
        exit 0
    fi
    eps=$(kubectl -n cassian get endpoints buildbuddy -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)
    n=$(printf '%s' "$eps" | wc -w)
    case "$n" in
        1) say "Rule 12 premise FRESH: exactly one endpoint serves the metrics Service ($eps)" ;;
        0) say "Rule 12 premise UNVERIFIABLE: no endpoints listed (cluster down, or renamed)" ;;
        *) say "⚑ Rule 12 STALE: $n endpoints serve the Service — counter deltas sample an"
           say "  unknown one of $n populations, and the control arm cannot detect it"
           stale=1 ;;
    esac
else
    say "Rule 12 premise UNVERIFIABLE: no kubectl — a fact about this reader, not the cluster"
fi

# ⚑ THE PORT ITSELF, because three rules name it. A 404 here is what sent three sessions to the
# wrong conclusion once already: it is a real HTTP response, so it reads as evidence of absence
# rather than as evidence about one address.
if command -v curl >/dev/null 2>&1; then
    if curl -sf --max-time 5 "$metrics" >/dev/null 2>&1; then
        say "metrics port FRESH: $metrics answers"
    else
        say "⚑ metrics port UNVERIFIABLE: $metrics did not answer — three rules cite it"
    fi
else
    say "metrics port UNVERIFIABLE: no curl"
fi

[ "$stale" -eq 0 ] || echo "rule_freshness: a cited premise has CHANGED — the rule needs re-measuring" >&2
exit 0

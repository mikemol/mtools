#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ THE STANDING BLOCKERS, AS A COMMAND RATHER THAN A REMEMBERED LIST. A claim with no
# re-derivation procedure will not be re-checked however load-bearing it is, because nothing about
# it announces that it could be. This repository carried "substrate and cassian's sessions are
# gone" through several derivation cycles — false for an hour — while dutifully re-measuring four
# filesystem blockers beside it. The discriminator was not importance; it was that four had a
# command attached and one did not.
#
# ⚑⚑ AND ONE OF THE FOUR WAS PROBING A PATH THAT DOES NOT EXIST. `substrate/scripts/
# membudget-ledger` has no `substrate/scripts/` directory; the real path is `scripts/
# membudget-ledger`. It reported "untracked" — the right answer for the wrong reason — every
# cycle, and agreed with the truth by luck, so nothing surfaced it. Had the ledger been committed
# at the real path this would have read as blocked indefinitely. A FALSE NEGATIVE THAT HAPPENS TO
# BE CORRECT IS INVISIBLE TO ITS OWN RE-RUN.
#
# ⚑ HENCE THE CONTROL. Every tracked-file query is paired with a probe that MUST find something,
# which distinguishes "absent" from "I am looking in the wrong place" — Rule 7's control arm
# arriving at a filesystem query rather than a build.
set -uo pipefail

sub=/home/mikemol/github/substrate
mtools="$(cd "$(dirname "$0")" && pwd)"

tracked() {  # repo, path, label
    if git -C "$1" ls-files --error-unmatch "$2" >/dev/null 2>&1; then
        printf '  %-34s TRACKED\n' "$3"
    else
        printf '  %-34s untracked\n' "$3"
    fi
}

# ⚑⚑ THE CONTROL PATH IS MEASURED, NOT GUESSED — and the first one was guessed and FAILED. This
# script's first run reported the control `substrate/README.md` as untracked, because substrate has
# no root README.md. That is the control doing its job on its own first execution: had it been
# taken as a pass, every "untracked" below would have been unverified. `.claude/agents/findings.py`
# is chosen because `git ls-files` lists it; substrate tracks 3,622 files, so its absence would
# mean the query itself is broken.
echo "=== control: a path known to be tracked must read TRACKED ==="
tracked "$sub" .claude/agents/findings.py "substrate findings.py (control)"

# ⚑⚑⚑ THE POPULATION IS ENUMERATED, NOT ASSERTED. A hand-written list of five module names is
# `0 of 5` reported as `0 of the island` — it cannot see a sixth module, and a control proves only
# that the QUERY works, never that the SEARCH SPACE was right. A peer stated the class after
# reporting "the CAS counters are out of reach" from one endpoint without enumerating the service's
# ports: that was `0 of 1` reported as `0 of the world`, and one `kubectl get svc` would have shown
# three. So this counts what exists before reporting what is tracked.
echo "=== substrate: the ratchet island ==="
island=$(find "$sub/substrate" -maxdepth 1 -name 'ratchet*.py' -o -maxdepth 1 -name 'baseline*.py' \
         -o -maxdepth 1 -name 'withheld*.py' 2>/dev/null | wc -l)
echo "  population: $island module(s) match the island's naming on disk"
for f in $(find "$sub/substrate" -maxdepth 1 \( -name 'ratchet*.py' -o -name 'baseline*.py' \
           -o -name 'withheld*.py' \) -printf '%f\n' 2>/dev/null | sort); do
    tracked "$sub" "substrate/$f" "$f"
done

echo "=== substrate: the membudget ledger ==="
# ⚑ `scripts/`, NOT `substrate/scripts/` — corrected by the peer who owns the tree.
tracked "$sub" scripts/membudget-ledger "scripts/membudget-ledger"

echo "=== mtools: cassian's components ==="
git -C "$mtools" ls-files \
    | cut -d/ -f1 | sort -u \
    | grep -vE '^(hooks|mdstruct|ratchet|rbe|findings|inbox|\.|BUILD|LICENSE|MODULE|README|SKELETON|blockers|pytest_main|setup|shellcheck_test|ruff_check|ratchet_check|mypy_check|mypy_runner)' \
    | sed 's/^/  landed: /' \
    || echo "  none landed"

echo "=== mtools: paperkit resolvable ==="
if "$mtools/mdstruct/.venv/bin/python3" -c 'import paperkit' 2>/dev/null; then
    echo "  paperkit IMPORTABLE"
else
    echo "  paperkit unimportable"
fi

echo "=== mtools: inbox ==="
find "$mtools/inbox" -name '*.md' ! -name README.md -printf '  mail: %f\n' 2>/dev/null \
    | grep . || echo "  inbox empty"

# ⚑⚑ REACHABILITY IS NOT CHECKED HERE AND THAT IS DELIBERATE. It is a live-session property, not a
# filesystem one — `ListAgents` is the instrument and only the harness can run it. Naming its
# absence is the point: this script covers what it covers, and the one claim it CANNOT cover is
# exactly the one that went stale for an hour.
echo "=== NOT COVERED: peer reachability — run ListAgents; it is a reading, not a fact ==="

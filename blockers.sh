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

# ⚑⚑⚑ A DENYLIST OF WHAT EXISTED WHEN IT WAS WRITTEN IS NOT A POPULATION QUERY, AND THIS ONE
# ROTTED IN EXACTLY THE WAY THIS SCRIPT'S OWN HEADER WARNS ABOUT. The first cut listed every
# top-level name and filtered out the ~17 that were present that day. So every file added AFTER
# it was written reported as a peer's landed component: measured, `collect_check.sh` and
# `PATHS-FORWARD.md` — two files this session wrote — were announced as cassian's deliverables.
#
# ⚑⚑ AND IT FAILS TOWARD FALSE PRESENCE, WHICH IS THE DIRECTION THAT ENDS AN INQUIRY. A blocker
# reporting "still blocked" gets re-measured next tick; one reporting "landed" is done being
# asked about. This script exists to be re-run on a schedule, so a false clear is a defect that
# removes its own detector.
#
# ⚑ THE REPAIR IS A STRUCTURAL CRITERION RATHER THAN A LONGER DENYLIST: a component IS a
# directory carrying a `pyproject.toml`. That cannot drift as this repo grows, a landed component
# necessarily satisfies it, and the three known distributions are the control below.
echo "=== mtools: components (a dir with a pyproject.toml) ==="
known="hooks mdstruct ratchet"
found=$(git -C "$mtools" ls-files '*/pyproject.toml' | cut -d/ -f1 | sort -u)

# ⚑ THE CONTROL MUST FIND THE THREE THIS REPO ALREADY HAS. A structural query that returned
# nothing would print "none landed" and read exactly like a correct negative.
for k in $known; do
    printf '%s\n' "$found" | grep -qx "$k" \
        || echo "  CONTROL FAILED: $k has a pyproject.toml and this query missed it"
done

printf '%s\n' "$found" | grep -vxF -e hooks -e mdstruct -e ratchet \
    | sed 's/^/  landed: /' \
    | grep . || echo "  none landed beyond the three this session authored"

echo "=== mtools: paperkit resolvable ==="
if "$mtools/mdstruct/.venv/bin/python3" -c 'import paperkit' 2>/dev/null; then
    echo "  paperkit IMPORTABLE"
else
    echo "  paperkit unimportable"
fi

echo "=== mtools: inbox ==="
# ⚑⚑⚑ UNREAD, NOT PRESENT — AND THE FIRST CUT MEASURED THE WRONG ONE. It listed every message
# in `inbox/`, so a message ACTED ON two ticks earlier reported as `mail:` on every subsequent
# tick, forever. That is Rule 18's own failure forming in the instrument that produced Rule 18: a
# line that says the same thing every time stops being read as a measurement and becomes
# furniture. A permanent "you have mail" is exactly as uninformative as a permanent "inbox empty".
#
# ⚑⚑ THE ARCHIVE CONVENTION IS THE ECOSYSTEM'S, NOT AN INVENTION. Measured before adopting:
# `cassian-observability` holds 9 live / 11 archived and `paperkit` 42 / 5, both under
# `inbox/archive/` with the filename unchanged. Inventing a marker here would have been a second
# convention for a solved problem — the re-derivation this repository exists to stop.
find "$mtools/inbox" -maxdepth 1 -name '*.md' ! -name README.md -printf '  UNREAD: %f\n' 2>/dev/null \
    | grep . || echo "  inbox: nothing unread ($(find "$mtools/inbox/archive" -name '*.md' 2>/dev/null | wc -l) archived)"

# ⚑⚑⚑ THE CENSUS FREEZE, POLLED AS A ROSTER RATHER THAN AS A STRING. A peer designated its
# revision log as the freeze artifact, and BOTH obvious string predicates were wrong: `grep`
# false-positived on the section's own prose describing the rule, and a row-wide substring matched
# the revision that REPAIRED the mechanism, because a cell announcing a fix carries the trigger it
# announces. The freeze is a property of the ROSTER — every party terminal — not of a spelling.
#
# ⚑⚑ AND THE COUNT IDENTITY IS THE PEER'S FINDING, NOT MINE: a party silently ABSENT from the
# table says exactly what a party with a terminal status says, so a dropped row reads as FROZEN.
# Asking "is anything non-terminal" is not enough; the population must also be whole. That is
# "what ELSE produces this reading" rather than "can I make this fail", and it finds what the
# first question cannot, because the first requires imagining the bad state in advance.
echo "=== census: is the freeze called? ==="
census="$mtools/findings/CENSUS-deps-build.md"
md="$mtools/mdstruct/.venv/bin/mdstruct"
if [ ! -x "$md" ]; then
    echo "  UNMEASURED: $md is not executable — this is a fact about the reader, not the freeze"
elif [ ! -f "$census" ]; then
    echo "  UNMEASURED: no census file at $census"
else
    roster=$("$md" tables "$census" 2>/dev/null | grep 'party | status' | grep -oE '[0-9]+ row' | grep -oE '[0-9]+')
    pending=$("$md" rows "$census" --col 1 --starts "in progress" 2>/dev/null | grep -cE '^  table')
    printf '  roster: %s of 6 parties listed; %s non-terminal\n' "${roster:-?}" "${pending:-?}"
    # ⚑⚑ BOTH ARMS MEASURED, on constructed fixtures, before this was trusted:
    #   all six terminal            -> roster=6 pending=0 -> FROZEN      (the poll CAN fire)
    #   cassian's §S row deleted    -> roster=5 pending=0 -> caught here (the pending check
    #                                  alone reported FROZEN; only the count identity refused)
    # ⚑ The second arm is the peer's finding and it is the one a "can I make this fail" probe
    # misses: nothing about a deleted row is a bad STATUS, so you only find it by asking what
    # ELSE produces "nothing non-terminal".
    if [ "${roster:-0}" -ne 6 ]; then
        echo "  NOT FROZEN — and the roster is SHORT: a dropped row reads as terminal"
    elif [ "${pending:-1}" -ne 0 ]; then
        echo "  NOT FROZEN — a party is still non-terminal; the embargo holds"
    else
        echo "  ⚑ FROZEN — every party terminal over a whole roster. Cross-reading is now the point."
    fi
fi

# ⚑⚑⚑ FRESHNESS RUNS HERE *AND* IN THE GATE, AND THAT IS TWO QUESTIONS RATHER THAN ONE ANSWER
# TWICE. The gate asks it once per commit — AFTER the work, when a stale premise can no longer
# change what was worth doing. This script runs at the START of a derivation, where the same
# answer REORDERS THE LIST: a rule whose cited premise has moved is a blocker, and a blocker that
# only surfaces at commit time surfaces after every decision it should have informed.
#
# ⚑⚑ MEASURED BEFORE ADDING IT: the tick was blind to this. `./blockers.sh | grep -ci
# 'fresh|stale|unverifiable'` returned 0 while `rule_freshness.sh` had been running in the gate
# for a full tick — the finding existed, was armed, and reached the one moment it could not act on.
if [ -x "$mtools/rule_freshness.sh" ]; then
    echo "=== are the environment claims this repo cites still true? ==="
    "$mtools/rule_freshness.sh" || true
else
    echo "=== rule freshness: UNMEASURED — rule_freshness.sh is not executable ==="
fi

# ⚑⚑ REACHABILITY IS NOT CHECKED HERE AND THAT IS DELIBERATE. It is a live-session property, not a
# filesystem one — `ListAgents` is the instrument and only the harness can run it. Naming its
# absence is the point: this script covers what it covers, and the one claim it CANNOT cover is
# exactly the one that went stale for an hour.
echo "=== NOT COVERED: peer reachability — run ListAgents; it is a reading, not a fact ==="

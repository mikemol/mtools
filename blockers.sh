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

# ⚑⚑⚑ `ls-files` ANSWERS A DIFFERENT QUESTION THAN INTAKE ASKS, AND THIS SCRIPT ASKED THE WRONG
# ONE FOR TEN TICKS. It reports a STAGED file as tracked — correctly, because the index IS the
# tracking record — but *tracked in a peer's index* and *fetchable by me* are different
# properties, and only the second decides whether code can move. Measured: every island module
# this script called TRACKED has ZERO commits on the branch. Not one is fetchable. A blocker
# reported as clearing, for ten ticks, that never cleared.
#
# ⚑⚑ AND `git log --all` IS WORSE, NOT BETTER. On the same file it shows 33 commits — every one
# under `refs/edit-snapshots/`, an editor's snapshot guard, none on any branch, none carried by a
# clone or fetch. A reader reaching for the more thorough instrument sees dense history and
# concludes the file is fetchable. Three instruments, one file: `ls-files` says tracked,
# `log --all` says 33 commits, `log` on the branch says nothing exists. ⚑ ONLY THE THIRD ANSWERS
# THE QUESTION, and it is the one that looks least thorough.
#
# ⚑ Reported by the peer whose tree it is, then reproduced here before adopting.
tracked() {  # repo, path, label
    if ! git -C "$1" ls-files --error-unmatch "$2" >/dev/null 2>&1; then
        printf '  %-34s untracked\n' "$3"
    elif [ "$(git -C "$1" log --oneline -- "$2" | wc -l)" -gt 0 ]; then
        printf '  %-34s FETCHABLE\n' "$3"
    else
        printf '  %-34s staged only (NOT fetchable)\n' "$3"
    fi
}

# ⚑⚑ THE CONTROL PATH IS MEASURED, NOT GUESSED — and the first one was guessed and FAILED. This
# script's first run reported the control `substrate/README.md` as untracked, because substrate has
# no root README.md. That is the control doing its job on its own first execution: had it been
# taken as a pass, every "untracked" below would have been unverified. `.claude/agents/findings.py`
# is chosen because `git ls-files` lists it; substrate tracks 3,622 files, so its absence would
# mean the query itself is broken.
# ⚑⚑⚑ THE CONTROL WAS RE-CHOSEN WHEN THE PREDICATE CHANGED, AND THE OLD ONE WOULD HAVE PASSED
# VACUOUSLY. `.claude/agents/findings.py` was picked to prove `ls-files` could see something; under
# the fetchability predicate it reads "staged only" — so the control would have reported the same
# thing as every subject it was meant to discriminate against. ⚑ A CONTROL VALIDATES ONE
# PROPERTY, AND CHANGING THE PREDICATE SILENTLY ORPHANS IT: nothing about the old line announced
# that it had stopped controlling for anything.
#
# ⚑ `applied_grammar.py` is chosen by MEASUREMENT, not by belief: it carries 2 commits on the
# branch and is present in `HEAD`'s tree, which is exactly the property intake needs. Four
# plausible guesses (`ratchet_core.py`, `corpus.py`, `README.md`, `agda_dag.py`) all failed that
# test first — the control had to be taken FROM the tree rather than proposed to it.
echo "=== control: a path known to be FETCHABLE must read FETCHABLE ==="
tracked "$sub" applied_grammar.py "substrate applied_grammar.py (control)"

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
# ⚑⚑⚑ THE POPULATION IS DERIVED, AND HARDCODING ONE PATH MADE THIS POLL BLIND TO A WHOLE CENSUS.
# This block named `CENSUS-deps-build.md` directly. A second census — `CENSUS-constitution.md` —
# was convened, run, and FROZEN while this script reported a confident state that did not mention
# it. MEASURED on the tick that found it: the poll said `FROZEN` and I had to discover by hand
# that a second census existed, was frozen, and had an unadmitted eighth leg in its directory.
#
# ⚑⚑ THAT IS `MEASURED-WITH-THE-WRONG-KEY` (gabion, 2026-09-06) IN THIS INSTRUMENT: the poll
# answered *is deps-build frozen* and its reader took it for *what is my census state*. A key that
# is cheap to compute and never asked what it is evidence OF gives a clean, well-formed, confident
# answer about the wrong question — which is worse than a noisy one, because nothing looks wrong.
#
# ⚑ EIGHTH HAND-WRITTEN POPULATION FOUND IN THIS REPOSITORY'S OWN CHECKERS. Every previous one
# rotted the same way: the denylist, the shellcheck target list, `exports_files`, the figure scan,
# the orphan sites, the hardcoded roster size, and §X's drift table omitting `hook_pycheck`.
md="$mtools/mdstruct/.venv/bin/mdstruct"
# `CENSUS-BRIEF` is the standing brief and `-ANALYSIS` is a companion; neither carries a roster.
censuses=$(cd "$mtools" && git ls-files 'findings/CENSUS-*.md' \
    | grep -v 'CENSUS-BRIEF' | grep -v 'ANALYSIS')
if [ ! -x "$md" ]; then
    echo "  UNMEASURED: $md is not executable — this is a fact about the reader, not the freeze"
elif [ -z "$censuses" ]; then
    echo "  UNMEASURED: no census run file is tracked under findings/"
else
  for rel in $censuses; do
    census="$mtools/$rel"
    printf '  --- %s\n' "$rel"
    # ⚑⚑⚑ BOTH QUERIES ARE SCOPED BY THE TABLE'S HEADER SIGNATURE, and only the first one was.
    # The roster count already keyed on `party | status`, which is a property of the table. The
    # PENDING count did not: `rows --col 1 --starts` searches EVERY table in the document, so a
    # row in an unrelated table whose second column begins "in progress" is counted as a
    # non-terminal party. ⚑ MEASURED on a fixture with one extra table: 2 matches, one of them
    # from a table that is not the roster.
    #
    # ⚑⚑ THE PEER FOUND THE SAME CLASS IN ITS OWN INSTRUMENT — `§G` keyed the freeze poll on
    # `--table 4`, and inserting a section renumbered the tables so the roster stayed at 4 BY
    # LUCK. A positional predicate that silently retargets produces a CONFIDENT WRONG ANSWER,
    # where an expired pointer at least fails to resolve. Reported to me, checked here, present.
    # ⚑⚑⚑ THE SIGNATURE IS PER-CENSUS AND HARDCODING ONE MADE THE POLL REPORT A FROZEN CENSUS AS
    # NOT FROZEN. `deps-build`'s §S is `party | status`; `constitution`'s is `surveyor | status`.
    # MEASURED the moment this block was generalised over both: roster `? of 7`, then
    # `NOT FROZEN — the roster is SHORT`, against a census whose §V carries FREEZE CALLED at rev 37
    # and whose seven legs are all in HEAD. ⚑ A confident refusal produced by a missing table, not
    # by a missing row — the same class as the positional `--table N` predicate this block already
    # refuses, arriving through the header instead of the index.
    #
    # ⚑ SO THE STATUS TABLE IS IDENTIFIED BY ITS SECOND COLUMN, which is the property that makes
    # it the status table, rather than by the noun a given run file happened to choose for parties.
    sig=$("$md" tables "$census" 2>/dev/null | grep -oE '(party|surveyor) \| status' | head -1)
    [ -n "$sig" ] || sig='party | status'
    roster=$("$md" tables "$census" 2>/dev/null | grep "$sig" | grep -oE '[0-9]+ row' | grep -oE '[0-9]+')
    tbl=$("$md" tables "$census" 2>/dev/null | grep "$sig" | grep -oE 'table [0-9]+' | grep -oE '[0-9]+')
    if [ -z "$tbl" ]; then
        echo "  UNMEASURED: no table carries the roster's header signature ($sig)"
        tbl=-1
    fi
    pending=$("$md" rows "$census" --col 1 --starts "in progress" 2>/dev/null \
        | grep -cE "^  table ${tbl} ")
    # ⚑⚑⚑ THE EXPECTED SIZE IS DERIVED FROM §R, NOT HARDCODED. The roster grew to seven when the
    # operator added `summit` at rev 21, and this script reported `7 of 6 — the roster is SHORT`,
    # which INVERTS ITS OWN EVIDENCE: the count exceeded the target and the string said deficit.
    # ⚑ Not an off-by-one — a predicate whose comparison could not represent the case that
    # occurred, so it fell through to the wrong branch and asserted with confidence.
    #
    # ⚑⚑ §R IS THE AUTHORITY AND CARRIES THE APEX AS AN EXTRA ROW. Measured: §R has 8 rows to §S's
    # 7, and the difference is exactly the apex line, which is not a surveying party. So expected
    # = |§R| - 1, and the identity survives every future dispatch without an edit here.
    expected=$(( $("$md" tables "$census" 2>/dev/null | grep 'surveyor | prefix' \
        | grep -oE '[0-9]+ row' | grep -oE '[0-9]+') - 1 ))
    printf '  roster: %s of %s parties listed; %s non-terminal\n' \
        "${roster:-?}" "${expected:-?}" "${pending:-?}"
    # ⚑⚑ BOTH ARMS MEASURED, on constructed fixtures, before this was trusted:
    #   all six terminal            -> roster=6 pending=0 -> FROZEN      (the poll CAN fire)
    #   cassian's §S row deleted    -> roster=5 pending=0 -> caught here (the pending check
    #                                  alone reported FROZEN; only the count identity refused)
    # ⚑ The second arm is the peer's finding and it is the one a "can I make this fail" probe
    # misses: nothing about a deleted row is a bad STATUS, so you only find it by asking what
    # ELSE produces "nothing non-terminal".
    if [ "${roster:-0}" -ne "${expected:-0}" ]; then
        echo "  NOT FROZEN — and the roster is SHORT: a dropped row reads as terminal"
    elif [ "${pending:-1}" -ne 0 ]; then
        echo "  NOT FROZEN — a party is still non-terminal; the embargo holds"
    else
        # ⚑⚑⚑ THE ROSTER CONDITION IS NECESSARY AND NOT SUFFICIENT. §G is explicit: the freeze
        # is a ROW IN §V reading `FREEZE CALLED`, and a message is a courtesy rather than the
        # event. Measured the moment the roster went terminal: no such row exists and §S's own
        # heading still reads NOT YET CALLED. ⚑ A satisfied precondition read as the event is this
        # repository's own green-over-nothing, in the poll that exists to refuse it.
        if "$md" rows "$census" --col 2 --starts "FREEZE" >/dev/null 2>&1; then
            echo "  ⚑ FROZEN — roster terminal AND §V carries the row. Cross-reading is the point."
        else
            echo "  NOT FROZEN — the roster condition is met, but §V carries no FREEZE CALLED row."
            echo "    That is the coordinator's to declare; a met precondition is not the event."
        fi
    fi
    # ⚑⚑⚑ AN UNADMITTED LEG IS INVISIBLE TO EVERY QUERY ABOVE, AND THAT IS THE CASE THAT OCCURRED.
    # `gabion` filed into `findings/constitution/` AFTER the freeze accounted seven parties —
    # untracked, correctly flagged as out-of-freeze by its author, and absorbed by nobody. The
    # roster count reads §S, the freeze reads §V, and NEITHER can see a file on disk that no row
    # mentions. ⚑ So a party that never appeared in the accounting is exactly the thing `§G` calls
    # a remainder entry rather than a silent omission — and it stayed silent to this poll.
    #
    # ⚑⚑ NOT AN ERROR, AND REPORTED AS SUCH. Admitting an eighth party against a roster frozen at
    # seven is an operator's act. This line makes it VISIBLE at the start of a derivation instead
    # of at the moment someone reads `ls-tree` and finds a count that disagrees with `§S`.
    legs="$mtools/findings/$(basename "$rel" .md | sed 's/^CENSUS-//')"
    if [ -d "$legs" ]; then
        unadmitted=$(cd "$mtools" && git ls-files --others --exclude-standard "${legs#"$mtools"/}")
        if [ -n "$unadmitted" ]; then
            echo "  ⚑ UNADMITTED artifact(s) in the leg directory — in no commit, in no §S row:"
            # ⚑ ONE LINE PER FILE, read from the variable rather than splitting it: `printf` with
            # an unquoted expansion would split correctly here and be indistinguishable from the
            # accidental splitting shellcheck exists to catch.
            printf '%s\n' "$unadmitted" | sed 's/^/      /'
            echo "    Whether these enter the accounting is the operator's, not the poll's."
        fi
    fi
  done
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

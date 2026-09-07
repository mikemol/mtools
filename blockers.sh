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

# ⚑⚑⚑ THIS ARM PRINTED ONE WORD FOR THREE STATES WITH THREE DIFFERENT OWNERS. `unimportable`
# collapses *paperkit is broken* (its owner's), *it is not installed here* (this repo's), and
# *the interpreter is absent* (a fact about the reader). A blocker that cannot say which it found
# cannot be acted on — and this one was carried unacted-on for the whole session because
# `unimportable` reads like a defect in paperkit.
#
# ⚑⚑ MEASURED WHICH: `uv pip install --dry-run` resolves the local checkout in milliseconds —
# *Would install 1 package*. paperkit is neither broken nor missing. Nothing here installs it, and
# `mdstruct/pyproject.toml` says why: it is declared as a PUBLISHED PACKAGE, never a path. THAT IS
# AN OPERATOR DECISION and this arm does not settle it; it reports which state it observed.
#
# ⚑ AND THE PROBE CARRIES A CONTROL, because through `2>/dev/null` a failing import and a missing
# interpreter are byte-identical. A probe whose failure mode includes *the reader was absent* must
# exhibit a hit of the same shape — this repository's own rule, applied to the one arm that never
# carried it.
echo "=== mtools: paperkit resolvable ==="
_pk_py="$mtools/mdstruct/.venv/bin/python3"
if [ ! -x "$_pk_py" ]; then
    echo "  paperkit: CONTROL UNAVAILABLE — $_pk_py is not executable."
    echo "    That is a fact about this reader, not about paperkit."
elif ! "$_pk_py" -c 'import json' 2>/dev/null; then
    echo "  paperkit: CONTROL FAILED — the interpreter cannot import a stdlib module."
    echo "    Any verdict below would describe the reader rather than paperkit."
elif "$_pk_py" -c 'import paperkit' 2>/dev/null; then
    echo "  paperkit IMPORTABLE (control: this interpreter imports)"
else
    echo "  paperkit not installed here (control: this interpreter imports stdlib fine)"
    echo "    NOT a defect in paperkit: its checkout resolves as an installable package."
    echo "    It is declared as a published package rather than a path — whether to install"
    echo "    it from a local checkout is the operator's call, not this poll's."
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
# ⚑⚑⚑ TRACKED IS NOT THE POPULATION, AND KEYING ON IT REPRODUCED THE DEFECT THE PREVIOUS REPAIR
# WAS FOR. One tick ago this line was a hardcoded path; replacing it with `git ls-files` looked
# like deriving the population and was a SECOND cheap key — `is it committed` rather than `is it
# a census run file`. MEASURED the tick after: `CENSUS-build-hermeticity.md` was convened by a
# peer, placed in this tree, carried mtools on its roster, and was INVISIBLE here because its
# dispatcher had not committed it yet.
#
# ⚑⚑ THAT IS THE MOST COMMON STATE, NOT AN EDGE CASE. A census is dispatched the moment the run
# file lands on disk — peers read it by path and file legs against it — and it reaches HEAD
# whenever its author next gets a clear interval, which in this tree is minutes to hours behind.
# So `git ls-files` excludes precisely the window in which a poll saying "here is what is open"
# has the most to report. ⚑ `§F`'s own inversion, arriving in my instrument: a file in a working
# tree is not an artifact another party can READ, but it is one another party can be ROSTERED BY.
#
# ⚑ SO THE FILESYSTEM IS THE POPULATION AND TRACKEDNESS IS A COLUMN. `find` sees both; the
# untracked ones are marked, because "this census is not in HEAD" is a fact worth reporting rather
# than a reason to omit the row.
censuses=$(cd "$mtools" && find findings -maxdepth 1 -name 'CENSUS-*.md' -type f 2>/dev/null \
    | grep -v 'CENSUS-BRIEF' | grep -v 'ANALYSIS' | sort)
if [ ! -x "$md" ]; then
    echo "  UNMEASURED: $md is not executable — this is a fact about the reader, not the freeze"
elif [ -z "$censuses" ]; then
    echo "  UNMEASURED: no census run file is tracked under findings/"
else
  for rel in $censuses; do
    census="$mtools/$rel"
    # ⚑ TRACKEDNESS IS REPORTED, NOT USED AS A FILTER. An untracked run file is a live census whose
    # dispatcher has not committed it — every peer reading it by path is already bound by it, and
    # a poll that omitted the row would be silent on the census most likely to be news.
    if (cd "$mtools" && git ls-files --error-unmatch "$rel" >/dev/null 2>&1); then
        printf '  --- %s\n' "$rel"
    else
        printf '  --- %s  ⚑ NOT IN HEAD (dispatched on disk; peers are bound by it anyway)\n' "$rel"
    fi
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
    # ⚑⚑⚑ AND THE SECOND COLUMN IS NOT ALWAYS SPELLED `status` — THIS BLOCK WENT BLIND BECAUSE THE
    # CENSUS IT WATCHES IMPROVED. `build-hermeticity` renamed its §S to `party | state` at rev 27,
    # in the act of REPAIRING its own state vocabulary, and this poll reported it `PRE-FILING` while
    # HEAD held 11 legs. MEASURED: `mdstruct tables` shows `table 8  12 row(s) x 2 col(s)
    # party | state`. ⚑ The freeze of that census is the stated dispatch trigger for TWO held runs
    # (`remaining-work`, `backlog`), so the instrument that fires the trigger could not evaluate the
    # condition, and both would have waited on a reading that never changes.
    # ⚑⚑ FOUND BY `rosettapkg`, FROM OUTSIDE, against my instrument — the third consecutive defect
    # in this poll reported by the party it misinformed rather than by me. A poll is a hand-written
    # population of the shapes its author had seen.
    # ⚑ So the noun is enumerated as a SET and a miss is REPORTED rather than defaulted: defaulting
    # to `party | status` is what turned an unrecognised header into a confident PRE-FILING.
    sig=$("$md" tables "$census" 2>/dev/null \
        | grep -oE '(party|surveyor|repo|leg) \| (status|state)' | head -1)
    # ⚑⚑ AN EMPTY SIGNATURE MUST NOT FALL THROUGH TO `grep ""`, WHICH MATCHES EVERY TABLE AND WOULD
    # REPORT AN UNRELATED TABLE'S ROW COUNT AS THE ROSTER. Three outcomes, not two: recognised /
    # no table at all / ⚑ A TABLE SHAPED LIKE A ROSTER UNDER A HEADER I DO NOT KNOW. The third is
    # the state this poll was silently in for `build-hermeticity`, and it read as the second.
    if [ -n "$sig" ]; then
        # ⚑⚑⚑ A CENSUS MAY CARRY MORE THAN ONE ROSTER-SHAPED TABLE, AND ASSUMING ONE CONCATENATED
        # TWO ROW COUNTS INTO `5\n12`, WHICH REACHED `[` AS A NON-INTEGER. `build-hermeticity` at
        # its freeze carries BOTH `party | state at freeze` (§G's publication, 5 GROUPED rows) and
        # `party | state` (§S's running roster, 12 rows, one party each). Both are correct and §G
        # asks for the first — ⚑ so the poll broke at the exact moment its subject did the right
        # thing, which is the THIRD instrument of mine to degrade that way today (a column renamed
        # during a vocabulary repair; a correction-rate grep defeated by subjects that name the
        # defect rather than the act). `rosettapkg` measured this one.
        # ⚑⚑ THE FIX IS NOT TO PICK ONE BY POSITION OR BY SPELLING. Keying on `state at freeze`
        # would be a fourth guessed literal, and `head -1` would silently prefer whichever table a
        # future edit happens to put first — the positional-predicate defect this block already
        # refuses. The MULTIPLICITY IS REPORTED and the RUNNING ROSTER is taken, because §S is what
        # a filer files into and §G's publication is a summary OF it at one instant.
        _hits=$("$md" tables "$census" 2>/dev/null | grep -c "$sig")
        if [ "$_hits" -gt 1 ]; then
            echo "  ⚑ ${_hits} roster-shaped tables — §G's freeze publication and §S's running"
            echo "    roster both match. Reading §S; §G's is a SUMMARY of it, not a second roster."
            "$md" tables "$census" 2>/dev/null | grep "$sig" | sed 's/^/      /'
        fi
        # ⚑ THE LAST MATCH IS TAKEN, AND THE REASON I FIRST WROTE HERE WAS FALSE. I claimed §G's
        # publication sits above §S. MEASURED: `§S Freeze roster` spans L1355-1435 and `§G The
        # freeze` L1436-1459 — §G comes AFTER, and BOTH matching tables live inside §S. The freeze
        # publication was written into the §S section, so the ordering that makes `tail -1` correct
        # is *summary first, then the per-party roster it summarises*, WITHIN §S.
        # ⚑⚑ THAT IS AN OBSERVED CONVENTION OF ONE RUN FILE, NOT AN INVARIANT, and it is recorded
        # as such: if a census ever publishes its summary below its roster this takes the wrong
        # table — which is why the multiplicity is PRINTED above rather than resolved silently. A
        # reader sees both counts and can tell. That is the residue, stated, not closed.
        _row=$("$md" tables "$census" 2>/dev/null | grep "$sig" | tail -1)
        roster=$(printf '%s' "$_row" | grep -oE '[0-9]+ row' | grep -oE '[0-9]+')
        tbl=$(printf '%s' "$_row" | grep -oE 'table [0-9]+' | grep -oE '[0-9]+')
    else
        roster=''
        tbl=''
        # ⚑ Name the unrecognised headers rather than asserting absence: this is the poll's own
        # absent-versus-unavailable line, and it now prints the evidence a reader needs to widen
        # the set above by MEASUREMENT instead of by another guessed literal.
        _hdrs=$("$md" tables "$census" 2>/dev/null | grep -oE '[a-z-]+ \| [a-z-]+$' | sort -u | paste -sd' · ')
        [ -n "$_hdrs" ] && echo "  ⚑ §S UNRECOGNISED, not absent — two-column headers present: $_hdrs"
    fi
    # ⚑⚑ A CENSUS WITH NO §S TABLE IS PRE-FILING, NOT SHORT-ROSTERED, AND THE POLL SAID SHORT.
    # MEASURED on `CENSUS-build-hermeticity.md` minutes after its dispatch: `§R` carries 9 rows and
    # no status table exists yet, so the roster count read `? of 8` and the branch below reported
    # `the roster is SHORT: a dropped row reads as terminal` — a DELETION claim about a table that
    # was never written. ⚑ That is absent-versus-unavailable inside the instrument that reports it:
    # a missing §S means *nobody has filed yet*, and a short §S means *a row was dropped*. Reading
    # the first as the second manufactures an accusation out of a census's normal opening state.
    if [ -z "$tbl" ]; then
        echo "  no §S status table yet — PRE-FILING, not short-rostered."
        echo "    (a missing §S is 'nobody has filed'; a short §S is 'a row was dropped')"
    else
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
    # ⚑⚑⚑ A `§S` LARGER THAN `§R` IS NOT A SHORT ROSTER, AND TREATING IT AS ONE TURNED A CRASH
    # INTO A WRONG ANSWER. The previous repair fixed the `5\n12` concatenation so this comparison
    # RUNS — and a running comparison then read `build-hermeticity`'s 12 `§S` rows against
    # `expected` = |§R| - 1 = 8 and reported `NOT FROZEN — the roster is SHORT` about a census whose
    # `§V` carries FREEZE CALLED at rev 39. ⚑⚑ **Before: a right answer from a dead predicate.
    # After: a WRONG answer from a live one** — and the second is more dangerous, because it has no
    # crash, no stderr, and nothing to notice. Measured and reported by `cassian-observability`.
    # ⚑ THE IDENTITY `|§S| == |§R| - 1` HELD ONLY WHILE `§S` WAS ONE ROW PER ROSTERED PARTY.
    # `§D` admits late arrivals and `§G` publishes aggregate rows — b-h's 12 is 11 legs plus a
    # `not surveyed` row covering nine unrostered repos, which `§G` defines as NOT A ZERO. So a
    # roster can legitimately EXCEED its `§R`, and only a DEFICIT is evidence of a dropped row.
    if [ "${roster:-0}" -gt "${expected:-0}" ]; then
        echo "  ⚑ §S carries ${roster} rows against §R's ${expected} surveying parties."
        echo "    That is §D admitting late arrivals or §G publishing an aggregate row — an"
        echo "    accounting that GREW, which is not a dropped row. Not blocking the verdict."
    fi
    if [ "${roster:-0}" -lt "${expected:-0}" ]; then
        echo "  NOT FROZEN — and the roster is SHORT: a dropped row reads as terminal"
    elif [ "${pending:-1}" -ne 0 ]; then
        echo "  NOT FROZEN — a party is still non-terminal; the embargo holds"
    else
        # ⚑⚑⚑ THE ROSTER CONDITION IS NECESSARY AND NOT SUFFICIENT. §G is explicit: the freeze
        # is a ROW IN §V reading `FREEZE CALLED`, and a message is a courtesy rather than the
        # event. Measured the moment the roster went terminal: no such row exists and §S's own
        # heading still reads NOT YET CALLED. ⚑ A satisfied precondition read as the event is this
        # repository's own green-over-nothing, in the poll that exists to refuse it.
        # ⚑⚑⚑ `§V` HAS NO ALLOCATOR AND TWO ROWS HAVE COLLIDED TWICE. Rev 12 recorded it —
        # `gabion` filed 10 and `linux-sources` 11 while this dispatcher was writing another 10 —
        # and rev 19 hit it again, `gabion`'s 18 reaching `HEAD` first. **Both were resolved by
        # renumbering BY HAND, and nothing between the two recurrences changed.**
        # ⚑⚑ A FINDING RECORDED TWICE AND NEVER FIXED IS BEING TREATED AS DECORATION. The poll
        # reads `§V` by COLUMN (`--col 2 --starts FREEZE`) and never by row number, so a duplicate
        # index is invisible to it: the log stays STRUCTURALLY VALID and becomes SEMANTICALLY
        # AMBIGUOUS, which is `linux-sources`' formulation and `mdstruct` sees only the first.
        # ⚑ THE DEFECT IS SELF-CLEARING BY MANUAL LABOUR, which is why it survived: by the time
        # anyone looks, whoever noticed has already renumbered. MEASURED on two fixtures before
        # this was written — a table with rows `1 2 2` reports `2`; one with `1 2 3` reports
        # nothing. Both arms, because a duplicate-detector that never fires is a print statement.
        # ⚑⚑⚑ AND THE FIRST VERSION OF THIS READ `mdstruct rows`, WHICH TRUNCATES. MEASURED on
        # the live file the hour after shipping: the detector saw rows `1..18` while the file held
        # `1..21 21` — it stops at an oversized row (`gabion`'s rev 18 is ~4KB of one cell) and
        # never reaches the collision. **It reported CLEAN, four times in one tick, on a file
        # containing exactly the defect it was built for**, and the live duplicate was found by
        # `gabion` running a raw pattern instead.
        # ⚑⚑ THAT IS THE MIS-NAMED-POPULATION DEFECT INSIDE THE INSTRUMENT BUILT TO CATCH IT: the
        # population is *rows in the file*, and `rows` answers *rows this tool chose to print*.
        # ⚑ SO THE REVISION INDEX IS READ FROM THE FILE. The `§V` row grammar is `| N | date |`
        # at line start, which is a LEXICAL fact about the log and not a structural one — the
        # struct-tools rule routes STRUCTURED questions to `mdstruct`, and *is this integer
        # repeated at the start of a line* is not one. `mdstruct` remains the reader for §S, §R
        # and the freeze row, where the question really is about sections and tables.
        # ⚑⚑⚑ A MALFORMED ROW BLINDS EVERY TABLE READER PAST IT, SILENTLY. Rows 18 and 22 carry
        # UNESCAPED PIPES inside code spans, so markdown counts 5 and 6 cells against the table's
        # 4 and `mdstruct rows` stops at the first one. MEASURED on the live file: 20 rows at 4
        # cells, one at 5, one at 6. ⚑ That is how the duplicate detector shipped one tick earlier
        # reported CLEAN on a duplicate that was present — it read a mode that had already stopped.
        # ⚑⚑ AND SILENCE PAST ROW 18 IS INDISTINGUISHABLE FROM A CLEAN READ, which is this
        # repository's dominant defect class. It was found by accident, while checking something
        # else, and nothing would have reported it. So the SHAPE is checked before any count over
        # the table is trusted — a cell count that differs from its siblings is the property, and
        # it needs no knowledge of what the columns mean.
        # ⚑⚑⚑ AND THE SHAPE DISAGREEMENT HAS THREE CAUSES, NOT ONE — `cassian` measured this over
        # 105 tracked files in an independent corpus: 12 anomalies, **three mechanisms**. Nine were
        # a raw pipe inside a cell (this repository's case, and EVERY ONE WAS ALREADY ESCAPED —
        # independent confirmation that escaping does not help). Five were the `||||` spanning-row
        # idiom, DELIBERATE and correct. Two were a genuinely missing cell, an author merging two
        # columns. ⚑⚑ A UNIFORM `fix the pipe` SWEEP WOULD HAVE DAMAGED FIVE AND MISSED NINE.
        # ⚑ THE OVER/UNDER SPLIT ROUTES THE REMEDY AND IS ONE `awk` COMPARISON: a row with MORE
        # cells than its header gained a separator (a raw pipe); one with FEWER lost a cell. The
        # arm still cannot name the cause — it reports a shape disagreement — but it can say which
        # of two remedies is even applicable, which the set alone could not.
        # ⚑⚑⚑ AND AN ESCAPED BACKTICK IN A CODE SPAN TRUNCATES THE STRUCTURAL READER WHILE LEAVING
        # THE CELL COUNT PERFECT. Found by BISECTION after three hypotheses died — pipes (a real
        # defect, repaired, not the cause), length (row 11 is 2325 chars and reads fine), encoding
        # (clean UTF-8 both sides of the boundary). Truncating the offending row at 800 chars read
        # all 27 rows; at 1050 it stopped at 18; the span between held `` `blocked on \`mtools\`` ``.
        # ⚑⚑ MARKDOWN DOES NOT TREAT A BACKSLASH AS AN ESCAPE INSIDE A CODE SPAN, so `\`` ends the
        # span at the backtick and the parser loses every row after it. **Two independent
        # truncation mechanisms lived in one row, each invisible to the instrument the other
        # blinds**: pipes stop field-splitting readers, escaped backticks stop the structural one.
        # ⚑ SO THE CELL-COUNT ARM CANNOT SEE THIS AND SAYS SO. It is a separate check.
        # ⚑ FIXED-STRING (`-F`), NOT A REGEX. The regex form matched every bare backtick and
        # reported 1543 lines where the true count is 1 — a confident wrong number from a pattern
        # that looked right, in the arm added to catch a defect that looked fixed.
        # ⚑⚑⚑ AND THE REACH ARM MEASURES THE CONSEQUENCE DIRECTLY, WHICH EVERY CAUSE-HUNTING ARM
        # ABOVE FAILED TO DO. Rows the structural reader REACHES versus rows PRESENT. It needs no
        # theory of the trigger — pipes, escaped backticks, or whatever combined with them in row
        # 18 that a minimal fixture could not reproduce. ⚑ Three cause hypotheses died tonight and
        # a fourth is necessary-not-sufficient; this one is agnostic and was measured on both arms:
        # the pre-repair blob reads 18 of 27 (TRUNCATED), a clean fixture reads 2 of 2 (ok).
        # ⚑⚑ IT IS THE CHECK THE OTHER ARMS SHOULD HAVE BEEN. A smell arm says *something may be
        # wrong*; this says *the reader stopped early, here, by this many rows.*
        _reach=$("$md" rows "$census" 2>/dev/null | sed -n 's/^  table [0-9]*  \([0-9]*\) | .*/\1/p' | wc -l)
        _present=$(grep -cE '^\| [0-9]+ \|' "$census" 2>/dev/null)
        if [ "${_reach:-0}" -lt "${_present:-0}" ]; then
            echo "  ⚑⚑ THE STRUCTURAL READER STOPS EARLY: reaches ${_reach} of ${_present} numbered"
            echo "    rows. Every row after the stop is INVISIBLE to mdstruct and to anything that"
            echo "    reads through it, while cell counts stay perfect. This measures the"
            echo "    CONSEQUENCE and needs no theory of the cause."
        fi
        _ebt=$(grep -cF '\`' "$census" 2>/dev/null)
        # ⚑⚑⚑ IN A TABLE ROW OR NOT — THE DISTINCTION IS THE WHOLE PREDICTIVE CONTENT, and it was
        # ABANDONED one commit earlier as unsupported because a fixture "failed to reproduce".
        # ⚑ That fixture never ran: a relative path to `mdstruct` broke after a `cd`, four readings
        # came back empty, and an empty reading was taken as a defect not reproducing. **The
        # correct hypothesis was discarded on a tool that was not executing.**
        _ebt_row=$(grep -E '^\|' "$census" 2>/dev/null | grep -cF '\`')
        if [ "${_ebt:-0}" -gt 0 ]; then
            # ⚑⚑⚑ THIS ARM REPORTS A SMELL AND CANNOT ESTABLISH THE CONSEQUENCE, AND ITS FIRST
            # WORDING CLAIMED OTHERWISE. It said the structural reader "loses every table row
            # after it" — asserted of any line carrying `\``. MEASURED: the two lines it fires on
            # in this repository's own `§V` are PROSE, correctly fenced, and all 29 revisions
            # read. ⚑ An arm that warns about a non-defect trains its reader to ignore it.
            # ⚑⚑ AND THE NARROWING I REACHED FOR IS UNJUSTIFIED. A minimal fixture reproducing
            # row 18's construct — a code span containing an escaped span, twice, inside a table
            # row — reads ALL its rows. So the escaped backtick is NECESSARY AND NOT SUFFICIENT,
            # something else in that row combined with it, and what remains unknown. Restricting
            # the arm to table rows would encode a hypothesis no fixture supports.
            # ⚑ SO IT REPORTS WHAT IT MEASURED AND NAMES THE CHECK THAT SETTLES IT. `mdstruct
            # rows` against the file answers the question this arm cannot.
            echo "  ⚑ ${_ebt} escaped backtick(s), ${_ebt_row} of them INSIDE A TABLE ROW."
            echo "    Position decides: in a table row it truncates the structural reader; in"
            echo "    prose it is harmless. MEASURED across three blobs of this file — 49a4f5a"
            echo "    (in row 18, reads 18 of 27) and 057bf13 (in prose, reads 28 of 28), while"
            echo "    RAGGEDNESS came and went across the same pair without changing the reach."
            echo "    ⚑ Invisible to the cell-count arm either way: a truncating backtick leaves"
            echo "      every cell count perfect. The reach arm above is what settles it."
        fi
        _over=$(awk -F'|' '/^\|/{if(!t){t=1;h=NF;next} if(NF>h)c++} !/^\|/{t=0} END{print c+0}' "$census" 2>/dev/null)
        _under=$(awk -F'|' '/^\|/{if(!t){t=1;h=NF;next} if(NF<h)c++} !/^\|/{t=0} END{print c+0}' "$census" 2>/dev/null)
        _cells=$(awk -F'|' '/^\| [0-9]+ \|/{print NF-2}' "$census" 2>/dev/null | sort -u | tr '\n' ' ')
        if [ "$(printf '%s' "$_cells" | wc -w)" -gt 1 ]; then
            echo "  ⚑ ${_over} row(s) OVER their header (a raw pipe added a separator)," \
                 "${_under} UNDER (a cell is missing)."
            echo "    Different causes, different remedies — and the ||||-spanning-row idiom is a"
            echo "    legitimate OVER that must not be 'repaired'. Read the row before acting."
        fi
        if [ "$(printf '%s' "$_cells" | wc -w)" -gt 1 ]; then
            echo "  ⚑ §V ROWS DISAGREE ON CELL COUNT: ${_cells}— a row carries a raw pipe,"
            echo "    usually inside a code span. Every table reader STOPS at the first such row"
            echo "    and reports what it saw as complete. Counts over this table are UNRELIABLE."
            # ⚑⚑ REMOVE THE PIPE — DO NOT ESCAPE IT. `awk -F'|'` and every field-splitting reader
            # split on the RAW BYTE, so `\|` changes rendering and not the split. MEASURED on a
            # fixture: an escaped row still yields 5 cells against 4. The first version of this
            # message said "unescaped pipe", which told a filer that escaping would fix it.
            echo "    ⚑ REMOVE the pipe; escaping it does NOT help — a field-splitting reader"
            echo "      splits on the raw byte and \\| still ends the cell."
            # ⚑ AND THIS ARM ANSWERS *ARE THE SHAPES UNIFORM*, NOT *IS EACH ROW CORRECT*. A peer
            # read `4 5 6` after a failed revert as evidence the revert worked; the file was at
            # 3 cells and the distinct-value set happened to contain the right numbers.
            echo "    ⚑ This reports the SET of shapes. It cannot tell you a given row is correct;"
            echo "      re-measure PER ROW after any repair."

        fi
        _dups=$(grep -oE '^\| [0-9]+ \|' "$census" 2>/dev/null \
            | grep -oE '[0-9]+' | sort -n | uniq -d | tr '\n' ' ')
        if [ -n "$_dups" ]; then
            echo "  ⚑ §V CARRIES DUPLICATE REVISION NUMBER(S): ${_dups}"
            echo "    Two parties allocated one index. The log is structurally valid and"
            echo "    semantically ambiguous; a leg citing that revision cites two rows."
        fi
        if "$md" rows "$census" --col 2 --starts "FREEZE" >/dev/null 2>&1; then
            echo "  ⚑ FROZEN — roster terminal AND §V carries the row. Cross-reading is the point."
        else
            echo "  NOT FROZEN — the roster condition is met, but §V carries no FREEZE CALLED row."
            echo "    That is the coordinator's to declare; a met precondition is not the event."
        fi
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
        # ⚑⚑⚑ THE UNADMITTED CHECK CANNOT SEE THE OTHER DIRECTION, AND ITS SILENCE READ AS
        # AGREEMENT. It finds files with no §S row. It cannot find §S rows that no longer cover
        # the directory — so when `gabion`'s leg went from untracked to COMMITTED, the only signal
        # I had went quiet at the exact moment the disagreement became permanent. MEASURED that
        # tick: `HEAD` held 8 constitution legs, `§S` held 7 rows, and this poll reported
        # `7 of 7 — FROZEN`.
        #
        # ⚑⚑ THAT IS ABSENT-VERSUS-UNAVAILABLE IN THE DETECTOR FOR ABSENT-VERSUS-UNAVAILABLE. I
        # built one direction of a two-sided comparison and read its silence as the two sides
        # agreeing. Third distinct blindness in this poll in three ticks — a hardcoded path, then
        # `tracked` as a cheap key, now a one-sided reconciliation — and each repair made the
        # enumeration better while never asking whether the roster still described the directory.
        #
        # ⚑ NOT AN ERROR EITHER. A count that outgrew its freeze is a fact about an accounting an
        # operator performed, and `§D` forbids amending an accounted roster. The poll's job is to
        # make the divergence VISIBLE rather than to reconcile it.
        n_head=$(cd "$mtools" && git ls-tree -r HEAD --name-only "${legs#"$mtools"/}" 2>/dev/null \
            | grep -vc 'apex')
        if [ -n "${tbl:-}" ] && [ "${tbl:-}" != "-1" ] && [ "${roster:-0}" -gt 0 ] \
           && [ "${n_head:-0}" -ne "${roster:-0}" ]; then
            # ⚑⚑⚑ THE SIGN IS THE DIAGNOSIS, AND ONE SENTENCE WAS SERVING BOTH SIGNS.
            # This arm was built for gabion's late leg, where HEAD EXCEEDS §S, and its prose says
            # so: *an accounting that an admission outgrew.* It then fired on the opposite sign
            # with the same sentence. MEASURED across all three frozen censuses this tick:
            #   constitution      §S 7, HEAD 8   a leg arrived after the freeze     <- prose true
            #   remaining-work    §S 8, HEAD 7   `substrate` FILED ELSEWHERE        <- prose FALSE
            #   build-hermeticity §S 12, HEAD 11 one `filed elsewhere` row          <- prose FALSE
            # ⚑⚑ A CORRECT COUNT UNDER A MIS-NAMED CAUSE PASSES EVERY ARITHMETIC CHECK. The
            # `grep -vc apex` population is right and the subtraction is right; only the sentence
            # was wrong, which is why it survived being read every tick for three ticks.
            # ⚑ THE UNDER-SIGN CAUSE IS CHECKABLE, so the poll checks it rather than narrating:
            # a surveyor whose leg lives in ANOTHER repo is rostered here and absent from this
            # directory BY DESIGN. That is not a dropped row, and it is not an outgrown roster.
            echo "  ⚑ §S DESCRIBES $roster PARTIES AND HEAD HOLDS $n_head LEG(S)."
            if [ "${n_head:-0}" -gt "${roster:-0}" ]; then
                echo "    HEAD EXCEEDS §S: an accounting that an admission outgrew. §D forbids"
                echo "    amending it; this line exists so the divergence is read rather than found."
            else
                _elsewhere=$(sed -n '/^## §S/,/^## §[^S]/p' "$census" 2>/dev/null \
                    | grep -ciE 'filed elsewhere')
                _gap=$((roster - n_head))
                if [ "${_elsewhere:-0}" -ge "${_gap:-0}" ] && [ "${_elsewhere:-0}" -gt 0 ]; then
                    echo "    §S EXCEEDS HEAD, AND IT IS ACCOUNTED FOR: $_elsewhere surveyor(s)"
                    echo "    marked 'filed elsewhere' are rostered here and file into their own"
                    echo "    tree. Absent from this directory BY DESIGN, not a dropped row."
                else
                    echo "    §S EXCEEDS HEAD BY $_gap AND ONLY $_elsewhere ROW(S) SAY WHY."
                    echo "    A rostered surveyor with no leg here and no 'filed elsewhere' mark"
                    echo "    is a DROPPED ROW — the one shape this arm exists to catch."
                fi
            fi
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

# ⚑⚑⚑ THE TERMINAL DIGEST — BECAUSE A CORRECT LINE THE READER NEVER RECEIVES IS NOT A REPORT.
#
# `linux-sources` replied to this repository's furniture rule — *a line that reports zero every
# time stops being read and becomes furniture* — with a variant that sharpens it: **their probe
# prints SIX** and they read past it on six consecutive ticks. ⚑ SO THE OPERATIVE PROPERTY IS
# CONSTANT, NOT ZERO, and a non-zero constant is WORSE, because it looks like the probe is working.
#
# ⚑⚑ THIS TICK PRODUCED A THIRD POSITION NEITHER OF US HELD. Their letter arrived, the inbox arm
# reported it correctly and by name, and this dispatcher still did not see it — because the STEP 0
# invocation was `./blockers.sh | sed -n '/CENSUS-remaining-work/,$p' | head -6`. MEASURED: the
# notice is line 44 of 91; the reader's window opens at line 74. Not furniture and not constant —
# **excluded by construction**, for an unknown number of ticks.
#
# ⚑ AND THE PIPELINE EXISTED NOWHERE IN THE TREE. `grep -rn` over every `.sh` and `.md` finds it
# zero times: it lived only in a turn, which is why nothing could gate it and why the next vantage
# inherits it as a habit rather than as a file. That is §8's B5 exactly — *a handle only survives
# if its referent lives outside the context* — and the repair must therefore BE a file.
#
# ⚑ THE FIX IS NOT A WIDER WINDOW. A window can always be narrowed again by the next reader, and
# widening it treats one reader's slice as the defect rather than the truncation itself. The poll
# instead REPEATS its unread count LAST, where every trailing window reaches it, and states its own
# line count so a reader can tell a truncated read from a complete one WITHOUT trusting its own
# pipeline. A digest that moves is not furniture; a digest that is missing is a detected truncation.
_unread_n=$(find "$mtools/inbox" -maxdepth 1 -name '*.md' ! -name README.md 2>/dev/null | wc -l)
echo "=== DIGEST (repeated last so a trailing window cannot exclude it) ==="
if [ "${_unread_n:-0}" -gt 0 ]; then
    echo "  UNREAD LETTERS: $_unread_n — read them before deriving this tick's list"
else
    echo "  unread letters: 0"
fi
echo "  END OF POLL. If this line is missing, your reader truncated it — the poll did not stop."

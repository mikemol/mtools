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
# ⚑ THE GATE'S LOG DIRECTORY, resolved the same way the gate resolves it, so the poll reads the
# record the gate actually writes rather than a path that merely looks like it.
_witness_logs_probe="${TMPDIR:-/home/mikemol/.cache}/mtools-gate-logs"
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
# ⚑⚑⚑ THIS SECTION WAS A BLOCKER AND IS NOT ONE ANY MORE, AND NOTHING SAID SO. It was carried in
# the symbol set every tick of this session, unmeasured, because it sits under the heading *the
# standing blockers*. MEASURED: it blocks nothing here — the only reference to any island module
# anywhere in this repository is the line below that reports it.
#
# ⚑⚑ THE DEPENDENCY WAS INVERTED AT `6da1021`, whose subject reads *built from the design not the
# modules*. mtools ships its own `mikemol-ratchet`, and the two are not the same code: `core.py`
# here is 325 lines defining six functions against substrate's 193 defining four, ONE NAME SHARED
# OUT OF TEN. That commit's reason: importing untracked modules would vendor a snapshot nobody can
# fetch, which is the anti-pattern this repository exists to retire.
#
# ⚑ SO IT REPORTS A TRUE FACT UNDER A HEADING THAT MADE IT LOOK ACTIONABLE. Thirty-two lines of a
# peer's working state, listed among blockers, trains a reader to scroll past thirty-two lines —
# the furniture rule reached by VOLUME rather than by constancy.
#
# ⚑ KEPT RATHER THAN DELETED: the count is still evidence about a peer this repo consumes from,
# and deleting it would lose the enumeration this block's own comment argues for. What changes is
# that it names its own status.
echo "=== substrate: the ratchet island (reported, not a blocker here) ==="
echo "  mtools ships mikemol-ratchet, interned at 6da1021 from the DESIGN, not these modules;"
echo "  whether substrate tracks them is substrate's call and blocks nothing in this tree."
island=$(find "$sub/substrate" -maxdepth 1 -name 'ratchet*.py' -o -maxdepth 1 -name 'baseline*.py' \
         -o -maxdepth 1 -name 'withheld*.py' 2>/dev/null | wc -l)
echo "  population: $island module(s) match the island's naming on disk"
for f in $(find "$sub/substrate" -maxdepth 1 \( -name 'ratchet*.py' -o -name 'baseline*.py' \
           -o -name 'withheld*.py' \) -printf '%f\n' 2>/dev/null | sort); do
    tracked "$sub" "substrate/$f" "$f"
done

# ⚑⚑⚑ THIS SECTION SITS BESIDE THE ISLAND'S AND HAS A DIFFERENT STATUS, WHICH IS THE POINT OF
# SAYING SO. The island reports a blocker RESOLVED by inversion — mtools built its own ratchet
# from the design. This one is DEFERRED: there is no `membudget/` here, no distribution, and no
# commit deciding it. What exists is `findings/membudget/`, 22 filings from five parties, eight
# of which discuss the keyway the intake plan named as its open design question.
#
# ⚑⚑ COPYING THE ISLAND'S WORDING WOULD HAVE BEEN A FALSE CLAIM. *Not a blocker here* is true
# there and false here: this repository does intend to intern membudget, and what stops it is a
# design question with a named owner rather than an inverted dependency. Reporting deferred work
# as resolved is the FLATTERING direction — the same direction the refusal record undercounted in.
#
# ⚑ A DEFERRAL WITH NO STATED EXIT IS INDISTINGUISHABLE FROM A THING NOBODY LOOKED AT AGAIN, so
# the exit condition is named rather than left to a reader who would have to find eight filings
# to reconstruct it.
#
# ⚑ THE WORD NAMES TWO REFERENTS IN THIS TREE and a hit count would have read as consumers:
# `figure_freshness.sh` mentions membudget twice and both are `findings/membudget/`, the corpus
# here; `mdstruct/pyproject.toml` mentions it twice and both are prose about a hypothetical
# sibling distribution. Neither is substrate's ledger script.
echo "=== substrate: the membudget ledger (DEFERRED here, not resolved) ==="
echo "  mtools intends to intern this; nothing is built yet and no commit decides it."
echo "  The exit is the keyway — declare the KIND (claim:path:, claim:label:), bare tags"
echo "  uncomparable — discussed across 8 of the 22 filings in findings/membudget/."
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
    # ⚑⚑⚑ ONE PROBE WHOSE STATUS IS READ, BEFORE ANY READ WHOSE EMPTINESS WOULD BE INTERPRETED.
    # Every `$md` call below is `2>/dev/null` and reads only stdout, so a reader that RUNS and
    # FAILS returns nothing — byte-identical to a file that legitimately has no such table.
    # ⚑⚑ MEASURED against the real reader, and the states ARE separable by status:
    #     a real census file          rc=0, 5 lines
    #     a markdown file, no tables  rc=0, 1 line   <- the honest empty
    #     an undecodable file         rc=1, 0 lines
    #     a path that does not exist  rc=2, 0 lines
    # The honest empty carries rc=0. Every failure carries a nonzero status, so the discriminator
    # exists and was being thrown away — the `paperkit` arm's defect one level in.
    # ⚑ WHY IT MATTERS HERE SPECIFICALLY: this poll selects every later tick's work. A census whose
    # reader failed would report `0 of 0 parties listed` — a clean-looking line about the census
    # rather than about the read, which is worse than an error because nothing looks wrong.
    # ⚑ ONE GUARD, NOT TEN. Repeating this at every call site is ten places to forget it, which is
    # the lesson `note_failure` in the gate was written for.
    if ! "$md" tables "$census" >/dev/null 2>&1; then
        echo "  ⚑ READER FAILED on this file — mdstruct exited nonzero."
        echo "    Every verdict below would describe the READ, not the census. Skipping it."
        continue
    fi
    # ⚑⚑⚑ THIS NOUN CLASS IS REPEATED AT FOUR SITES AND THREE OF THEM HAD A DIFFERENT ONE.
    # This site read `(party|surveyor|repo|leg)`; lines 817, 820 and 985 read `(surveyor|party)`,
    # dropping `repo` and `leg`. ⚑ AND THE ARM PINNED ONLY THIS ONE — a single assertion that the
    # signature is derived rather than hardcoded, satisfied by the site that was already right, so
    # three quarters of the finders used a narrower predicate than the test checked. An n-of-m
    # whose population is *places I looked* rather than *places the predicate lives*.
    # ⚑⚑ MEASURED HARMLESS TODAY, WHICH IS WHY IT SURVIVED. Across all ten run files this poll
    # reads, both spellings select the same table: no census currently heads its §S with `repo` or
    # `leg`. A divergence that only shows on inputs nothing produces yet is unreachable from
    # output — the first census to head its §S `leg | status` would be found here and MISSED at
    # the three sites below, so the poll would publish a roster from one branch and a vocabulary
    # refusal from another about the same file.
    # ⚑ POSITIVE CONTROL: `leg | why` is a real two-column header in this corpus
    # (findings/CENSUS-deps-build-ANALYSIS.md), so the noun exists here. That file is outside this
    # poll's population by the `grep -v ANALYSIS` above, which is what makes it a control and not
    # a finding.
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
        #
        # ⚑⚑⚑ AND THAT EVIDENCE WAS FABRICATED, IN THE LINE WHOSE ONLY JOB IS TO SUPPLY IT.
        # The regex was `'[a-z-]+ \| [a-z-]+$'` — anchored on the RIGHT and open on the LEFT, so it
        # matched the last two fields of a header of ANY width and reported them as a two-column
        # table. MEASURED on `CENSUS-backlog.md`, whose three tables are 3, 4 and 3 columns wide and
        # not one of which is two: the poll printed `two-column headers present: changed | affects
        # prefix | file` — `changed | affects` being the tail of `rev | when | what changed |
        # affects`, and `prefix | file` the tail of `surveyor | prefix | file`. Neither header
        # exists. On `build-hermeticity` it emitted FIVE, including `substrate | el-openglo` off the
        # tail of a FIVE-column table.
        # ⚑⚑ THE LINE EXISTS TO SEPARATE *UNRECOGNISED* FROM *ABSENT* AND IT MANUFACTURED THE
        # EVIDENCE FOR *UNRECOGNISED*. Its comment invites a reader to widen the signature set from
        # what it prints; doing so would have added `changed | affects` as an §S signature — a
        # header no census has. A guessed literal is at least somebody's observation; this was an
        # artifact of an unanchored match, and it arrived wearing the word MEASUREMENT.
        # ⚑ AND THE VERDICT UNDERNEATH WAS RIGHT. `backlog` really is pre-filing, so the fabricated
        # evidence sat directly above a true conclusion, which is what let it read as consistent.
        # ⚑ THE ANCHOR IS THE `col(s)` MARKER, because that is where the header provably STARTS in
        # this reader's output — a left anchor derived from the format rather than from the header.
        # Both arms measured before this was written: `backlog` (no 2-col table) now prints NOTHING,
        # and `build-hermeticity` prints exactly `party | state`, which IS its §S header.
        # ⚑ RESIDUE, STATED NOT CLOSED: `[a-z-]+` has no space, so `party | state at freeze` (a real
        # two-column header) is not reported. Narrower than a real header — but under-reporting a
        # candidate is a silence, where the old form was a fabrication.
        _hdrs=$("$md" tables "$census" 2>/dev/null | grep -oE 'col\(s\)  [a-z-]+ \| [a-z-]+$' \
            | sed 's/^col(s)  //' | sort -u | paste -sd' · ')
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
    # ⚑⚑⚑ AND THAT `- 1` WAS A HARDCODED POPULATION, RIGHT FOUR TIMES AND WRONG THE FIFTH.
    # `rosettapkg` hosted a census here under §13 and reported, from outside, that their §R holds
    # EIGHT parties while this poll read seven. They offered a candidate cause — a trailing
    # annotation on one row — and did not assert it. MEASURED, the cause is different: five of the
    # six run files carry an apex row in §R and theirs does not, so the constant was a claim about
    # every §R this poll would ever read, made from the four its author had seen.
    # ⚑⚑ THE FOUR EARLIER CENSUSES MADE IT LOOK DERIVED. A constant correct for every file its
    # author has seen is indistinguishable from a measurement until a file arrives from elsewhere,
    # which §13 now guarantees will keep happening.
    # ⚑ AND THE REPORTER DECLINED THE REPAIR THAT WOULD HAVE HIDDEN IT: editing their roster to
    # satisfy this probe would have meant deleting a real party to make a green line.
    _r_rows=$("$md" tables "$census" 2>/dev/null | grep 'surveyor | prefix' \
        | grep -oE '[0-9]+ row' | grep -oE '[0-9]+')
    _r_apex=$("$md" rows "$census" 2>/dev/null | grep -ci apex || true)
    if [ "${_r_apex:-0}" -gt 0 ]; then
        expected=$(( ${_r_rows:-0} - 1 ))
    else
        expected=${_r_rows:-0}
    fi
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
                # ⚑⚑⚑ COUNT THE MARK IN A TABLE CELL, NEVER THE STRING IN A SECTION. This was
                # `grep -ciE 'filed elsewhere'` over a `sed` range and it reported the count as
                # `surveyor(s)`. It counts neither surveyors nor rows: it counts LINES CARRYING A
                # SUBSTRING, over a range that includes every paragraph explaining what the mark
                # is for. MEASURED on `CENSUS-vfs.md`: 11 against a roster of 8, and the file's own
                # §S prose documents walking into it twice while writing that prose.
                # ⚑⚑ A TABLE USED AS AN INSTRUMENT ACCRETES MENTIONS OF ITS OWN TRIGGER — recorded
                # at mdstruct/src/mikemol/mdstruct/tables.py:137, and `rows --where` carries the
                # same lesson in its docstring: *--where asks whether any cell MENTIONS a term,
                # --starts asks whether one column DECLARES it.* The right instrument existed and
                # its documentation was written about this exact failure.
                # ⚑ FOUR PARTIES CONVERGED ON THIS REPAIR INDEPENDENTLY. `vfs_census` scored ten of
                # nineteen rows on prose in comments and string literals before the same fix; its
                # repair was to reach the read through a Call node rather than a text match.
                # Structure, not text, in both cases.
                #
                # ⚑ TWO-ARMED BEFORE IT WAS WRITTEN, because a one-armed test passes a broken-shut
                # gate. On `CENSUS-vfs.md`: intact -> 8 (equals the roster); one surveyor's mark
                # deleted -> 7 (the dropped row IS seen); one sentence of prose mentioning the mark
                # added -> 8 (unmoved). The old grep read 11 / 10 / 12 on those same three.
                # ⚑⚑⚑ ZERO MATCHES EXITS rc=1 AND WRITES TO stderr, so there is no `row(s)` line
                # to capture and the substitution yields EMPTY, not `0`. An empty string then flows
                # into `-ge` as a syntax error or a silent 0 depending on the shell's mood. MEASURED
                # the first time this arm ran: `CENSUS-build-hermeticity.md` printed
                # `§S marks:  (cells declaring the mark, col 1)` — a blank where a number belongs.
                # ⚑⚑ THE `:-0` IS NOT A PAPERING-OVER, BECAUSE THE TWO CASES ARE NOW DISTINGUISHED
                # BELOW. A count of zero and a query that could not run are different facts, and
                # the old arm's grep could not tell them apart either — it just never showed one.
                _elsewhere=$("$md" rows "$census" --col 1 --starts 'filed elsewhere' 2>/dev/null \
                    | sed -n 's/^  \([0-9]\+\) row(s).*/\1/p')
                _elsewhere=${_elsewhere:-0}
                # ⚑⚑⚑ THE MARK'S VOCABULARY IS NOT UNIFORM ACROSS CENSUSES, and only a prefix
                # predicate could reveal it. `CENSUS-build-hermeticity.md` §S says
                # `filed (authored elsewhere under an operator's...)` — the mark inside a
                # parenthetical rather than at the head of the cell. `--starts` correctly reports
                # no match; the old substring grep matched it anywhere and read six phrasings as
                # one. ⚑ A SUBSTRING SEARCH CANNOT DISCOVER THAT ITS TERM HAS DIALECTS, because
                # every dialect satisfies it. This arm names the shortfall instead of absorbing it.
                _anywhere=$("$md" rows "$census" --where 'elsewhere' 2>/dev/null \
                    | sed -n 's/^  \([0-9]\+\) row(s).*/\1/p')
                _anywhere=${_anywhere:-0}
                _gap=$((roster - n_head))
                # ⚑⚑⚑ A GAP IS NOT MADE OF ONE STATE, AND THE ARM COUNTED AS IF IT WERE. `_gap`
                # is every rostered party with no leg in THIS directory — which includes parties
                # that have not filed ANYWHERE. A surveyor who accepted and has not yet written is
                # PENDING; one who declined with a measured reason is TERMINAL. **Neither is a
                # dropped row**, and the arm called both one because it compared the gap against
                # `filed elsewhere` alone.
                # ⚑⚑ REPORTED BY `rosettapkg`, who verified before claiming a pattern: they
                # cross-tabulated every census in this tree that rosters them against what their
                # own HEAD holds, found ONE disagreeing row out of seven adjudicable, and handed
                # over the row rather than a claim about the table. They did not touch this file.
                # ⚑ THE PRECEDENT IS THIS ARM'S OWN UNADJUDICATED BRANCH, one axis over: calling a
                # census this reader cannot parse a dropped row *reports the READER*. Calling a
                # party who has not filed anywhere a dropped row **reports the CALENDAR**.
                #
                # ⚑⚑ THE STATES ARE COUNTED AS A UNION OVER ROWS, NOT SUMMED. `--starts 'filed'`
                # is a PREFIX OF `filed elsewhere`, so summing the probes double-counts — MEASURED:
                # `--starts filed` returns 14 against `build-hermeticity`'s 12-row §S. The probe
                # below asks for rows whose state is NOT the mark and NOT one of the terminal or
                # pending forms; a row matching none of them is the residue this arm exists for.
                _pending=$("$md" rows "$census" --col 1 --starts 'accepted' 2>/dev/null \
                    | sed -n 's/^  \([0-9]\+\) row(s).*/\1/p')
                _pending=${_pending:-0}
                _declined=$("$md" rows "$census" --col 1 --starts 'scoped decline' 2>/dev/null \
                    | sed -n 's/^  \([0-9]\+\) row(s).*/\1/p')
                _declined=${_declined:-0}
                _notyet=$("$md" rows "$census" --col 1 --starts 'not yet filed' 2>/dev/null \
                    | sed -n 's/^  \([0-9]\+\) row(s).*/\1/p')
                _notyet=${_notyet:-0}
                _accounted=$((_elsewhere + _pending + _declined + _notyet))
                # ⚑⚑⚑ FIVE OF EIGHT CENSUSES PUBLISH THEIR OWN STATE VOCABULARY IN A
                # `state | means` TABLE, AND THIS ARM READ NONE OF THEM. The four prefixes above
                # were written by hand from the two files their author was reading. MEASURED, the
                # declared union is far wider: `filed`, `not surveyed`, `retired`, `no response`,
                # `DRAFTED`, `STAGED`, `declined`, `filed (rev n)`.
                # ⚑⚑ TWO OF THE UNSEEN STATES ARE LOAD-BEARING, and one census says so in its own
                # table: `not surveyed` is annotated *⚑⚑⚑ NO — and it READS as a zero. Nobody was
                # asked.* An arm that cannot see it reports the absence of a survey as the absence
                # of a finding — the one confusion this whole poll exists to refuse.
                # ⚑ SO THE VOCABULARY IS READ FROM THE CENSUS rather than extended here. Adding
                # `filed` to the list would repair one file and leave the mechanism: the next
                # census to mint a state would be miscounted the same way, and nothing would say
                # so. A published declaration is the only population that cannot go stale.
                # ⚑⚑⚑ AND `filed` IS NOT ADDED TO THE PROBES, DELIBERATELY, THOUGH IT WOULD TURN
                # `remaining-work`'s seven unnamed rows green. MEASURED: `--starts 'filed'` returns
                # **8 of 8** there — it matches `filed elsewhere` too, because one declared state
                # is a PREFIX OF ANOTHER. Summing per-state probes over a declared vocabulary
                # double-counts, which is the same arithmetic that read 14 against a 12-row table.
                # ⚑⚑ SO THE DECLARED STATES ARE NOT A PARTITION AND CANNOT BE SUMMED. The row
                # count from the table stays the total — one measurement, independent of the
                # probes — and what this detector adds is the DIAGNOSIS a residue needs to be
                # actionable, not a bigger sum that would be wrong in a new way.
                _declared=$("$md" tables "$census" 2>/dev/null \
                    | grep -c 'state | means' || true)
                _declared=${_declared:-0}
                # ⚑⚑⚑ THE TERMS AND THE TOTAL MUST COME FROM DIFFERENT MEASUREMENTS, and this
                # partition did not. Every term above is the same query with a different prefix,
                # and `_accounted` is their sum — so when the four prefixes match nothing, all
                # four terms are 0, the total is 0, and **they agree with each other because they
                # are one failure counted four times.** Printing the terms proves nothing there.
                # ⚑⚑ THE BOUND IS `rosettapkg`'s, ON A RULE THEY HAD JUST TAKEN FROM ME. Printing
                # the operands stops a HIDDEN operand; it does not stop a partition whose terms
                # share a source. Their own figure line read `0 of >=0`, which is true of every
                # population — *a claim that cannot be wrong, wearing the shape of a clean result*.
                # ⚑⚑⚑ AND MEASURING IT FOUND A SECOND DEFECT UNDERNEATH. On
                # `CENSUS-build-hermeticity.md` the four terms are 0 while `--starts 'filed'`
                # returns **14 rows at rc=0** — the reader parses that file perfectly. Every §S row
                # there says `filed`, a terminal state my four prefixes never enumerated because I
                # built them from the two censuses I happened to be reading. **A hand-written
                # vocabulary, in the arm written to repair a hand-written population.**
                # ⚑ SO THE TOTAL IS NOW READ FROM THE TABLE ITSELF rather than summed from the
                # probes: `§S` row count is an independent measurement, and a disagreement between
                # it and the sum is exactly the signal the sum alone cannot produce.
                # ⚑⚑ THE §S TABLE IS FOUND BY SHAPE, NOT BY POSITION. A census may carry a §G
                # freeze summary with a similar header, so the LAST match wins — the poll already
                # documents that §S is the running roster and §G is a summary of it.
                # ⚑⚑⚑ THE SHAPE WAS TWO HAND-WRITTEN ALTERNATIVES AND IT MISSED A CENSUS SILENTLY.
                # `surveyor | status` and `party | state` were written from the files in front of
                # their author; `CENSUS-deps-build.md` heads its §S `party | status | evidence`, a
                # third column neither allows for. **That census printed no `declared:` line at
                # all** — not the classified reading, not the refusal — so a reader saw six censuses
                # answered and one silent, with nothing saying which it was. Absence and unavailable,
                # in the table-finder every downstream figure comes from.
                # ⚑⚑ THE REPAIR IS A PREDICATE, NOT A LONGER LIST: column 0 names a PARTY, column 1
                # names a STATE, and anything after is description. MEASURED against every table
                # header in the corpus — 25 distinct headers — two-armed, 12 of 12.
                # ⚑ THE FALSE-POSITIVE ARM IS THE ONE THAT EARNED THE BOUNDARY. `surveyor | prefix
                # | file` and `party | the hole | resolution` both open with a party word and are
                # NOT §S tables; a widened list would have taken them and classified a roster
                # against a state vocabulary. And `party | state at freeze` is §G — my first
                # expectation listed it as a table to TAKE and the predicate was right to refuse
                # it: taking both would make `last wins` a coin-flip between two tables answering
                # different questions.
                # ⚑⚑⚑ AND THIS FILE ALREADY KNEW. Line 285, written long before the finder existed,
                # says in as many words: *`deps-build`'s §S is `party | status`; `constitution`'s is
                # `surveyor | status`.* The fact was in the script, in prose, above the code that
                # needed it — **a recorded lesson is not an applied one**, measured here for the
                # fifth time in this tree and the first where the record and the defect are in the
                # same file.
                _spos=$("$md" tables "$census" 2>/dev/null \
                    | grep -E '^  table [0-9]*  .*(party|surveyor|repo|leg) \| (status|state)( \||$)' | tail -1 \
                    | sed -n 's/^  table \([0-9]*\)  .*/\1/p')
                _rows=$("$md" tables "$census" 2>/dev/null \
                    | grep -E '^  table [0-9]*  .*(party|surveyor|repo|leg) \| (status|state)( \||$)' | tail -1 \
                    | sed -n 's/^  table [0-9]*  \([0-9]*\) row(s).*/\1/p')
                _rows=${_rows:-0}
                _unmatched=$((_rows - _accounted))
                # ⚑⚑⚑ AND NOW THE DOCUMENT'S OWN VOCABULARY IS ACTUALLY READ, by the mode built
                # for it. The previous tick measured that five censuses publish a `state | means`
                # table, reported that this arm read none of them, and shipped `mdstruct classify`
                # to close it — **and then did not consume it.** A component with full coverage and
                # no caller is *the packager is not a user of its own package*, which is this
                # repository's named defect, demonstrated one tick earlier by a hook carrying 52
                # warrants that `settings.json` invoked nowhere. This is the wiring.
                # ⚑⚑ THE HAND-WRITTEN PROBES ABOVE ARE KEPT, NOT REPLACED, and the reason is that
                # they answer a DIFFERENT question: three censuses publish no vocabulary at all, so
                # a classifier refuses them (rc=2) while the prefixes still say something. Deleting
                # the fallback would trade a blind spot for a hole.
                # ⚑ THE TWO READINGS ARE PRINTED SIDE BY SIDE rather than reconciled here. Where
                # they disagree, that is the finding — and reconciling them in this script would be
                # judgement in the turn rather than a measurement a reader can check.
                # ⚑ ONLY THE RESIDUE IS READ HERE, and only to decide whether to point a reader at
                # the tool. The COUNT is emitted once, ungated, further down — a `_cls_named` was
                # computed here too and became dead when that emission moved, which is the shape
                # this poll keeps producing: a value measured for a caller that no longer wants it.
                _cls_residue=0
                _cls_ok=0
                _cls_accounted=0
                if [ -n "${_spos:-}" ]; then
                    _cls=$("$md" classify "$census" --table "$_spos" 2>/dev/null || true)
                    if [ -n "$_cls" ]; then
                        _cls_ok=1
                        _cls_residue=$(printf '%s\n' "$_cls" \
                            | sed -n 's/^ *\([0-9]*\)  ⚑ UNCLASSIFIED.*/\1/p')
                        _cls_residue=${_cls_residue:-0}
                        # ⚑⚑⚑ THE ROWS CARRYING A STATE THE CENSUS ITSELF DECLARES — the same
                        # quantity `_accounted` estimates with four hand-written prefixes, read
                        # from the document instead. MEASURED: two censuses printed
                        # `0 = 0+0+0+0` over §S tables of 8 and 12 rows and reached NO VERDICT,
                        # while their own vocabularies partitioned those rows without residue.
                        # ⚑⚑ AND THE PREFIXES WENT STALE BY MY OWN HAND. This session rewrote
                        # `CENSUS-vfs.md`'s §S to `filed` / `no leg yet`; the prefixes say
                        # `filed elsewhere`, `accepted`, `scoped decline`, `not yet filed` and
                        # match none of it. A hand-written vocabulary made stale by its author's
                        # edit, inside the arm built to catch stale hand-written vocabularies.
                        _cls_total=$(printf '%s\n' "$_cls" \
                            | sed -n 's/^  \([0-9]*\) row(s) classified.*/\1/p')
                        _cls_accounted=$(( ${_cls_total:-0} - _cls_residue ))
                    fi
                fi
                # ⚑⚑⚑ EVERY COMPONENT OF THE ASSERTED EXPRESSION IS PRINTED, NOT JUST ITS VERDICT.
                # The old branch asserted `_elsewhere >= _gap` and printed only `_elsewhere`, so a
                # reader got a conclusion with one operand invisible and no way to check the
                # comparison that produced it. THAT IS WHY THE WRONG POPULATION SURVIVED: the
                # number on screen was not the number doing the work.
                # ⚑⚑ A PRINTED EXPRESSION IS A PROOF-CARRYING ARTIFACT — or a disproof-carrying
                # one, which is the half that matters: a reader can falsify it from the line alone,
                # without re-deriving anything. An asserted verdict with hidden operands can only
                # be trusted or doubted.
                echo "    §S marks: $_elsewhere (col-1 cells DECLARING it; $_anywhere mention it anywhere)"
                echo "    gap:      $_gap = roster $roster - HEAD legs $n_head"
                echo "    states:   $_accounted = $_elsewhere filed + $_pending pending + $_declined declined + $_notyet not-yet"
                # ⚑ THE INDEPENDENT SECOND SOURCE, PRINTED BESIDE THE SUM. `§S` holds this many
                # rows; the probes classified that many. The remainder is states this arm's
                # vocabulary does not know — a fact about THIS READER, and it is now visible
                # rather than absorbed into a zero.
                echo "    §S rows:  $_rows measured; $_unmatched carry a state these probes do not name"
                # ⚑⚑⚑ THE SECOND SOURCE, PRINTED — IT WAS COMPUTED AND DISCARDED. `_cls_named` is
                # the DOCUMENT-relative count: §S read against the states this census declares,
                # by the mode built for it. It was measured for every census with a §S and only a
                # conditional pointer to re-run the tool by hand was ever emitted.
                # ⚑⚑ WHICH IS THE DEFECT THE COMMENT TWENTY LINES UP NAMES, ONE LEVEL IN. That
                # block argues shipping `classify` and not consuming it is *the packager is not a
                # user of its own package*, adds the wiring — and then drops the wired value
                # before the report. A computed value nothing prints is a caller that does not
                # consume its own call.
                # ⚑⚑⚑ AND IT IS THE HALF THAT SAVES THE PARTITION. The four terms above are one
                # query with four prefixes: when the prefixes miss, all four read 0, the total
                # reads 0, and they agree BECAUSE THEY ARE ONE FAILURE COUNTED FOUR TIMES.
                # MEASURED the tick this line was added: `vfs` and `build-hermeticity` both
                # printed `0 = 0 + 0 + 0 + 0` over §S tables of 8 and 12 rows while the document's
                # own vocabulary named 8 of 8 and 11 of 12. Printing the operands cannot detect
                # that; a term from a DIFFERENT source can.
                # ⚑⚑⚑ AND THE EMISSION THAT WAS HERE WAS GATED, WHICH IS THE DEFECT THE HOISTED
                # BLOCK BELOW EXISTS TO PREVENT — added one tick after that hoist, inside the
                # branch it was hoisted out of. `deps-build` and `constitution` AGREE on totals,
                # so this whole block is skipped and neither printed a `declared:` line: the four
                # censuses that did print one were exactly the four that DIVERGE, which reads as a
                # property of those censuses and is a property of the branch.
                # ⚑⚑ IT WAS ALSO A DUPLICATE MEASUREMENT. `_cls_named`/`_cls_residue` here and
                # `_vt`/`_vr` below are the same `classify` call on the same table; two readings of
                # one source are not two sources, and keeping both would have made a reader think
                # the poll had corroboration it does not have. The second-source FRAMING moved
                # down to the ungated line; the computation here is gone rather than re-emitted.
                # ⚑ THE DOCUMENT'S OWN READING, BESIDE THIS ARM'S. `classify` groups §S against the
                # states the census declares; a residue there is a state the document USES and never
                # DECLARED, which is a finding about the census rather than about this reader — the
                # inverse of the line above it, and the pair is why both are printed.
                # ⚑ THE `declared:` LINE MOVED OUT OF THIS BRANCH, and only the residue POINTER
                # stays — the count is now printed for every census below, diverging or not, so
                # emitting it here too would report one census twice and the rest once.
                if [ "${_cls_ok:-0}" -eq 1 ] && [ "${_cls_residue:-0}" -gt 0 ]; then
                    echo "    ⚑ a row using a state the census never declared is the one thing"
                    echo "      only that reading reveals — mdstruct classify" \
                         "$(basename "$census") --table $_spos"
                fi
                # ⚑ AND WHETHER THE CENSUS PUBLISHED ITS VOCABULARY IS ITSELF THE DISCRIMINATOR.
                # An unmatched row in a census that DECLARES its states is this reader failing to
                # read a published list; an unmatched row in one that declares nothing is a state
                # nobody wrote down. Different repairs, and the arm could not tell them apart.
                if [ "${_unmatched:-0}" -gt 0 ] && [ "${_declared:-0}" -gt 0 ]; then
                    echo "    ⚑ this census PUBLISHES a state|means table and $_unmatched row(s)"
                    echo "      still went unnamed — the vocabulary is declared and unread."
                fi
                # ⚑ THE THIRD OUTCOME, AND IT IS NOT A FAILURE. When no cell declares the mark but
                # some row mentions it, this reader cannot adjudicate the file — that is INVALID,
                # not FALSE, and reporting it as a dropped row would be a statement about the
                # reader dressed as a finding about the census. The same three-state discipline
                # this fleet applies to lease identity and to absence claims.
                # ⚑⚑ THE VOCABULARY-GAP BRANCH COMES FIRST, because it explains the others.
                # If §S holds rows and NONE of them classified, the arm is reading a dialect it
                # does not know — and every downstream figure is 0 for that one reason. Reporting
                # a dropped row there would be *the reader described as the file*, which is the
                # same three-state discipline UNADJUDICATED already applies one axis over.
                # ⚑⚑⚑ WHEN THE PREFIXES REACH NOTHING AND THE DOCUMENT'S OWN STATES REACH
                # EVERYTHING, THE DOCUMENT WINS — and the line says which instrument answered.
                # A verdict that silently switched sources would print two different measurements
                # under one label, which is the manufactured corroboration this poll refuses
                # elsewhere. The prefixes are a READER's vocabulary; the declared states are the
                # FILE's, and only the second can be stale-proof.
                if [ "${_rows:-0}" -gt 0 ] && [ "${_accounted:-0}" -eq 0 ] \
                   && [ "${_cls_accounted:-0}" -ge "${_gap:-0}" ] && [ "${_cls_accounted:-0}" -gt 0 ]; then
                    echo "    ACCOUNTED by declared states: $_cls_accounted >= $_gap — the four"
                    echo "    prefixes above matched nothing, and this census's OWN vocabulary"
                    echo "    explains every rostered surveyor without a leg here. None is dropped."
                elif [ "${_rows:-0}" -gt 0 ] && [ "${_accounted:-0}" -eq 0 ]; then
                    echo "    UNCLASSIFIED: $_rows §S row(s) and 0 matched any state this arm"
                    echo "    names. The terms below would all read 0 for that ONE reason, so"
                    echo "    their agreement is not evidence. Extend the vocabulary or read §S."
                elif [ "${_elsewhere:-0}" -eq 0 ] && [ "${_anywhere:-0}" -gt 0 ]; then
                    echo "    UNADJUDICATED: 0 cells declare the mark, $_anywhere mention it. This"
                    echo "    census phrases the mark differently — a prefix reader cannot settle"
                    echo "    it, and calling it a dropped row would report the READER, not the file."
                elif [ "${_accounted:-0}" -ge "${_gap:-0}" ] && [ "${_accounted:-0}" -gt 0 ]; then
                    # ⚑⚑⚑ THIS VERDICT SPENT THE ONE READING THIS POLL DECLARES IT CANNOT MAKE.
                    # It said *filed elsewhere, STILL PENDING, or terminally declined*. `accepted`
                    # is a PAST-TENSE DOCUMENT STATE; `still pending` is a PRESENT-TENSE CLAIM
                    # ABOUT A PARTY — and this script's own `NOT COVERED: peer reachability` line
                    # says liveness is unreadable here. The disclosure was published and the
                    # defect kept.
                    # ⚑⚑ MEASURED ACROSS A FLEET RESTART, 09-08 to 09-10: `CENSUS-paperkit-use`'s
                    # §S is BYTE-IDENTICAL while `summit`, `linux-sources`, `substrate` and
                    # `paperkit` all went away, `summit` still reading `accepted, not yet filed`.
                    # A roster CANNOT move when a party stops existing, so its stale state and its
                    # fresh state are byte-identical — the equality this file's opening refuses.
                    # ⚑ THE REPAIR DOES NOT ADD A LIVENESS READ, which is impossible here. It
                    # stops ASSERTING one: the row carries a state, and whether the party is still
                    # working is a separate question this poll does not answer. `rosettapkg` is
                    # `not yet filed` by a departed dispatcher — neither pending nor terminal, and
                    # no vocabulary here has a state for that.
                    echo "    ACCOUNTED: $_accounted >= $_gap — every rostered surveyor without a"
                    echo "    leg here carries a state that explains it: filed elsewhere, accepted"
                    echo "    and unfiled, or terminally declined. None is a dropped ROW."
                    echo "    ⚑ A STATE IS NOT A LIVENESS. These are the document's words as"
                    echo "      written; whether each party is still running is NOT COVERED here"
                    echo "      (see the reachability line) — run ListAgents against this roster."
                else
                    echo "    DROPPED ROW: $_accounted < $_gap — $_gap surveyor(s) have no leg here"
                    echo "    and only $_accounted carry any state at all. A rostered surveyor with"
                    echo "    neither a leg nor a state is the one shape this arm exists to catch."
                fi
            fi
        fi
        # ⚑⚑⚑ THE VOCABULARY READING BELONGS OUTSIDE THE DIVERGENCE BRANCH, AND I PUT IT INSIDE.
        # Everything above runs only when `§S` and HEAD DISAGREE, which is right for a divergence
        # diagnosis and wrong for a classification. `CENSUS-deps-build.md` has 7 rostered and 7
        # legs in HEAD, so it AGREES, so the block was skipped and that census printed **no
        # `declared:` line at all** — not the reading, not the refusal.
        # ⚑⚑ I NAMED THE WRONG CAUSE FOR A TICK. The symbol I carried said the §S table-finder
        # missed `party | status | evidence`, and it did — the finder is now a measured predicate,
        # two-armed, 12 of 12 — **but that was never why deps-build was silent.** A census can
        # agree on totals and still use a state it never declared; those are independent questions
        # that happened to share a branch, and fixing the finder alone would have left the silence.
        # ⚑ A READER WHO SEES SIX ANSWERS AND ONE SILENCE cannot tell whether the seventh was clean
        # or unreached — absence-versus-unavailable, in the accounting every downstream figure of
        # this section comes from. So the reading is emitted for every census that has a §S.
        _vpos=$("$md" tables "$census" 2>/dev/null \
            | grep -E '^  table [0-9]*  .*(party|surveyor|repo|leg) \| (status|state)( \||$)' | tail -1 \
            | sed -n 's/^  table \([0-9]*\)  .*/\1/p')
        if [ -n "${_vpos:-}" ]; then
            _v=$("$md" classify "$census" --table "$_vpos" 2>/dev/null || true)
            if [ -n "$_v" ]; then
                _vr=$(printf '%s\n' "$_v" | sed -n 's/^ *\([0-9]*\)  ⚑ UNCLASSIFIED.*/\1/p')
                _vr=${_vr:-0}
                _vt=$(printf '%s\n' "$_v" | sed -n 's/^  \([0-9]*\) row(s) classified.*/\1/p')
                # ⚑⚑ THIS IS THE SECOND SOURCE, AND SAYING SO IS THE POINT OF THE LINE. The four
                # state terms above are one query run with four prefixes, so when the prefixes miss
                # they all read 0 and agree with each other — one failure counted four times, which
                # printing the operands cannot detect. This count comes from the DOCUMENT's own
                # declarations, so a disagreement between the two is a real reading rather than a
                # restatement.
                echo "  §S vocabulary: $(( ${_vt:-0} - _vr )) of ${_vt:-0} row(s) match a state" \
                     "this census publishes; $_vr do not — a SECOND source, not the prefixes above"
            else
                # ⚑ REFUSAL, NOT A ZERO. A census publishing no vocabulary cannot be read against
                # one, and reporting that as `0 matched` would be this reader's blindness wearing
                # the shape of a finding about the census.
                echo "  §S vocabulary: this census publishes no state|means table, so its §S" \
                     "cannot be read against its own declarations — the prefix terms are then the" \
                     "ONLY reading, and they share one source"
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
# ⚑⚑⚑ THE SYMBOLS CARRIED BETWEEN TICKS HAD NO RE-DERIVATION PROCEDURE, WHICH IS THE DEFECT THIS
# FILE'S OPENING COMMENT NAMES. It fixed the remembered-list problem for filesystem blockers and
# left the tick's own carried set hand-written — the reified population, one level out.
#
# ⚑⚑ MEASURED, AND TWO HAD ALREADY DRIFTED. The vacuity sweep's inline-path gap was carried as
# *one instance fixed* and reads FOUR; the refusal record was carried as *two ragged rows* and
# reads THREE OF SEVEN. Both were re-stated from memory every tick and neither was re-read.
#
# ⚑ THE SYMBOLS THAT DISSOLVED THIS WEEK WERE ALL POLLED ONES — paperkit, the island, the ledger.
# They dissolved because this script re-printed them until someone asked what they blocked. An
# unpolled symbol has no such pressure, so the four that rotted are exactly the four never printed.
echo "=== carried symbols: the ones no filesystem section re-derives ==="
# ⚑⚑⚑ THE ANNOUNCEMENT OF THE FIX WAS HALF THE EVIDENCE THAT IT WAS UNFIXED. This probe grepped
# the file for the phrase `named at the freeze`, which survives in every retrospective description
# of the state it names — including the `§V` row RECORDING that the slot was filled, which quotes
# the old wording to say it changed. So the slot could not be observed as filled while its own
# revision row existed, and the poll reported it unfilled while `§R` read `mtools`.
#
# ⚑⚑ THAT IS `table_rows`' OWN `--starts` LESSON, WHICH THIS POLL HAD AVAILABLE AND DID NOT APPLY:
# *a fix and its announcement necessarily discuss the thing being fixed, so a table used as an
# instrument ACCRETES MENTIONS OF ITS OWN TRIGGER, and every repair adds one.* A phrase cannot
# distinguish a state from a report of that state.
#
# ⚑ REPORTED BY `rosettapkg`, who touched neither file — `§R` is this tree's accounting and this
# script is its instrument — and who supplied the discriminator from their own tree: key on
# POSITION rather than wording, because a roster row's identity is its place in a table. Their
# ragged-row arm keys on a cell count differing from its own header's, which no prose can imitate.
#
# ⚑⚑ AND THE SLOT IS READ FROM ITS ROW'S FIRST CELL. `--col 1 --starts` anchors on the PREFIX of
# the prefix column, so the row is found by what it IS rather than by how it is worded — which
# also survives someone rewording the slot.
# ⚑ THE DENOMINATOR LINE IS THE TOOL'S, NOT A ROW. `mdstruct` prints its count with every mode —
# deliberately, so an empty result cannot read as a tool that failed — and a caller splicing raw
# output into its own report leaks that line. Kept out by taking only rows, and the count is not
# lost: an empty `$_apex_row` is the UNMEASURED branch below.
_apex_row=$("$md" rows "$mtools/findings/CENSUS-remaining-work.md" \
            --col 1 --starts 'AX-' 2>/dev/null | grep '^  table ' || true)
if [ -z "$_apex_row" ]; then
    echo "  apex slot: UNMEASURED — no roster row carries the AX- prefix."
    echo "    That is a fact about this reader or a moved roster, not about the naming."
elif printf '%s' "$_apex_row" | grep -q 'named at the freeze'; then
    echo "  apex slot: unfilled — the roster row still reads 'named at the freeze'"
else
    # ⚑ THE PARTY IS THE ROW'S FIRST CELL, and `rows` truncates cells to its own display width —
    # a reader's formatting, not the artifact. So the name is taken and the annotation dropped
    # rather than printing a cell cut mid-word, which would read as a party named `operato`.
    printf '  apex slot: NAMED — %s\n' \
        "$(printf '%s' "$_apex_row" \
           | sed 's/.*table [0-9]*  //; s/ | .*//; s/ —.*//; s/[[:space:]]*$//')"
fi
_rt="$_witness_logs_probe/REFUSALS.tsv"
if [ -r "$_rt" ]; then
    # ⚑⚑⚑ TWO SHAPES, NOT ONE, AND ONE SENTENCE DESCRIBED BOTH. The count has been right since a
    # field count corrected it from a remembered two to a measured three; the CAUSE attached to it
    # was still wrong. Read rather than counted:
    #   3 fields — no session id AND no gate name: genuinely pre-schema, unattributable
    #   4 fields — HAS a session id, missing only the gate name: attributable to a SESSION, and
    #              the gap is WHICH GATE refused
    # ⚑⚑ *pre-column rows are unattributable* is true of the first shape and false of the second.
    # A reader acting on it looks for a missing attribution that is present, and misses the
    # missing gate name that is the actual gap. A correct count under a mis-named cause, one layer
    # down from the correct count this figure already produced once.
    _preschema=$(awk -F'\t' 'NF<4' "$_rt" | grep -c . || true)
    _nogate=$(awk -F'\t' 'NF==4' "$_rt" | grep -c . || true)
    _rows=$(grep -c . "$_rt" || true)
    # ⚑ AND THE SUBJECT IS NAMED. This record lives in a host-local cache, not the repository, so
    # NO COMMIT CAN MOVE IT — which is why the numerator sat static across many ticks while it was
    # re-derived as a carried blocker each time. A reader watching it for movement is watching an
    # artifact this repository does not write.
    echo "  refusal record (host-local cache; no commit moves this): $_rows row(s)," \
         "$_preschema pre-schema (no session id, no gate — unattributable)," \
         "$_nogate attributable to a session but not to a gate"
else
    echo "  refusal record: absent on this host — a fact about the reader, not the record"
fi
# ⚑⚑⚑ THIS LINE ONCE COUNTED WITH A REGEX AND REPORTED 4 WHERE THE SWEEP MEASURES 23. The regex
# matched ONE syntactic form, `(_CONST / "a")`; the sweep's predicate is any `read_text` receiver
# that is not a mapped NAME, which also covers bare names outside the map. A correct-looking
# figure over a mis-named population — reported by the instrument built to refuse exactly that.
# ⚑ SO THE POLL ASKS THE SWEEP rather than re-deriving with a second, weaker predicate. Two
# instruments computing one figure two ways is how they come to disagree without either noticing.
# ⚑⚑⚑ AND THEN THIS LINE PRINTED A BOUND AND CALLED IT A READING. `_MAX_UNRESOLVED` is a
# HAND-TYPED CONSTANT — what someone declared the sweep MAY report — while the sweep computes
# `len(unresolved)` and asserts only `<=` between them. The sentence *ceiling read from the sweep
# itself* promised a measurement over a literal, and the grep above is a grep for that literal;
# the sweep never runs here.
# ⚑⚑ MEASURED, by forcing the ceiling to -1 so the sweep's own assertion prints its set:
# ceiling 21, actual 21. EQUAL TODAY — because the ceiling was last lowered until it touched the
# count — which is exactly why nothing noticed. The next test the sweep resolves drops the count
# to 20 while this line keeps printing 21, indistinguishable from correct.
# ⚑⚑ AND THE ARM REQUIRED IT: `test_the_poll_reports_the_sweeps_own_figure` asserts the string
# `_MAX_UNRESOLVED` appears here, under a comment reading *THE PROPERTY IS THAT THE FIGURE COMES
# FROM THE SWEEP*. Satisfied by, and only by, reading the ceiling.
# ⚑ b98f14b's DEFECT TWO COMMITS LATER, in this file: a typed figure reprinted every tick. There
# it was a sum; here a bound wearing a measurement's sentence.
# ⚑ DERIVING IT IS REFUSED, NOT OVERLOOKED. `len(unresolved)` costs a full pytest run per poll
# invocation, on a script whose process starts are already a measured cost. A bound reported AS a
# bound is a TRUE statement; what was false was the claim to have read it. So the figure stays and
# the sentence changes, and the command that yields the real count is printed for a reader who
# wants it.
_unres=$(grep -oE '^_MAX_UNRESOLVED = [0-9]+' "$mtools/hooks/tests/test_bar_fires.py" \
         | grep -oE '[0-9]+' || true)
echo "  vacuity sweep CEILING: ${_unres:-?} — the declared bound, NOT a count of what the sweep"
echo "    resolves today. The sweep asserts len(unresolved) <= this. To measure the actual:"
echo "      env -C hooks .venv/bin/python3 -m pytest tests/test_bar_fires.py -k vacuous"
echo "    with _MAX_UNRESOLVED forced negative, so the assertion prints its own set."

# ⚑⚑⚑ THE REMOTE SWEEP CANNOT BE TAKEN WHOLE, AND THE CAUSE IS ONE DECLARED INPUT. Measured across
# two ticks: every `lost inputs with digests` failure under `--config=remote` is in
# `mdstruct/BUILD.bazel`, and bazel retries until it exhausts them. ISOLATED ON ONE AXIS:
#
#     hooks + fence + ratchet   (27 targets, no pandoc)   27/27 PASS, 46 remote actions
#     mdstruct ruff/mypy/ratchet (3 targets, no pandoc)    3/3  PASS
#     mdstruct test_*           (16 targets, pandoc)       FAULT on every attempt
#
# The distinguishing input is `@pandoc//:bin` — 156 MB, staged into all 16 and none of the others.
# ⚑⚑ I CALLED THIS INFRASTRUCTURE NOISE ONE TICK AGO, from the true observation that a DIFFERENT
# target fails each attempt. True, and it pointed at *random* when the pattern is one package and
# one input: the failing target is just whichever was scheduled when the blob went missing. A
# plausible reading of a real measurement, aimed at the wrong subject.
# ⚑ THE DECLARATION ITSELF IS CORRECT AND IS NOT THE DEFECT. `MODULE.bazel` stages pandoc because
# 54 of 97 mdstruct cases were SILENTLY SKIPPING without it; undeclaring it to make the sweep green
# would restore a suite that reports green over cases that never ran. The fault is the cache's
# handling of a large blob, not the input's presence.
# ⚑ DERIVED RATHER THAN TYPED, because a status word is what rotted twice in the entry below. What
# is cheap here is the blob's existence and size; whether the cache serves it today is a sweep.
#
# ⚑⚑⚑ AND THE FIRST FORM OF THIS PROBE REPORTED `0 MB` — A PATH THAT NAMED THE WRONG FILE, for the
# fourth time in this repository. It globbed `*+pandoc/bin/pandoc` with `-quit`, which stops at
# whichever match the TRAVERSAL reaches first — and every mdstruct test's runfiles tree carries a
# 114-byte SYMLINK at exactly that path. 114/1048576 truncates to 0. The real binary is matched
# too; it simply was not first, and `-quit` cannot say which it took.
# ⚑⚑ MY OWN F-ARM PASSED AND COULD NOT HAVE CAUGHT IT: it tested the ABSENT case (no cache -> "NOT
# FETCHED") and never the present one, so it proved the probe fails safe while the direction that
# mattered went unmeasured. An arm that tests one direction passes a probe that is wrong in the
# other — this file's own two-armed discipline, violated by the hand that wrote it down.
# ⚑ ANCHORED ON `external/` — where the repo rule materialises the download — and taking the MAX
# rather than the first, so a stray small match cannot win by being reached earlier.
_pbin=$(find "$HOME/.cache/bazel" -path '*/external/*+pandoc/bin/pandoc' -printf '%s\n' 2>/dev/null \
        | sort -n | tail -1 || true)
echo "  remote sweep: the large declared input is $(if [ -n "$_pbin" ]; then echo "$((_pbin / 1048576)) MB"; else echo "NOT FETCHED here"; fi) (@pandoc//:bin,"
# ⚑⚑⚑ AND THE LINE THAT STOOD HERE SAID *A WHOLE-TREE REMOTE GREEN IS NOT CURRENTLY OBTAINABLE*,
# WHICH IS FALSE — MEASURED ONE TICK AFTER I WROTE IT, by running the sweep I had declared
# impossible. `bazel test //... --config=remote --nocache_test_results`: the fault hit
# `//mdstruct:test_frontmatter` on attempt one, bazel retried on its own, and attempt two executed
# all 46 with 81 remote actions and zero faults.
# ⚑⚑ `lost inputs` IS A RETRYABLE CONDITION AND BAZEL'S OWN RETRY IS THE MECHANISM. I read *faults
# on some attempt* as *cannot complete* — the second tick running in which the wrong subject was my
# own characterisation of these failures. Previously I called them RANDOM when they were localised
# to one input; then I called them FATAL when they are transient. Each reading was drawn from a
# true observation and pointed one step past it.
# ⚑ THE LOCALISATION STILL HOLDS and is the useful half: the fault is always in the pandoc-staging
# set, never elsewhere. What changes is the prescription — retry, do not partition.
echo "    staged into all 16 mdstruct test targets and no others). Every remote lost-input"
echo "    fault measured so far is in that set; the other 30 targets never fault."
echo "    ⚑ THE FAULT IS TRANSIENT, NOT FATAL: bazel retries a lost input on its own and the"
echo "    sweep then completes. Measured 46/46 with 81 remote actions on attempt two. So run"
echo "    the whole tree and let it retry:"
echo "      bazel test //... --config=remote --nocache_test_results"
echo "    ⚑⚑ AND --nocache_test_results IS NOT OPTIONAL: without it a sweep reports 'Executed 0"
echo "    out of 46' from cache, which measures the cache rather than the executor."

# ⚑⚑⚑ AN OPERATOR DECISION MUST NAME WHO RAISED IT, AND ONE OF THREE HAD NOBODY. The operator
# asked *why are we concerned about cost?* and there was no answer: the only commit raising the
# gate-cost question is `614163d`, MINE, and its own finding is that no stable quantity exists —
# four runs on an unchanged tree read 132s, 88s, 65s, 61s, converging as the action cache warmed
# while three checkers were ADDED. The measurement dissolved the question it was then listed under.
#
# ⚑⚑ AND NOTHING RECORDED A CONSEQUENCE. No refused commit, no bypass, no complaint that the gate
# is unaffordable. A decision with no consequence and no petitioner is not blocked on anyone; it
# is a measurement promoted to a standing ask, re-derived every tick as though the promotion were
# a fact. THE DEFECT IS THE PROMOTION, NOT THE FIGURE — `614163d` is sound, and its range stated
# with conditions is the honest form.
#
# ⚑ SO THE PETITIONER IS A COLUMN. A self-raised measurement and a request someone made are
# otherwise byte-identical in the symbol set, and one of them is not blocked at all.
echo "=== operator decisions carried, and who raised each ==="
# ⚑⚑⚑ DISCHARGED 2026-09-11 AT f7d92c9, AND THE ENTRY OUTLIVED ITS OWN DECISION BY ONE TICK.
# `ANSWERED: adopt` was true from 2026-09-07 until the last distribution was paid; the moment
# `NOT ARMED` derived to `none`, everything printed beneath it — the measurement recipe, the
# ordering rule, the RUF105 chain caveat — became live-voice guidance for an empty population.
# `Code form holds in the NOT ARMED ones` was advice about a set with no members.
# ⚑⚑ THE FOURTH ROT ON THIS ENTRY, AND THE FIRST THAT THE DERIVATION COULD NOT CATCH. The figure
# rotted twice, `BLOCKED` once, the distribution list once — each a FIELD, each repaired by
# deriving it. This one is the entry's CONTINUED EXISTENCE in the present tense, which no field
# derivation reaches: the ARMED line was correct on the tick the block around it went obsolete.
# ⚑ SO THE SHAPE FOLLOWS THE `cassian's hook components` PRECEDENT BELOW — DISCHARGED, a date, a
# commit, and the measurement that mattered. Every comment in this block is KEPT: they record
# three separate stale-record defects measured in this very entry, and they are invisible to the
# poll's output, so they cannot rot the way an `echo` does.
echo "  RUF201 rule-name autofix   raised by mtools   DISCHARGED 2026-09-11 at f7d92c9"
# ⚑⚑⚑ AND THE ADOPTION HAS A PRECONDITION THE FIRST ATTEMPT DISCOVERED. Applying the autofix
# renamed 26 selectors and made EVERY ruff target exit 2: *Invalid selector … Selecting rules by
# name requires preview mode*. The gate runs `ruff check` with no `--preview`, so a renamed config
# is unloadable by the checker that gates this tree. Reverted; nothing shipped.
# ⚑⚑ SECOND RULING 2026-09-08: take tree-wide `--preview` FIRST, then rename. Measured paydown,
# three separate runs rather than one figure: hooks 41 + mdstruct 55 + ratchet 11 = 107.
# ⚑ ALL 107 ARE ALREADY RATCHET BASELINE KEYS — the ratchet runs preview and tolerates them. Arming
# the GATE with `--preview` converts 107 tolerated findings into hard failures, because the gate's
# ruff has no baseline. So the paydown precedes the arming, or the gate blocks the commits that
# would clean it.
# ⚑⚑⚑ THE FIGURE WAS TYPED HERE AND REPRINTED EVERY TICK, THREE OFF. It read `hooks 41 +
# mdstruct 55 + ratchet 11 = 107`; measured two ticks after a paydown moved it, ratchet was 8 and
# hooks had GROWN to 43. A typed count announces no way to re-check it — this poll's own opening
# rule — and it sat in the section reporting OPERATOR DECISIONS, which is the figure a reader
# would use to judge whether a decision is still worth its cost.
# ⚑⚑ IT WAS ALSO THE PARTITION SHAPE: three terms and a total from one typing, agreeing because
# they were written together, which is agreement carrying no information.
# ⚑ AND THE REPAIR IS NOT TO DERIVE IT HERE. Three ruff runs per poll would add three process
# starts to a script measured at 222, and the honest alternative to a stale number is NO number
# plus the command that yields a fresh one. A reader who wants the size can take it.
# ⚑⚑⚑ NO LONGER BLOCKED, AND THE WORD OUTLIVED THE WORK BY ONE TICK. Third ruling 2026-09-11: ARM
# `preview = true` REPO-WIDE, THEN PAY DOWN. hooks was armed and paid at 9802790 — 48 findings, the
# distribution clean under preview, its ratchet baseline LOWERED to zero on the operator's ruling
# 2026-09-12 (--write, 13 paid keys removed; a regression is now REFUSED rather than tolerated).
# ⚑⚑ THE STATUS WORD IS THE PART THAT ROTS, AND THIS ENTRY IS THE THIRD TIME. The figure above went
# stale twice and was repaired by REMOVING the number and printing the command instead; `BLOCKED`
# is the same defect one field over — a state word with no way to re-check it, in the section a
# reader consults to judge whether a decision still costs anything. It is now derived below.
# ⚑ THE HISTORY ABOVE IS KEPT IN FULL. The preconditions it records are why the ruling has three
# dates, and a reader meeting only the final state cannot tell an easy decision from one that took
# three attempts and a reverted autofix.
# ⚑⚑⚑ AND THE PREVIOUS REPAIR CLAIMED A DERIVATION IT DID NOT PERFORM. The comment above ends *it
# is now derived below*, and the line beneath it read `PARTIALLY PAID — hooks is armed and clean;
# the remaining distributions are NOT armed` — a second hand-written status under a sentence
# promising a measured one. ⚑ ratchet was armed and paid one tick later and that line kept naming
# hooks alone, which is the THIRD rot on this single entry: the figure twice, then `BLOCKED`, now
# the distribution list. A comment asserting what the line beside it destroys.
# ⚑⚑ THE FACT IS ON THE FILESYSTEM AND COSTS ONE GREP PER DISTRIBUTION: a config either sets
# `preview = true` in its own `[tool.ruff.lint]` or it does not. No ruff run, no process start —
# the objection that killed deriving the FIGURE (three ruff invocations per poll) does not apply to
# the STATUS, and conflating the two is why this stayed typed for three rots.
_armed=""
_unarmed=""
for _d in $(git -C "$mtools" ls-files '*/pyproject.toml' | cut -d/ -f1 | sort -u); do
    if grep -qE '^preview[[:space:]]*=[[:space:]]*true' "$mtools/$_d/pyproject.toml"; then
        _armed="$_armed $_d"
    else
        _unarmed="$_unarmed $_d"
    fi
done
echo "    every distribution armed and paid; all four ratchet baselines EMPTY. Four commits:"
echo "    9802790 hooks · 39b25ad ratchet · 9129a3d mdstruct · f7d92c9 fence."
# ⚑⚑⚑ THE DERIVATION SURVIVES THE DISCHARGE, AND ITS QUESTION HAS INVERTED. While the paydown ran
# it answered *which are left*; now it answers *has one been UN-armed* — a config edit dropping
# `preview = true` would silently restore a whole class of findings to unchecked, and this line is
# the only place a reader would see it. A discharged decision whose state can still regress needs
# its check kept, which is why this entry is collapsed rather than deleted.
# ⚑ AND IT COSTS ONE GREP PER DISTRIBUTION, so keeping it is nearly free — the objection that kept
# the FIGURE out of this poll (three ruff invocations per run) never applied to the STATUS.
echo "    ⚑ ARMED:${_armed:- none} · NOT ARMED:${_unarmed:- none}  — derived per poll, so this"
echo "      line now watches for a distribution being UN-armed rather than for work remaining."
# ⚑⚑ THE DISTRIBUTION LIST IS DERIVED, NOT TYPED — AND IT WAS TYPED, AND IT WENT STALE. This line
# read `for d in hooks mdstruct ratchet` while `fence` had landed at cc3d301, so a reader taking
# the measurement would have omitted a whole distribution and reported a total for a population
# that is not this repository's. The same hand-written-population defect as ⟐FENCE-WARRANTS, in
# the poll rather than in the gate.
# ⚑ AND DERIVING IT COSTS NOTHING HERE: the query at the top of this script already enumerates
# every distribution by its pyproject.toml. What that comment above refuses is RUNNING RUFF in the
# poll — three process starts — which is a separate thing from knowing WHICH directories to name.
# ⚑⚑⚑ THE DECLARED RUFF, NOT THE HOST VENV'S — AND THIS LINE OUTLIVED THE DECISION THAT RETIRED
# THAT INSTRUMENT. It read `.venv/bin/ruff` while `ad49f96` removed host ruff from the gate and
# `preflight.sh` on the operator's ruling that gate verdicts use the build's venv. A poll telling
# a reader to measure with the instrument the repository has stopped trusting is the stale-record
# class this poll exists to catch, in the poll.
# ⚑⚑ THE TWO AGREE TODAY AND THAT IS NOT THE POINT. Measured on `hooks`, byte-identical output:
# 48 errors, same seven rules, same counts, host venv and `@ruff//:bin` alike. They are 0.16.6 by
# a coincidence maintained BY HAND between resolvers with no shared constraint — so naming the
# declared one costs nothing today and is the one that stays right.
# ⚑ `//<dist>:ratchet` ALREADY RUNS `--preview` and is NOT a substitute here: it reports refusals
# against a baseline — *did the debt grow* — while this line asks *how big is the debt*. Different
# questions; the target answers the first, and nothing answers the second without running ruff.
# ⚑ AND THE PATH MUST BE ABSOLUTE, WHICH THE OBVIOUS FORM IS NOT: `cquery --output=files` prints
# `external/+_repo_rules+ruff/ruff`, relative to the EXECROOT — measured — so under `env -C $d` it
# would resolve against the distribution directory and fail. `bazel info execution_root` supplies
# the prefix. A printed instruction nobody has run is prose, not a measurement.
# ⚑⚑⚑ AND THIS RECIPE PRODUCED A PATH THAT NAMES NOTHING, MEASURED BY RUNNING IT — in the very
# entry whose comment above says *a printed instruction nobody has run is prose*. `execution_root`
# is `<output_base>/execroot/_main`, and `external/+_repo_rules+ruff/ruff` does NOT exist beneath
# it; the fetched binary lives at `<output_base>/external/...`. The execroot form resolves only
# while a build happens to have staged that tree, so it works when you have just built and fails
# when you have not — a recipe whose correctness depends on unstated state.
# ⚑⚑ `bazel info output_base` IS THE STABLE ANCHOR, and it was available all along. The lesson the
# comment above records — run the instruction — was applied to the RELATIVE-vs-ABSOLUTE question
# and not to the prefix itself, so the fix stopped one layer short of the defect.
# ⚑⚑ THE RECIPE IS NO LONGER PRINTED, AND THE COMMENTS ABOVE ARE WHY IT IS KEPT IN SOURCE. It
# answered *how big is the remaining paydown* — a question whose answer is now 0 in every
# distribution, so printing the command invites a reader to run three ruff invocations to be told
# nothing. ⚑ Its two hard-won corrections (derive the distribution list; `output_base`, not
# `execution_root`) are recorded in the comments above and would be needed again by whoever arms
# the next preview-gated rule, which is exactly why they stay readable here rather than being cut.
# ⚑⚑ THIS LINE WAS A LIVE CONSTRAINT AND IS NOW A HISTORICAL ONE, so it says which. Renaming was
# unshippable BEFORE the arming: measured, `--select magic-value-comparison` gives rc=2 *ruff
# failed* without `--preview` and rc=1 with it, so the rename had to follow the arming rather than
# precede it. hooks is armed, and its selectors ARE renamed — stating the bar as still-binding
# would tell a reader the opposite of what the tree holds.
# ⚑ AND THE TAIL OF THIS LINE WAS THE SAME ROT A SECOND TIME IN ONE ENTRY. It read *Done for
# hooks; the other three await it* — a count and a name, both hand-written, both wrong the tick
# ratchet landed. The order is a permanent fact about ruff and stays typed; WHICH distributions
# have done it is a fact about this tree and is derived above.
# ⚑ THE ORDERING RULE IS A PERMANENT FACT ABOUT RUFF AND A SPENT INSTRUCTION HERE. *Arm preview,
# then rename* still holds — a name selector cannot LOAD without it, measured — but there is no
# distribution left to apply it to, so printing it each tick is guidance for nobody. Kept in
# source for the next preview-gated adoption; not printed, because a live imperative with no
# population is the shape this whole entry rotted on four times.
# ⚑⚑⚑ THE SUPPRESSION RULES CHAIN, AND THE SECOND LINK IS PREVIEW-ONLY. Measured on a probe with
# an F-arm (a bare violation is REPORTED in both configurations, so a rc=0 below means suppression
# rather than a rule that never ran):
#
#     # noqa: S101              no-preview rc=0   --preview rc=0
#     # ruff: ignore[S101]      no-preview rc=0   --preview rc=0    <- both, safe today
#     # ruff: ignore[assert]    no-preview rc=1   --preview rc=0    <- PREVIEW-ONLY
#     # ruff: ignore  (bare)    no-preview rc=1   --preview rc=1    <- suppresses NOTHING
#
# ⚑⚑ RUF105 moves `noqa:` to `ruff: ignore[CODE]`; RUF106 then objects to that very CODE and wants
# the NAME. Satisfying RUF106 before preview is armed produces directives the gate's ruff does not
# honour, and the suppressed findings reappear.
# ⚑ AND THE ARM'S OWN F-ARM CORRECTED THIS ENTRY. I first wrote that the failure is SILENT. It is
# not: swapping one directive to the name form yields TWO findings — the un-suppressed one, and
# `RUF102 Invalid rule code in suppression` naming the directive. The probe measured suppression
# alone and missed the second signal. The harm is the reappearing finding; the overstatement was
# mine, and claiming less evidence than exists is its own defect.
# ⚑ SO THE CODE FORM IS THE RESTING PLACE. 16 directives swapped in hooks and verified: `ruff
# check` (no preview) still `All checks passed!`, suite 337 pass. RUF105 cleared, RUF106 opened at
# the same 16 sites, total unmoved at 41 — a rule renamed, not a defect paid.
# ⚑⚑⚑ THE CHAIN CAVEAT IS NO LONGER PRINTED BECAUSE THE HAZARD IS CLOSED BY CONSTRUCTION. It
# warned that a renamed suppression directive fails SILENTLY in a distribution that is not armed —
# true, and there is now no such distribution. The comments below record the mechanism and the
# measurement, which is what a future reader arming a preview-gated rule elsewhere would need.
# ⚑⚑ AND THE SILENT-FAILURE HAZARD IS CLOSED WHERE PREVIEW IS ARMED, WHICH IS WHY THIS SAYS WHERE.
# The chain fails silently only when the gate and the census disagree about the rule set. `preview
# = true` in a distribution's own `[tool.ruff.lint]` removes the flag both callers could differ on
# — the gate passes no `--preview` and loads it from the config — so in hooks there is no longer a
# configuration in which a renamed directive stops suppressing. Measured: reverting one directive
# to the code form leaves the suppression WORKING and raises only the style rule.
# ⚑ THE THIRD NAME IN THIS ENTRY, AND IT WAS THE NEXT ONE TO ROT. It read `(hooks)` as an example
# of the mechanism rather than as a status — a distinction that survives exactly until a reader
# takes it for the list. Pointing at the derived line costs nothing and cannot go stale.
# ⚑⚑ DISCHARGED 2026-09-10 AT ab722b5, AND THE OLD LINE SURVIVED THE EVENT IT DESCRIBED. It read
# "ANSWERED 2026-09-07: mtools asks for a diff" — true when written, false the moment the diff
# arrived. cassian filed it, mtools answered in findings/cassian-observability.md, and the filing
# is archived. A carried-decision line naming a request that has been FULFILLED is the stale-record
# class this poll exists to catch, sitting in the poll itself.
echo "  cassian's hook components  raised by cassian  DISCHARGED 2026-09-10 at ab722b5"
echo "    diff filed, answered in findings/cassian-observability.md, filing archived."
echo "    ⚑ measured while answering: 16 flag-argument arms here against the 7 cassian listed;"
echo "      nine shapes covered that their list omits. Nothing to lift; flow is outward."
echo "  gate cost                  raised by mtools   ⚑ WITHDRAWN — self-raised, no consequence"
echo "    614163d measured that no stable figure exists; carrying it as blocked was my error."

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

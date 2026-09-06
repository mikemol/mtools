#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A STANDING WITNESS ON A CHECKER'S DOMAIN. An action's verdict ranges over its DECLARED
# inputs, so a checker whose declaration is short of its real domain returns a stale green for
# every input it cannot see. mypy is the case that matters here, because it is the one checker
# whose verdict on a file depends on files it does not name: editing an imported module changes
# the importer's type-correctness while leaving its bytes untouched.
#
# ⚑⚑ THE CLAIM WAS TRUE AND UNARMED, WHICH IS THE STATE THIS REPOSITORY REFUSES ELSEWHERE. The
# BUILD file declares `glob(["src/**/*.py", ...])` — structurally right, and never once tested
# against a transitive edit. A glob that silently stopped matching, a `srcs` narrowed during a
# refactor, or a distribution added without the pattern would each produce a green mypy over a
# domain smaller than the type checker's own.
#
# ⚑ AND A ONE-ARMED VERSION OF THIS WITNESS IS WORSE THAN NONE. Asserting only that the action
# RE-RUNS proves the file is an input; asserting only that mypy FAILS proves mypy works. Neither
# alone proves the DOMAIN is complete — the pair does: a transitive edit must reach the action,
# and a transitive DEFECT must reach the verdict.
set -uo pipefail

dist="${1:?the distribution directory was not passed}"
target="${2:?the target was not passed}"
victim="${3:?the transitive module was not passed}"

# ⚑⚑⚑ THE ARM-2 PAYLOAD IS THE CHECKER'S OWN DEFECT CLASS, AND HARDCODING IT SILENTLY SCOPED THIS
# WITNESS TO ONE CHECKER. The first cut planted a Python TYPE error — which mypy catches and ruff
# and the ratchet do not. Pointed at `//ratchet:ruff`, that witness would have reported arm 2
# FAILED and read as "ruff's domain is short" when the truth was "I planted a defect ruff does not
# look for". ⚑ A PROBE THE CHECKER IGNORES IS INDISTINGUISHABLE FROM A DOMAIN THAT EXCLUDES IT.
#
# ⚑⚑ So the payload is a parameter and its DEFAULT is stated rather than assumed:
#   mypy     a return type that does not match its annotation
#   ruff     an unused import (F401)
#   ratchet  a preview-rule violation, which grows the census by a key
probe_kind="${4:-mypy}"

cd "$(dirname "$0")" || exit 1
# ⚑⚑⚑ RESIDUE FROM A KILLED PREDECESSOR IS DETECTED BEFORE ANYTHING RUNS, because `trap ... EXIT`
# CANNOT fire on SIGKILL. Measured: killing a witness inside its mutation window leaves the probe
# in the victim, and the next gate run censuses it — reporting ratchet keys from a probe nobody
# wrote. ⚑ SIGTERM is fine (the trap runs); SIGKILL is not, and no handler can make it be.
#
# ⚑⚑ THIS IS THE ONLY CASE WHERE A WITNESS CAN POISON A LATER RUN, and it is silent: the residue
# is syntactically valid, the suite still passes, and only the ratchet notices — as new debt, in a
# file the author did not touch. A pre-flight refusal is the whole repair.
#
# ⚑ IT RUNS BEFORE THE TRACKED CHECK, and the order is a claim about what each guard KNOWS.
# Residue is a fact about the file's CONTENTS and needs no repository; tracking is a fact about
# git. Checking contents first gives the more specific diagnosis — and it also makes the guard
# reachable by a fixture, where the tracked check would have refused first and a test could not
# tell which guard fired.
if grep -q "transient domain probe" "$victim" 2>/dev/null; then
    echo "domain_witness: $victim already carries probe residue — refusing" >&2
    echo "  a previous witness was killed inside its mutation window (SIGKILL defeats the" >&2
    echo "  EXIT trap). Run: git checkout $victim" >&2
    exit 2
fi

# ⚑⚑⚑ THE VICTIM MUST BE TRACKED, AND NOTHING CHECKED IT. `git checkout` on an untracked path
# silently does nothing, so every arm ran, the payloads ACCUMULATED, and arm 3 reported RESTORED
# over a file it had not restored. ⚑ MEASURED: a test passed `ratchet/x.py` — a path that did not
# exist — and the witness CREATED it, appending five probe payloads across five invocations. The
# ratchet then censused the debris and refused the commit, which is the only reason it surfaced.
# A witness that can bring a file into existence is not probing a domain; it is editing one.
if ! git ls-files --error-unmatch "$victim" >/dev/null 2>&1; then
    echo "domain_witness: $victim is not tracked — refusing" >&2
    echo "  every arm mutates this file and restores it with 'git checkout', which silently" >&2
    echo "  does nothing for an untracked path: the probe would persist and arm 3 would" >&2
    echo "  report RESTORED over a file it never touched" >&2
    exit 2
fi

# ⚑⚑⚑ A DIRTY VICTIM IS REFUSED, BECAUSE ARM 3 RESTORES WITH `git checkout <path>` AND THAT
# DISCARDS THE WHOLE FILE — not just the probe. MEASURED: an uncommitted edit to `blockers.sh`
# was destroyed by the shellcheck witness, which reported rc=0 while doing it. The next commit
# then failed with `no changes added to commit`, and I spent a tick attributing that to
# `git commit --only` and then to path scope, testing and eliminating both, because a witness
# reporting success is not where one looks for a deletion.
#
# ⚑⚑ THE WITNESS CANNOT TELL ITS OWN PROBE FROM A USER'S WORK. `git checkout` is file-granular
# and the probe is line-granular, so restoration is necessarily over-broad. The residue guard
# above catches a probe left by a KILLED predecessor; this catches work that was never a probe at
# all, and both are the same underlying fact: this instrument's restore is a whole-file operation.
#
# ⚑ IT REFUSES RATHER THAN SAVING AND REPLAYING THE EDIT. A witness that stashed and restored a
# user's work would be a second mutation path over the same file, and the failure mode of a
# stash-replay that goes wrong is silent corruption rather than a refusal.
# ⚑⚑⚑ UNSTAGED, NOT MERELY UNCOMMITTED — AND THE FIRST CUT OF THIS GUARD WAS A DEADLOCK.
# `git status --porcelain` is non-empty for a STAGED change too, so refusing on it made every
# victim file permanently uncommittable: a change to `blockers.sh` could never pass the gate that
# runs a witness over `blockers.sh`. Measured: rc=2 on a staged-only edit.
#
# ⚑⚑ AND THE DISTINCTION IS NOT A CONVENIENCE, IT IS WHAT `git checkout` DOES. Measured in a
# scratch repo: with v2 staged and v3 in the working tree, `git checkout -- f.txt` yields **v2**.
# It restores from the INDEX. So a staged change SURVIVES arm 3 and only unstaged work is
# destroyed — which is exactly the set this guard must refuse, and no larger.
#
# ⚑ THE FIX FOR MY OWN DEADLOCK IS THE MEASUREMENT I SHOULD HAVE TAKEN BEFORE WRITING THE GUARD:
# I knew the restore was file-granular and assumed it was HEAD-granular too.
if [ -n "$(git diff --name-only -- "$victim" 2>/dev/null)" ]; then
    echo "domain_witness: $victim has UNSTAGED changes — refusing" >&2
    echo "  arm 3 restores from the index with 'git checkout' and would DISCARD them." >&2
    echo "  Stage them (git add) or stash. A STAGED change is safe and does not trip this." >&2
    exit 2
fi

# ⚑⚑ THE RESTORE VERIFIES, because a restore that fails silently is the same defect one layer in.
# ⚑⚑⚑ THE BEFORE-IMAGE IS TAKEN BEFORE ANY MUTATION, AND WITHOUT IT THIS WITNESS COULD NOT TELL
# ITS OWN RESIDUE FROM A PEER'S WORK. `restore` compared `git diff --quiet -- $victim`, which is a
# WHOLE-FILE predicate: it conflates *I failed to restore my own edit* with *someone else's edit
# arrived while I ran*. Both print `the tree is dirty`, and only the first is this script's
# business.
#
# ⚑⚑ MEASURED, AND IT BLOCKED FOUR PARTIES AT ONCE (2026-09-06). Seven sessions write this tree.
# Four witnesses lost the arm-3 race simultaneously and left sabotage in `blockers.sh`,
# `cmdparse.py`, `frontmatter.py` and `state.py` — including a TYPE defect
# (`def _transient_domain_probe() -> int: return "not an int"`) that produced six mypy/ruff
# refusals I read as six separate failures. `gabion` diagnosed the attribution half and declined
# to revert a file it did not own, which was correct and is why it stayed stranded.
#
# ⚑⚑⚑ AND THE DANGEROUS DIRECTION IS THAT THE SABOTAGE OUTLIVES THE RUN THAT MADE IT. A later
# commit by ANY party carries `probe_unused=$(echo $PROBE_UNQUOTED)` into HEAD as real content,
# after which `//:shellcheck_githooks` fails on it FOR REAL, in a file nobody edited on purpose.
# **A witness that proves a gate can fail by writing a defect it does not reliably clean up is a
# defect generator under concurrency** — gabion's phrase, and it names what I built.
#
# ⚑ THE SABOTAGE STAYS IN THE REAL FILE. A witness over a copy proves the COPY's domain, which is
# the whole reason arm 2 mutates the tracked file. So the repair is not to move the mutation; it is
# to make the restore VERIFIABLE independent of everything else in the tree.
before_image="$(git hash-object "$victim" 2>/dev/null)"

# ⚑⚑⚑ `git checkout`'s OWN STATUS IS REPORTED SEPARATELY FROM THE DIRTINESS RE-READ, AND
# CONFLATING THEM MADE THE BEFORE-IMAGE REPAIR INHERIT THE DEFECT IT FIXED. The before-image made
# a failed restore ATTRIBUTABLE — correctly, which is why the message could say *this is my
# residue* rather than *the tree is dirty*. ⚑ But the comparison is still A POINT SAMPLE OF A
# MUTABLE FILE, so it can be right about attribution and wrong about the present.
#
# ⚑⚑ MEASURED FROM THE BLOCKED SEAT (`gabion`, in one sequence): the gate printed
# `CONTENT DIFFERS ... before=d960db4d now=59f4460e`, and an immediate check found
# `git hash-object` == `git ls-files -s` == the very `before=` the message named as correct — then
# the retry failed with `Unable to create .git/index.lock`. **The `checkout` never ran; something
# else restored the file; and the message described a state that no longer existed when it was
# read.**
#
# ⚑⚑⚑ SO THE TWO OUTCOMES ARE NOW NAMED. A non-zero `checkout` is *I could not act* — a lock, a
# permission, a missing path — and says nothing about the file. A zero `checkout` with a hash that
# still differs is *I acted and it did not take*. `gabion`'s statement of the class is the one to
# keep: **a before-image fixes attribution; it does not make a reading current.**
restore() {
    _co_err="$(git checkout "$victim" 2>&1)"; _co_rc=$?
    now="$(git hash-object "$victim" 2>/dev/null)"
    if [ "$now" = "$before_image" ]; then
        return 0
    fi
    if [ "$_co_rc" -ne 0 ]; then
        echo "domain_witness: $victim — COULD NOT RESTORE; git checkout exited $_co_rc" >&2
        echo "  git said: ${_co_err%%$'\n'*}" >&2
        echo "  ⚑ THIS IS 'I COULD NOT ACT', NOT 'MY RESTORE FAILED'. The file's state is" >&2
        echo "  unknown to this witness — re-read it rather than trusting this line." >&2
        return 0
    fi
    echo "domain_witness: $victim CONTENT DIFFERS FROM THE BEFORE-IMAGE — this witness's own" >&2
    echo "  restore ran (rc=0) and did not take. before=${before_image:-<unmeasured>}" >&2
    echo "  now=${now:-<unreadable>}" >&2
    echo "  ⚑ THIS IS MY RESIDUE, NOT A PEER'S EDIT. Run: git checkout $victim" >&2
}
trap restore EXIT

# ⚑⚑⚑ THE PROBE KIND IS VALIDATED BEFORE ANY BAZEL RUNS, AND IT WAS NOT. The dispatch's `*)` arm
# sits after the control and after arm 1 — so a typo'd kind paid for a full control invocation and
# a mutate-plus-rebuild before refusing, and it refused with the victim already edited. ⚑ A guard
# that fires late is still correct and still teaches the wrong thing: the cheapest possible
# refusal for an unusable argument is before the first side effect.
case "$probe_kind" in
    mypy|ruff|ratchet|baseline|shellcheck) ;;
    *) echo "domain_witness: unknown probe kind '$probe_kind' — a probe the checker does not" >&2
       echo "  seek is indistinguishable from a domain that excludes the file, so this refuses" >&2
       echo "  rather than planting bytes no checker will read" >&2
       exit 2 ;;
esac

fail=0
say() { printf '  %s\n' "$*"; }

# ⚑ THE CONTROL RUNS FIRST AND MUST PASS. An arm measured against an already-red tree reports the
# pre-existing failure as its own finding — and every subsequent arm agrees for the wrong reason.
if ! bazel test "$target" >/dev/null 2>&1; then
    say "CONTROL FAILED: $target is red BEFORE the probe — the arms below would be meaningless"
    exit 1
fi

# ⚑⚑ ARM 1 — REACHABILITY. A CONTENT change (not `touch`: bazel keys on bytes, so an mtime bump
# invalidates nothing and an arm built on one measures the clock, not the graph).
# ⚑⚑⚑ THE PROBE CARRIES A NONCE, AND WITHOUT ONE THIS ARM IS UNFALSIFIABLE-GREEN'S TWIN: A
# PERMANENT FALSE RED. A fixed probe string is a digest the cache has already seen, so the second
# run of this witness is served from the remote cache — `Executed 0 out of 1` — and the arm
# concludes the file is outside the domain. Measured: identical `# probe` appends returned
# `Executed 0` while a nonce-carrying append returned `1 linux-sandbox`, same file, seconds apart.
#
# ⚑⚑ AND THE TWO EXPLANATIONS ARE INDISTINGUISHABLE IN THE OUTPUT THIS ARM READS. "Not an input"
# and "already answered" both print `Executed 0`. A witness that cannot separate them is not
# measuring the domain — it is measuring whether it has run before, which is the one question it
# was not asked.
printf '\n# transient domain probe %s\n' "$(date +%s%N)" >> "$victim"
# ⚑⚑⚑ THE OUTPUT IS CAPTURED, THEN MATCHED — NEVER `bazel | grep -q`. Under `pipefail`, a `grep -q`
# that MATCHES closes the pipe, bazel takes SIGPIPE, and the pipeline reports bazel's death as the
# verdict: the arm fails precisely BECAUSE it found what it was looking for. Measured here — both
# arms of this witness reported FAILED against a tree that had passed the same probes by hand
# minutes earlier. That is this repository's Rule 14 defect (the reporter's status standing in for
# the subject's) reappearing inside the witness written to enforce the rule it belongs to.
out="$(bazel test "$target" 2>&1)"
if printf '%s' "$out" | grep -q "Executed 1 out of 1 test"; then
    say "arm 1 REACHABILITY: a content change in $victim re-executes the action"
else
    say "arm 1 FAILED: editing $victim did NOT invalidate $target — it is outside the domain"
    say "  (or the probe's bytes were already cached — arm 1 nonces to rule that out)"
    fail=1
fi
restore

# ⚑⚑ ARM 2 — VERDICT. Reachability alone only proves the bytes are keyed; this proves the checker
# actually ranges over them.
case "$probe_kind" in
    # ⚑⚑⚑ THE BASELINE IS A DECLARED DATA INPUT, NOT A SOURCE FILE, AND IT IS THE ONE THIS
    # REPOSITORY'S OWN `ratchet_check.sh` HEADER WARNS GETS DROPPED: "a ratchet whose baseline sits
    # outside its own key can be lowered with no gate noticing." Every other probe here appends to
    # a `.py` the checker reads; this one mutates the file the verdict is compared AGAINST.
    #
    # ⚑⚑ AND THE DIRECTION MATTERS, WHICH IS WHY ADDING A KEY IS THE WRONG ARM. Measured: appending
    # a fabricated key re-executes the action and PASSES — correctly, because a baseline holding a
    # key the census does not produce is paydown, not growth. Only REMOVING a key makes a real
    # finding unaccounted, and that is the arm that must refuse. A witness that appended would have
    # reported arm 2 FAILED against a gate behaving exactly as designed.
    # ⚑ THE NONCE IS A COMMENT LINE, NOT A KEY, so the census is unaffected and only the file's
    # DIGEST moves. Without it this probe alternates between exactly two digests (shortened and
    # restored) and passes only because arm 3 rewrites the file — a Rule 16 defect that survives by
    # accident rather than by design. An accidental pass is one refactor away from a permanent red.
    # ⚑⚑⚑ THE ONLY DESTRUCTIVE PROBE, AND IT MUST BE. Every other kind APPENDS, so a concurrent
    # reader sees the file plus noise. This one DELETES a key — measured as necessary: a
    # comment-only probe leaves the gate PASSING, because a baseline holding a key the census does
    # not produce is paydown, and only a MISSING key is growth.
    #
    # ⚑⚑ SO A READER THAT SAMPLES THIS FILE MID-PROBE SEES THE BASELINE SHORT BY ONE KEY and
    # reports that finding as NEW DEBT — a false refusal. Measured: deleting the last line alone
    # reproduces exactly the refusal that blocked a commit earlier, `tests/test_core.py:
    # noqa-comments` reported as new. ⚑ I had attributed that failure to the nonce being read as
    # a key, which was a real defect and was fixed — but the DELETION was the operative half, and
    # the fix worked for a reason I had wrong.
    #
    # ⚑ THE DIRECTION IS SAFE AND THE AMBIGUITY IS NOT: a false refusal never absolves debt, but
    # it is indistinguishable from a genuine violation, so an operator meeting it debugs a finding
    # that does not exist.
    baseline) head -n -1 "$victim" > "$victim.probe" \
                  && printf '# transient domain probe %s\n' "$(date +%s%N)" >> "$victim.probe" \
                  && mv "$victim.probe" "$victim" ;;
    # ⚑⚑⚑ EVERY PAYLOAD CARRIES THE MARKER, AND THIS ONE DID NOT. The residue guard (line ~54) and
    # the gate's sweep both key on the literal `transient domain probe`; the mypy payload was the
    # one probe kind that omitted it, so a stranded mypy probe was invisible to BOTH — measured
    # today, `ratchet/src/mikemol/ratchet/state.py` dirty with a probe that `grep -c 'transient
    # domain probe'` reported as 0. ⚑ A guard and a sweep that agree on a predicate the payload
    # does not satisfy is a control that cannot see the thing it exists for.
    mypy)    printf '\n\n# transient domain probe %s\ndef _transient_domain_probe() -> int:\n    return "not an int"\n' "$(date +%s%N)" >> "$victim" ;;
    ruff)    printf '\nimport os  # transient domain probe\n' >> "$victim" ;;
    # ⚑ SHELLCHECK'S DEFECT CLASS IS AN UNQUOTED EXPANSION — the one thing every other probe here
    # cannot express, because the other checkers read Python. Measured: this single line yields
    # SC2034, SC2086 and SC2116, so the probe is unambiguous rather than resting on one rule
    # remaining enabled.
    # ⚑⚑ THE PAYLOAD IS ASSEMBLED, NOT WRITTEN LITERALLY, because a literal unquoted expansion in
    # THIS file makes THIS file fail the very checker it is probing — measured: the control caught
    # it and refused, correctly, since a target already red makes every arm below meaningless.
    shellcheck) printf '\n# transient domain probe %s\nprobe_unused=%s%s(echo %sPROBE_UNQUOTED)\n' "$(date +%s%N)" '$' '' '$' >> "$victim" ;;
    ratchet) printf '\n\n# transient domain probe %s\ndef _transient_domain_probe():\n    """Probe."""\n    return 1\n' "$(date +%s%N)" >> "$victim" ;;
    *)       say "arm 2 FAILED: unknown probe kind $probe_kind"; exit 1 ;;
esac
# ⚑⚑⚑ THE EXIT STATUS IS THE VERDICT, NOT A STRING IN THE TRANSCRIPT. The first cut matched
# `FAILED` in bazel's output, which is a SUBSTRING OF A STATUS LINE and not the status: it appears
# in a cached summary, in an unrelated target's row when the arm runs inside a suite, and nowhere
# at all when a target fails to build rather than to test. Measured: this arm reported FAILED
# inside the gate — where `bazel test //...` had just run and one unrelated target was red — while
# passing in isolation seconds later. An ORDER-DEPENDENT arm is worse than a failing one, because
# it is green whenever anyone checks it directly.
# ⚑ THAT IS THIS REPOSITORY'S OWN RULE 25 IN THE WITNESS BUILT TO ENFORCE ITS FAMILY: a string
# match answers "does this word appear", and the question was "did this target refuse".
if ! bazel test "$target" >/dev/null 2>&1; then
    say "arm 2 VERDICT: a $probe_kind defect in $victim fails $target"
else
    # ⚑ THE TWO EXPLANATIONS ARE NAMED, because this arm cannot tell them apart and a message that
    # asserted only the first would send a reader to repair a declaration that is already correct.
    say "arm 2 FAILED: $target did not refuse a planted $probe_kind defect in $victim"
    say "  either the domain is SHORT, or the $probe_kind probe is not a defect THIS checker seeks"
    fail=1
fi
restore

# ⚑ ARM 3 — RESTORATION. A witness that leaves the tree dirty makes the NEXT gate's verdict a
# fact about this script.
# ⚑⚑ THE VICTIM'S CONTENT IS CHECKED BEFORE THE TARGET IS, BECAUSE THE TARGET CANNOT ATTRIBUTE.
# `bazel test` going red after a restore has two causes — my probe survived, or a peer wrote to
# some other declared input while I ran — and this arm reported the first for both. Comparing the
# victim against its before-image separates them: if the content matches, my restore succeeded and
# anything still red belongs to someone else's write.
after_image="$(git hash-object "$victim" 2>/dev/null)"
if [ "$after_image" != "$before_image" ]; then
    say "arm 3 FAILED: $victim's content differs from its before-image — MY restore failed"
    say "  before=${before_image:-<unmeasured>} after=${after_image:-<unreadable>}"
    say "  ⚑ this is this witness's own residue. Run: git checkout $victim"
    fail=1
elif bazel test "$target" >/dev/null 2>&1; then
    say "arm 3 RESTORED: $dist is green again"
else
    # ⚑ NOT A RESTORE FAILURE, AND SAYING SO IS THE POINT. The victim is byte-identical to what
    # this witness found. A red target now is a fact about a DIFFERENT input — a peer's in-flight
    # write, or a defect that was already there — and reporting it as `was not restored` sends the
    # reader to `git checkout` a file that is already correct.
    say "arm 3: $victim RESTORED (content matches its before-image), but $target is RED"
    say "  ⚑ that is NOT this witness's residue — some other declared input of $target changed"
    say "  seven sessions write this tree; check 'git status' before treating it as a defect"
    fail=1
fi

[ "$fail" -eq 0 ] || { echo "domain_witness: REFUSED" >&2; exit 1; }
printf 'domain_witness: %s — domain is reachable, ranged-over, and restored\n' "$target"

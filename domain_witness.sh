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

# ⚑⚑ THE RESTORE VERIFIES, because a restore that fails silently is the same defect one layer in.
restore() {
    git checkout "$victim" 2>/dev/null
    if ! git diff --quiet -- "$victim" 2>/dev/null; then
        echo "domain_witness: $victim did not restore — the tree is dirty" >&2
    fi
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
    baseline) head -n -1 "$victim" > "$victim.probe" \
                  && printf '# transient domain probe %s\n' "$(date +%s%N)" >> "$victim.probe" \
                  && mv "$victim.probe" "$victim" ;;
    mypy)    printf '\n\ndef _transient_domain_probe() -> int:\n    return "not an int"\n' >> "$victim" ;;
    ruff)    printf '\nimport os  # transient domain probe\n' >> "$victim" ;;
    # ⚑ SHELLCHECK'S DEFECT CLASS IS AN UNQUOTED EXPANSION — the one thing every other probe here
    # cannot express, because the other checkers read Python. Measured: this single line yields
    # SC2034, SC2086 and SC2116, so the probe is unambiguous rather than resting on one rule
    # remaining enabled.
    # ⚑⚑ THE PAYLOAD IS ASSEMBLED, NOT WRITTEN LITERALLY, because a literal unquoted expansion in
    # THIS file makes THIS file fail the very checker it is probing — measured: the control caught
    # it and refused, correctly, since a target already red makes every arm below meaningless.
    shellcheck) printf '\nprobe_unused=%s%s(echo %sPROBE_UNQUOTED)\n' '$' '' '$' >> "$victim" ;;
    ratchet) printf '\n\ndef _transient_domain_probe():\n    """Probe."""\n    return 1\n' >> "$victim" ;;
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
if bazel test "$target" >/dev/null 2>&1; then
    say "arm 3 RESTORED: $dist is green again"
else
    say "arm 3 FAILED: $victim was not restored — the tree is dirty"
    fail=1
fi

[ "$fail" -eq 0 ] || { echo "domain_witness: REFUSED" >&2; exit 1; }
printf 'domain_witness: %s — domain is reachable, ranged-over, and restored\n' "$target"
